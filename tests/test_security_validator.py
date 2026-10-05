"""Handler input validation.

Covers both directions of the old denylist's failure: it rejected valid
scientific language, and it did not stop anything real.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcp.servers.handlers.security_validator import (  # noqa: E402
    DEFAULT_ALLOWED_EXTENSIONS,
    SecurityValidator,
)


@pytest.fixture
def validator(tmp_path):
    return SecurityValidator(audit_log_path=str(tmp_path / "audit.log"))


class TestOrdinaryScientificLanguageIsAccepted:
    """The denylist rejected all of these as injection attempts."""

    @pytest.mark.parametrize(
        "value",
        [
            "run evaluation of the binding curves",
            "delete the outlier samples",
            "import my counts matrix",
            "update the metadata table",
            "insert a gap at position 42",
            "compile the results into one figure",
            "drop replicate 3",
            "the executive summary",
            "medieval protein evolution",
            "os. 2 mg/mL stock",
            "exec summary for the PI",
        ],
    )
    def test_accepted(self, validator, value):
        result = validator.validate_parameters({"note": value})
        assert result["valid"], result["errors"]


class TestParameterValidation:
    def test_bad_parameter_name_rejected(self, validator):
        assert not validator.validate_parameters({"bad name!": 1})["valid"]

    @pytest.mark.parametrize("name", ["resolution", "n_neighbors", "log2fc-threshold"])
    def test_identifier_names_accepted(self, validator, name):
        assert validator.validate_parameters({name: 0.5})["valid"]

    def test_absurdly_long_value_rejected(self, validator):
        result = validator.validate_parameters({"seq": "A" * 200_000})
        assert not result["valid"]
        assert "over the" in result["errors"][0]

    def test_a_real_protein_sequence_is_not_too_long(self, validator):
        # Titin is ~34,350 aa, the longest human protein. It must fit.
        assert validator.validate_parameters({"seq": "A" * 34_350})["valid"]

    def test_list_values_are_checked(self, validator):
        assert not validator.validate_parameters(
            {"seqs": ["ok", "A" * 200_000]}
        )["valid"]

    def test_empty_params_are_valid(self, validator):
        assert validator.validate_parameters({})["valid"]


class TestUploadAllowlist:
    @pytest.mark.parametrize(
        "filename",
        [
            "structure.pdb",
            "complex.cif",
            "model.mmcif",
            "seqs.fasta",
            "protein.fa",
            "chain.faa",
            "alignment.a3m",
            "msa.sto",
            "ligand.sdf",
            "docked.pdbqt",
        ],
    )
    def test_protein_formats_are_accepted(self, validator, filename):
        """None of these could be uploaded before."""
        result = validator.validate_file_upload(filename, 1024)
        assert result["valid"], result["errors"]

    @pytest.mark.parametrize(
        "filename", ["counts.csv", "matrix.tsv", "adata.h5ad", "run.mzml"]
    )
    def test_existing_formats_still_work(self, validator, filename):
        assert validator.validate_file_upload(filename, 1024)["valid"]

    def test_compression_looks_through_to_the_real_extension(self, validator):
        result = validator.validate_file_upload("counts.csv.gz", 1024)
        assert result["valid"]
        assert result["extension"] == ".csv"

    def test_compressed_unsupported_type_still_rejected(self, validator):
        assert not validator.validate_file_upload("payload.exe.gz", 1024)["valid"]

    @pytest.mark.parametrize("filename", ["evil.exe", "script.sh", "lib.so", "noext"])
    def test_unsupported_types_rejected(self, validator, filename):
        assert not validator.validate_file_upload(filename, 1024)["valid"]

    @pytest.mark.parametrize(
        "filename", ["../../etc/passwd.csv", "/etc/shadow.csv", "a/b.csv", "..\\x.csv"]
    )
    def test_paths_in_filenames_rejected(self, validator, filename):
        assert not validator.validate_file_upload(filename, 1024)["valid"]

    def test_dotfile_rejected(self, validator):
        assert not validator.validate_file_upload(".env", 10)["valid"]

    def test_empty_filename_rejected(self, validator):
        assert not validator.validate_file_upload("", 10)["valid"]

    def test_oversized_upload_rejected(self, validator):
        result = validator.validate_file_upload("big.h5ad", 5 * 1024**3)
        assert not result["valid"]
        assert "GB" in result["errors"][0]

    def test_a_large_but_plausible_omics_file_is_accepted(self, validator):
        """The old 100 MB cap rejected ordinary single-cell datasets."""
        assert validator.validate_file_upload("adata.h5ad", 900 * 1024**2)["valid"]

    def test_negative_size_rejected(self, validator):
        assert not validator.validate_file_upload("x.csv", -1)["valid"]

    def test_allowlist_covers_both_domains(self):
        assert ".pdb" in DEFAULT_ALLOWED_EXTENSIONS
        assert ".h5ad" in DEFAULT_ALLOWED_EXTENSIONS


class TestRateLimit:
    def test_allows_up_to_the_limit(self, tmp_path):
        v = SecurityValidator(
            audit_log_path=str(tmp_path / "a.log"), max_operations_per_minute=5
        )
        assert all(v.check_rate_limit("op") for _ in range(5))

    def test_blocks_beyond_the_limit(self, tmp_path):
        v = SecurityValidator(
            audit_log_path=str(tmp_path / "a.log"), max_operations_per_minute=3
        )
        for _ in range(3):
            v.check_rate_limit("op")
        assert not v.check_rate_limit("op")

    def test_keys_are_independent(self, tmp_path):
        v = SecurityValidator(
            audit_log_path=str(tmp_path / "a.log"), max_operations_per_minute=2
        )
        v.check_rate_limit("a")
        v.check_rate_limit("a")
        assert v.check_rate_limit("b")

    def test_idle_keys_are_evicted(self, validator):
        """The dict previously grew without bound, one entry per identifier."""
        for i in range(50):
            validator.check_rate_limit(f"key-{i}")
        stale = datetime.now(timezone.utc).replace(year=2000)
        for window in validator._operation_counts.values():
            window.clear()
            window.append(stale)
        validator.check_rate_limit("fresh")
        assert validator.get_security_report()["tracked_operation_keys"] <= 2

    def test_is_thread_safe(self, tmp_path):
        import threading

        v = SecurityValidator(
            audit_log_path=str(tmp_path / "a.log"), max_operations_per_minute=1000
        )
        allowed = []

        def hammer():
            for _ in range(100):
                allowed.append(v.check_rate_limit("shared"))

        threads = [threading.Thread(target=hammer) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # 800 attempts against a 1000 budget: all allowed, none lost.
        assert len(allowed) == 800
        assert all(allowed)


class TestAuditTrail:
    def test_parameters_are_recorded_not_hashed(self, validator, tmp_path):
        """A hash cannot reconstruct what was run."""
        validator.audit_operation(
            "scrnaseq", "cluster", {"resolution": 0.8, "seed": 42}
        )
        for handler in validator.security_logger.handlers:
            handler.flush()
        log = (tmp_path / "audit.log").read_text()
        assert "resolution" in log
        assert "0.8" in log
        assert "42" in log

    def test_large_values_are_summarised_not_dropped(self, validator, tmp_path):
        validator.audit_operation("x", "y", {"seq": "A" * 10_000})
        for handler in validator.security_logger.handlers:
            handler.flush()
        log = (tmp_path / "audit.log").read_text()
        assert "10000 chars total" in log

    def test_dataframe_is_summarised_by_shape(self, validator, tmp_path):
        pd = pytest.importorskip("pandas")
        validator.audit_operation(
            "x", "y", {"data": pd.DataFrame({"a": [1, 2, 3]})}
        )
        for handler in validator.security_logger.handlers:
            handler.flush()
        assert "shape" in (tmp_path / "audit.log").read_text()

    def test_handlers_are_not_duplicated_across_instances(self, tmp_path):
        """N instances previously meant N file handlers on one global logger."""
        path = str(tmp_path / "shared.log")
        first = SecurityValidator(audit_log_path=path)
        before = len(first.security_logger.handlers)
        for _ in range(5):
            SecurityValidator(audit_log_path=path)
        assert len(first.security_logger.handlers) == before

    def test_unwritable_log_directory_does_not_raise(self, tmp_path):
        blocked = tmp_path / "ro"
        blocked.mkdir()
        blocked.chmod(0o500)
        try:
            SecurityValidator(audit_log_path=str(blocked / "sub" / "audit.log"))
        finally:
            blocked.chmod(0o700)


def test_report_window_matches_what_is_retained(validator):
    """The old report counted "last hour" over 60-second data."""
    validator.check_rate_limit("op")
    report = validator.get_security_report()
    assert report["operations_last_minute"] == 1
    assert "operations_last_minute" in report
