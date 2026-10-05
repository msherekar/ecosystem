"""Protein science domain.

Sequences, structures, variants, and clients for the public protein
databases. Pure: no Streamlit, no FastAPI.
"""

from .sequence import (
    ProteinSequence,
    SequenceError,
    Variant,
    parse_fasta,
    parse_fasta_file,
    write_fasta,
)
from .uniprot import UniProtEntry, UniProtError, search_uniprot, fetch_uniprot_entry

__all__ = [
    "ProteinSequence",
    "SequenceError",
    "Variant",
    "parse_fasta",
    "parse_fasta_file",
    "write_fasta",
    "UniProtEntry",
    "UniProtError",
    "search_uniprot",
    "fetch_uniprot_entry",
]
