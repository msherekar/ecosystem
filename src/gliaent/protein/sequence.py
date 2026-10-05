"""Protein sequences, FASTA I/O, and variants.

The first real protein primitive in Gliaent. Before this, the only
protein-shaped code in the repository was a mock UniProt search and a
mass-spectrometry server; `biopython` was a declared dependency that nothing
imported for sequence work.

A `Variant` is first-class because biochemists think in mutations — `K27M`,
`C215S` — not in edited strings. A construct is a parent sequence plus an
ordered mutation list, which is what lets an assay result, a design and a
structure all refer to the same object.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, TextIO

#: The 20 standard amino acids, plus the ambiguity codes IUPAC defines for
#: protein: B (D/N), Z (E/Q), J (I/L), X (any), U (selenocysteine),
#: O (pyrrolysine) and `*` for a translation stop.
STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")
AMBIGUOUS_AA = set("BXZJUO*")
VALID_AA = STANDARD_AA | AMBIGUOUS_AA

THREE_TO_ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
    "SEC": "U", "PYL": "O", "ASX": "B", "GLX": "Z", "XAA": "X",
    "XLE": "J", "MSE": "M",  # selenomethionine, common in crystallography
}
ONE_TO_THREE = {v: k.capitalize() for k, v in THREE_TO_ONE.items()}

#: Monoisotopic average residue masses in Da, for molecular weight.
_AA_MASS = {
    "A": 71.0788, "R": 156.1875, "N": 114.1038, "D": 115.0886, "C": 103.1388,
    "E": 129.1155, "Q": 128.1307, "G": 57.0519, "H": 137.1411, "I": 113.1594,
    "L": 113.1594, "K": 128.1741, "M": 131.1926, "F": 147.1766, "P": 97.1167,
    "S": 87.0782, "T": 101.1051, "W": 186.2132, "Y": 163.1760, "V": 99.1326,
    "U": 150.0379, "O": 237.3018,
}
_WATER_MASS = 18.0153

#: Kyte-Doolittle hydropathy, used for GRAVY.
_KD_HYDROPATHY = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5,
    "E": -3.5, "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9,
    "M": 1.9, "F": 2.8, "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9,
    "Y": -1.3, "V": 4.2,
}

#: Matches a substitution in one-letter HGVS-like shorthand: K27M, p.K27M.
_SUBSTITUTION_RE = re.compile(
    r"^(?:p\.)?(?P<wt>[A-Z])(?P<pos>\d+)(?P<mut>[A-Z*])$"
)
#: Three-letter form: p.Lys27Met
_SUBSTITUTION_3_RE = re.compile(
    r"^(?:p\.)?(?P<wt>[A-Z][a-z]{2})(?P<pos>\d+)(?P<mut>[A-Z][a-z]{2}|Ter)$"
)


class SequenceError(ValueError):
    """A sequence or variant could not be parsed or applied."""


@dataclass(frozen=True)
class Variant:
    """A single amino-acid substitution, in 1-based residue numbering.

    1-based because that is what every structure file, paper and oligo order
    form uses. Converting to 0-based happens once, inside `apply_to`.

    Attributes:
        position: 1-based residue index in the parent sequence.
        wildtype: Expected parent residue, one-letter.
        mutant: Replacement residue, one-letter. `*` introduces a stop.
    """

    position: int
    wildtype: str
    mutant: str

    def __post_init__(self) -> None:
        if self.position < 1:
            raise SequenceError(
                f"variant position must be 1-based (>= 1), got {self.position}"
            )
        for residue, label in ((self.wildtype, "wildtype"), (self.mutant, "mutant")):
            if residue not in VALID_AA:
                raise SequenceError(
                    f"{label} residue {residue!r} is not a valid amino acid code"
                )

    @classmethod
    def parse(cls, text: str) -> "Variant":
        """Parse `K27M`, `p.K27M` or `p.Lys27Met`.

        Raises:
            SequenceError: If the notation is not recognised.
        """
        token = text.strip()
        match = _SUBSTITUTION_RE.match(token)
        if match:
            return cls(
                position=int(match.group("pos")),
                wildtype=match.group("wt"),
                mutant=match.group("mut"),
            )
        match = _SUBSTITUTION_3_RE.match(token)
        if match:
            wt = THREE_TO_ONE.get(match.group("wt").upper())
            raw_mut = match.group("mut")
            mut = "*" if raw_mut == "Ter" else THREE_TO_ONE.get(raw_mut.upper())
            if wt and mut:
                return cls(int(match.group("pos")), wt, mut)
        raise SequenceError(
            f"could not parse variant {text!r}; expected forms like "
            "'K27M', 'p.K27M' or 'p.Lys27Met'"
        )

    def __str__(self) -> str:
        return f"{self.wildtype}{self.position}{self.mutant}"

    @property
    def is_nonsense(self) -> bool:
        """True if this introduces a premature stop."""
        return self.mutant == "*"

    @property
    def is_synonymous(self) -> bool:
        return self.wildtype == self.mutant


@dataclass
class ProteinSequence:
    """An amino-acid sequence with provenance.

    Attributes:
        sequence: Uppercase one-letter residues, no whitespace.
        identifier: Short id, e.g. a UniProt accession or construct name.
        description: Free-text, e.g. the FASTA header remainder.
        variants: Mutations applied to reach this sequence from its parent.
        parent_id: Identifier of the sequence these variants were applied to.
    """

    sequence: str
    identifier: str = ""
    description: str = ""
    variants: List[Variant] = field(default_factory=list)
    parent_id: Optional[str] = None

    def __post_init__(self) -> None:
        cleaned = re.sub(r"\s+", "", self.sequence).upper()
        invalid = sorted(set(cleaned) - VALID_AA)
        if invalid:
            raise SequenceError(
                f"sequence {self.identifier or '<unnamed>'} contains "
                f"non-amino-acid characters: {invalid}. If this is a "
                "nucleotide sequence, translate it first."
            )
        self.sequence = cleaned

    def __len__(self) -> int:
        return len(self.sequence)

    def __str__(self) -> str:
        return self.sequence

    def residue_at(self, position: int) -> str:
        """Residue at a 1-based position.

        Raises:
            IndexError: If `position` is outside the sequence.
        """
        if not 1 <= position <= len(self.sequence):
            raise IndexError(
                f"position {position} outside sequence {self.identifier!r} "
                f"of length {len(self.sequence)} (positions are 1-based)"
            )
        return self.sequence[position - 1]

    def apply(self, variants: Iterable[Variant | str]) -> "ProteinSequence":
        """Return a new sequence with `variants` applied.

        Validates each variant's wildtype residue against this sequence, which
        is how off-by-one numbering errors get caught before an experiment is
        ordered rather than after.

        Args:
            variants: `Variant` objects or parseable strings like "K27M".

        Returns:
            A new `ProteinSequence`; this one is unchanged.

        Raises:
            SequenceError: If a wildtype residue does not match, two variants
                target the same position, or a position is out of range.
        """
        parsed = [v if isinstance(v, Variant) else Variant.parse(v) for v in variants]

        seen: Dict[int, Variant] = {}
        for variant in parsed:
            if variant.position in seen:
                raise SequenceError(
                    f"two variants target position {variant.position}: "
                    f"{seen[variant.position]} and {variant}"
                )
            seen[variant.position] = variant

        residues = list(self.sequence)
        for variant in parsed:
            try:
                actual = self.residue_at(variant.position)
            except IndexError as exc:
                raise SequenceError(
                    f"variant {variant} is outside {self.identifier or '<unnamed>'}: "
                    f"{exc}"
                ) from exc
            if actual != variant.wildtype:
                raise SequenceError(
                    f"variant {variant} does not match the sequence: position "
                    f"{variant.position} is {actual!r}, not {variant.wildtype!r}. "
                    "Check the numbering convention (mature protein vs. including "
                    "the signal peptide or initiator methionine)."
                )
            residues[variant.position - 1] = variant.mutant

        mutated = "".join(residues)
        # A nonsense variant truncates; keeping residues past the stop would
        # misrepresent the construct that would actually be expressed.
        if "*" in mutated:
            mutated = mutated[: mutated.index("*")]

        label = ",".join(str(v) for v in parsed)
        return ProteinSequence(
            sequence=mutated,
            identifier=f"{self.identifier}_{label}" if self.identifier else label,
            description=(
                f"{self.description} [{label}]" if self.description else label
            ),
            variants=[*self.variants, *parsed],
            parent_id=self.identifier or self.parent_id,
        )

    def molecular_weight(self) -> float:
        """Average molecular weight in Daltons.

        Raises:
            SequenceError: If the sequence contains ambiguity codes, whose
                mass is undefined. Returning an approximate number here would
                be the same error as the fabricated results elsewhere.
        """
        unknown = sorted(set(self.sequence) - set(_AA_MASS))
        if unknown:
            raise SequenceError(
                f"cannot compute molecular weight: ambiguous residues {unknown} "
                "have no defined mass. Resolve them first."
            )
        return sum(_AA_MASS[r] for r in self.sequence) + _WATER_MASS

    def gravy(self) -> float:
        """Grand average of hydropathy (Kyte-Doolittle).

        Negative is hydrophilic, positive hydrophobic. Residues without a
        published value (ambiguity codes) are excluded from the average.

        Raises:
            SequenceError: If no residue has a hydropathy value.
        """
        scored = [_KD_HYDROPATHY[r] for r in self.sequence if r in _KD_HYDROPATHY]
        if not scored:
            raise SequenceError("no residues with a defined hydropathy value")
        return sum(scored) / len(scored)

    def composition(self) -> Dict[str, int]:
        """Residue counts, descending by frequency."""
        counts: Dict[str, int] = {}
        for residue in self.sequence:
            counts[residue] = counts.get(residue, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

    def to_fasta(self, line_width: int = 60) -> str:
        """Render as a FASTA record."""
        header = f">{self.identifier or 'sequence'}"
        if self.description:
            header += f" {self.description}"
        lines = [
            self.sequence[i : i + line_width]
            for i in range(0, len(self.sequence), line_width)
        ] or [""]
        return "\n".join([header, *lines]) + "\n"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identifier": self.identifier,
            "description": self.description,
            "length": len(self),
            "sequence": self.sequence,
            "variants": [str(v) for v in self.variants],
            "parent_id": self.parent_id,
        }


def parse_fasta(source: str | Path | TextIO) -> List[ProteinSequence]:
    """Parse FASTA text, a path, or an open handle.

    A `str` is ALWAYS treated as FASTA text and a `Path` as a file. Sniffing
    whether a string is a filename or a sequence guesses wrong in both
    directions — a bare residue string looks like a relative path, and a path
    that does not exist looks like malformed text — so the distinction is
    carried by the type instead. Use `parse_fasta_file` for a path held as a
    string.

    Accepts `*` for stops and `-`/`.` for alignment gaps; gaps are stripped,
    since a gapped row belongs to an alignment rather than a sequence.

    Args:
        source: FASTA text, a `Path` to a FASTA file, or a readable handle.

    Returns:
        One `ProteinSequence` per record, in file order.

    Raises:
        SequenceError: If the input has no FASTA header, a record has an empty
            body, or a residue code is invalid.
    """
    if isinstance(source, Path):
        text = source.read_text()
    elif isinstance(source, str):
        text = source
    else:
        text = source.read()

    if ">" not in text:
        raise SequenceError(
            "input contains no FASTA header line (expected a line starting "
            "with '>')"
        )

    records: List[ProteinSequence] = []
    header: Optional[str] = None
    body: List[str] = []

    def flush() -> None:
        if header is None:
            return
        raw = "".join(body).replace("-", "").replace(".", "")
        identifier, _, description = header.partition(" ")
        if not raw:
            raise SequenceError(
                f"FASTA record {identifier!r} has a header but no sequence"
            )
        records.append(
            ProteinSequence(
                sequence=raw,
                identifier=identifier,
                description=description.strip(),
            )
        )

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith((";", "#")):
            continue
        if line.startswith(">"):
            flush()
            header = line[1:].strip()
            body = []
        else:
            body.append(line)
    flush()

    if not records:
        raise SequenceError("no FASTA records found")
    return records


def parse_fasta_file(path: str | Path) -> List[ProteinSequence]:
    """Parse a FASTA file by path.

    Args:
        path: Filesystem path to a FASTA file.

    Returns:
        One `ProteinSequence` per record.

    Raises:
        FileNotFoundError: If the path does not exist.
        SequenceError: If the file is not valid FASTA.
    """
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"no such FASTA file: {resolved}")
    return parse_fasta(resolved)


def write_fasta(
    sequences: Sequence[ProteinSequence],
    destination: Optional[str | Path] = None,
    line_width: int = 60,
) -> str:
    """Render sequences as FASTA, optionally writing to a file.

    Args:
        sequences: Records to write.
        destination: If given, the text is also written here.
        line_width: Residues per line.

    Returns:
        The FASTA text.

    Raises:
        ValueError: If `sequences` is empty.
    """
    if not sequences:
        raise ValueError("nothing to write: sequences is empty")
    text = "".join(s.to_fasta(line_width=line_width) for s in sequences)
    if destination is not None:
        Path(destination).write_text(text)
    return text
