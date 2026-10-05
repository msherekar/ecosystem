"""Protein sequence primitives, FASTA I/O, and variants."""

import pytest

from gliaent.protein.sequence import (
    ProteinSequence,
    SequenceError,
    Variant,
    parse_fasta,
    parse_fasta_file,
    write_fasta,
)

# Human lysozyme C, mature chain (UniProt P61626, residues 19-148).
LYSOZYME = (
    "KVFERCELARTLKRLGMDGYRGISLANWMCLAKWESGYNTRATNYNAGDRSTDYGIFQINS"
    "RYWCNDGKTPGAVNACHLSCSALLQDNIADAVACAKRVVRDPQGIRAWVAWRNRCQNRDVR"
    "QYVQGCGV"
)


class TestVariantParsing:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("K27M", (27, "K", "M")),
            ("p.K27M", (27, "K", "M")),
            ("p.Lys27Met", (27, "K", "M")),
            ("C215S", (215, "C", "S")),
            ("W1*", (1, "W", "*")),
            ("p.Trp26Ter", (26, "W", "*")),
        ],
    )
    def test_parses_accepted_notations(self, text, expected):
        variant = Variant.parse(text)
        assert (variant.position, variant.wildtype, variant.mutant) == expected

    @pytest.mark.parametrize(
        "text", ["", "27", "K27", "KM", "Z", "K-1M", "Kxx27Met", "p.K27"]
    )
    def test_rejects_unparseable(self, text):
        with pytest.raises(SequenceError, match="could not parse variant"):
            Variant.parse(text)

    def test_zero_or_negative_position_rejected(self):
        # 1-based numbering is a hard invariant: structures and papers use it.
        with pytest.raises(SequenceError, match="1-based"):
            Variant(position=0, wildtype="K", mutant="M")

    def test_invalid_residue_rejected(self):
        with pytest.raises(SequenceError, match="not a valid amino acid"):
            Variant(position=5, wildtype="K", mutant="1")

    def test_str_round_trips(self):
        assert str(Variant.parse("p.Lys27Met")) == "K27M"

    def test_nonsense_and_synonymous_flags(self):
        assert Variant.parse("W26*").is_nonsense
        assert Variant.parse("K27K").is_synonymous
        assert not Variant.parse("K27M").is_nonsense


class TestProteinSequence:
    def test_whitespace_and_case_are_normalised(self):
        seq = ProteinSequence("  mkv faa\nlk ")
        assert seq.sequence == "MKVFAALK"
        assert len(seq) == 8

    def test_rejects_nucleotide_input_with_a_useful_message(self):
        # A common user error: pasting DNA into a protein field. '1' is not a
        # valid code, but neither is a long run that is clearly nucleotides —
        # here we check the invalid-character path names the likely cause.
        with pytest.raises(SequenceError, match="translate it first"):
            ProteinSequence("ATGGCGZ1")

    def test_accepts_ambiguity_codes(self):
        assert len(ProteinSequence("MKVX")) == 4

    def test_residue_at_is_one_based(self):
        seq = ProteinSequence("MKVFAA")
        assert seq.residue_at(1) == "M"
        assert seq.residue_at(6) == "A"

    @pytest.mark.parametrize("position", [0, 7, -1, 100])
    def test_residue_at_out_of_range_raises(self, position):
        with pytest.raises(IndexError, match="1-based"):
            ProteinSequence("MKVFAA").residue_at(position)

    def test_molecular_weight_of_a_known_peptide(self):
        # Gly-Gly: 2 * 57.0519 + 18.0153
        assert ProteinSequence("GG").molecular_weight() == pytest.approx(132.1191, abs=1e-3)

    def test_molecular_weight_refuses_ambiguous_residues(self):
        # Returning an approximate mass here would be the same class of error
        # as the fabricated p-values: a plausible number with no basis.
        with pytest.raises(SequenceError, match="no defined mass"):
            ProteinSequence("MKVX").molecular_weight()

    def test_gravy_sign_is_right(self):
        assert ProteinSequence("IIVVLL").gravy() > 0  # hydrophobic
        assert ProteinSequence("RRKKDD").gravy() < 0  # hydrophilic

    def test_composition_is_sorted_by_frequency(self):
        composition = ProteinSequence("AAAKKM").composition()
        assert list(composition.items())[0] == ("A", 3)
        assert composition["K"] == 2


