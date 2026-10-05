"""Guard against fabricated scientific results.

The proteomics and ATAC-seq MCP servers once generated `np.random` fold
changes, p-values, peak counts and enrichment scores, returned them with
`success: True`, and slept to imitate compute time. A scientist could not tell
the output from a real run.

This test makes that class of defect fail the build. It distinguishes two
legitimate uses of randomness from the illegitimate one:

- synthetic INPUT inside a self-test or demo entry point (allowed)
- randomness in a function that produces a RESULT (rejected)

It is deliberately an AST check rather than a grep, so `main()` test harnesses
do not have to be exempted by filename.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Analysis code that must never invent numbers.
GUARDED_ROOTS = [
    REPO_ROOT / "src" / "mcp" / "servers",
    REPO_ROOT / "src" / "modules",
    REPO_ROOT / "src" / "gliaent",
]

#: Enclosing functions where synthetic data is a fixture, not a result.
FIXTURE_FUNCTIONS = {"main", "_demo", "demo", "_main"}

#: numpy randomness only. Fabricated results always came through numpy;
#: stdlib `random` is also used for rate-limit jitter, which is legitimate.
RANDOM_ATTRS = {"random", "rand", "randn", "randint", "normal", "uniform",
                "beta", "exponential", "lognormal", "choice", "poisson"}


def _guarded_files():
    for root in GUARDED_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path


def _random_calls_outside_fixtures(path: Path):
    """Return (lineno, snippet) for each disallowed random use in `path`."""
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        # A separate test covers syntax errors; don't double-report here.
        return []

    # Map every node to its enclosing function names.
    enclosing: dict[int, list[str]] = {}

    class Walker(ast.NodeVisitor):
        def __init__(self):
            self.stack: list[str] = []

        def visit_FunctionDef(self, node):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def generic_visit(self, node):
            if hasattr(node, "lineno"):
                enclosing.setdefault(id(node), list(self.stack))
            super().generic_visit(node)

    walker = Walker()
    walker.visit(tree)

    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if node.attr not in RANDOM_ATTRS:
            continue
        # Match np.random.X / numpy.random.X / random.X
        chain = node
        parts = []
        while isinstance(chain, ast.Attribute):
            parts.append(chain.attr)
            chain = chain.value
        if isinstance(chain, ast.Name):
            parts.append(chain.id)
        parts.reverse()
        dotted = ".".join(parts)
        if not dotted.startswith(("np.random", "numpy.random")):
            continue

        names = enclosing.get(id(node), [])
        if any(n in FIXTURE_FUNCTIONS or n.startswith("test_") for n in names):
            continue
        offenders.append((node.lineno, dotted))
    return offenders


@pytest.mark.parametrize(
    "path", list(_guarded_files()), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_no_randomness_in_result_producing_code(path):
    """Randomness outside a fixture function means invented results."""
    offenders = _random_calls_outside_fixtures(path)
    assert not offenders, (
        f"{path.relative_to(REPO_ROOT)} uses randomness in result-producing code:\n"
        + "\n".join(f"  line {line}: {call}" for line, call in offenders)
        + "\n\nIf this is a synthetic test fixture, move it into a function named "
        "main()/demo() or a test_*. If it is standing in for an unimplemented "
        "analysis, raise NotImplementedError instead."
    )


def test_no_simulated_processing_delays():
    """`asyncio.sleep` to imitate compute time always accompanied fake results."""
    offenders = []
    for path in _guarded_files():
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if "asyncio.sleep" not in stripped or stripped.startswith("#"):
                continue
            lowered = stripped.lower()
            if any(w in lowered for w in ("simulate", "mock", "fake", "pretend")):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {stripped}")
    assert not offenders, "simulated processing delays found:\n" + "\n".join(offenders)


def test_uniprot_search_is_not_a_canned_response():
    """The mock UniProt client returned hardcoded p53 for every query."""
    source = (REPO_ROOT / "src" / "modules" / "search" / "uniprot.py").read_text()
    assert "mock_results" not in source, "uniprot.py still returns canned results"
    # The specific tell: the query interpolated into a hardcoded protein name.
    assert "Cellular tumor antigen p53 - {query}" not in source