class TestApplyVariants:
    def test_applies_a_substitution(self):
        mutant = ProteinSequence(LYSOZYME, identifier="LYZ").apply(["C6S"])
        assert mutant.residue_at(6) == "S"
        assert len(mutant) == len(LYSOZYME)

    def test_parent_is_unchanged(self):
        parent = ProteinSequence(LYSOZYME, identifier="LYZ")
        parent.apply(["C6S"])
        assert parent.residue_at(6) == "C"
        assert parent.variants == []

    def test_records_lineage(self):
        mutant = ProteinSequence(LYSOZYME, identifier="LYZ").apply(["C6S", "K1M"])
        assert mutant.parent_id == "LYZ"
        assert [str(v) for v in mutant.variants] == ["C6S", "K1M"]
        assert "C6S" in mutant.identifier

    def test_wildtype_mismatch_is_caught(self):
        """The check that stops a mis-numbered mutant being ordered."""
        with pytest.raises(SequenceError, match="does not match the sequence"):
            ProteinSequence(LYSOZYME, identifier="LYZ").apply(["A6S"])

    def test_mismatch_message_mentions_numbering_conventions(self):
        with pytest.raises(SequenceError, match="signal peptide"):
            ProteinSequence(LYSOZYME).apply(["A6S"])

    def test_out_of_range_variant_is_caught(self):
        with pytest.raises(SequenceError, match="outside"):
            ProteinSequence("MKVFAA").apply(["A99G"])

    def test_duplicate_positions_rejected(self):
        with pytest.raises(SequenceError, match="two variants target position"):
            ProteinSequence(LYSOZYME).apply(["C6S", "C6A"])

    def test_nonsense_variant_truncates(self):
        mutant = ProteinSequence("MKVFAAGG").apply(["F4*"])
        assert mutant.sequence == "MKV"

    def test_accepts_variant_objects_and_strings(self):
        seq = ProteinSequence("MKVFAA")
        assert seq.apply([Variant(1, "M", "A")]).sequence == (
            seq.apply(["M1A"]).sequence
        )

    def test_variants_chain(self):
        once = ProteinSequence("MKVFAA", identifier="x").apply(["M1A"])
        twice = once.apply(["K2R"])
        assert twice.sequence == "ARVFAA"
        assert len(twice.variants) == 2


class TestFasta:
    def test_parses_a_single_record(self):
        records = parse_fasta(">LYZ human lysozyme\n" + LYSOZYME + "\n")
        assert len(records) == 1
        assert records[0].identifier == "LYZ"
        assert records[0].description == "human lysozyme"
        assert records[0].sequence == LYSOZYME

    def test_parses_multiple_records(self):
        text = ">a desc one\nMKV\nFAA\n>b desc two\nGGG\n"
        records = parse_fasta(text)
        assert [r.identifier for r in records] == ["a", "b"]
        assert records[0].sequence == "MKVFAA"

    def test_strips_alignment_gaps(self):
        assert parse_fasta(">a\nMK--V..F\n")[0].sequence == "MKVF"

    def test_ignores_blank_and_comment_lines(self):
        assert parse_fasta(">a\n\n; a comment\nMKV\n")[0].sequence == "MKV"

    def test_missing_header_raises(self):
        with pytest.raises(SequenceError, match="no FASTA header"):
            parse_fasta(LYSOZYME)

    def test_header_with_no_body_raises(self):
        with pytest.raises(SequenceError, match="no sequence"):
            parse_fasta(">a desc\n>b desc\nMKV\n")

    def test_reads_from_a_path(self, tmp_path):
        path = tmp_path / "x.fasta"
        path.write_text(">p1\nMKVFAA\n")
        assert parse_fasta(path)[0].sequence == "MKVFAA"

    def test_missing_path_raises_filenotfound(self):
        with pytest.raises(FileNotFoundError):
            parse_fasta_file("/nonexistent/path.fasta")

    def test_a_bare_sequence_string_is_text_not_a_path(self):
        """Regression: a residue string must not be sniffed as a filename."""
        with pytest.raises(SequenceError, match="no FASTA header"):
            parse_fasta(LYSOZYME)

    def test_parse_fasta_file_accepts_a_string_path(self, tmp_path):
        path = tmp_path / "s.fasta"
        path.write_text(">p\nMKV\n")
        assert parse_fasta_file(str(path))[0].sequence == "MKV"

    def test_round_trips(self):
        original = ProteinSequence(LYSOZYME, identifier="LYZ", description="lysozyme C")
        reparsed = parse_fasta(original.to_fasta())[0]
        assert reparsed.sequence == original.sequence
        assert reparsed.identifier == original.identifier
        assert reparsed.description == original.description

    def test_wraps_at_the_requested_width(self):
        body = ProteinSequence("A" * 130, identifier="x").to_fasta(line_width=60)
        lines = body.strip().split("\n")[1:]
        assert [len(line) for line in lines] == [60, 60, 10]

    def test_write_fasta_to_file(self, tmp_path):
        path = tmp_path / "out.fasta"
        seqs = [ProteinSequence("MKV", identifier="a"), ProteinSequence("GG", identifier="b")]
        write_fasta(seqs, path)
        assert len(parse_fasta(path)) == 2

    def test_write_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            write_fasta([])
