"""UniProt REST client.

Replaces a mock that ignored the query entirely and returned hardcoded p53
and alpha-2-macroglobulin entries, with the user's search string interpolated
into the protein name so the fake result looked responsive. Searching
"lysozyme" returned "Cellular tumor antigen p53 - lysozyme".

API reference: https://www.uniprot.org/help/api_queries
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

UNIPROT_SEARCH_URL = "https://rest.uniprot.org/uniprotkb/search"
UNIPROT_ENTRY_URL = "https://rest.uniprot.org/uniprotkb/{accession}"

#: Fields requested from the API. Keeping this explicit keeps responses small
#: and makes the parse below total rather than defensive.
_FIELDS = ",".join(
    [
        "accession",
        "id",
        "protein_name",
        "gene_names",
        "organism_name",
        "length",
        "sequence",
        "reviewed",
        "cc_function",
        "cc_subcellular_location",
        "ft_binding",
        "xref_pdb",
    ]
)

DEFAULT_TIMEOUT = 20.0


class UniProtError(RuntimeError):
    """A UniProt request failed.

    Raised rather than returned, so a caller cannot mistake a failure for an
    empty result set.
    """


@dataclass
class UniProtEntry:
    """One UniProtKB entry.

    Attributes:
        accession: Stable primary accession, e.g. "P04637".
        entry_name: Mnemonic id, e.g. "P53_HUMAN".
        protein_name: Recommended full name.
        gene_names: All gene names, primary first.
        organism: Scientific name with common name where available.
        length: Residue count.
        sequence: The amino-acid sequence, if requested.
        reviewed: True for Swiss-Prot (manually curated), False for TrEMBL.
        function: Free-text function annotation.
        subcellular_location: Free-text localisation annotation.
        pdb_ids: Cross-referenced PDB structures, for the structure viewer.
    """

    accession: str
    entry_name: str = ""
    protein_name: str = ""
    gene_names: List[str] = field(default_factory=list)
    organism: str = ""
    length: Optional[int] = None
    sequence: str = ""
    reviewed: bool = False
    function: str = ""
    subcellular_location: str = ""
    pdb_ids: List[str] = field(default_factory=list)

    @property
    def gene(self) -> str:
        """The primary gene name, or empty string."""
        return self.gene_names[0] if self.gene_names else ""

    @property
    def url(self) -> str:
        """Canonical web URL.

        Uses the /uniprotkb/ path; the older /uniprot/ form redirects.
        """
        return f"https://www.uniprot.org/uniprotkb/{self.accession}"

    @property
    def has_structure(self) -> bool:
        return bool(self.pdb_ids)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accession": self.accession,
            "entry_name": self.entry_name,
            "protein_name": self.protein_name,
            "gene_names": list(self.gene_names),
            "gene": self.gene,
            "organism": self.organism,
            "length": self.length,
            "reviewed": self.reviewed,
            "function": self.function,
            "subcellular_location": self.subcellular_location,
            "pdb_ids": list(self.pdb_ids),
            "url": self.url,
        }


def _parse_entry(raw: Dict[str, Any]) -> UniProtEntry:
    """Convert one API record into a `UniProtEntry`.

    Written to tolerate missing optional blocks: UniProt omits annotation
    sections entirely rather than returning nulls, and TrEMBL entries carry
    far less than Swiss-Prot ones.
    """
    protein_name = (
        raw.get("proteinDescription", {})
        .get("recommendedName", {})
        .get("fullName", {})
        .get("value", "")
    )
    if not protein_name:
        submitted = raw.get("proteinDescription", {}).get("submissionNames") or []
        if submitted:
            protein_name = submitted[0].get("fullName", {}).get("value", "")

    gene_names: List[str] = []
    for gene in raw.get("genes", []) or []:
        primary = gene.get("geneName", {}).get("value")
        if primary:
            gene_names.append(primary)
        for synonym in gene.get("synonyms", []) or []:
            value = synonym.get("value")
            if value:
                gene_names.append(value)

    function = ""
    subcellular = ""
    for comment in raw.get("comments", []) or []:
        texts = comment.get("texts") or []
        value = texts[0].get("value", "") if texts else ""
        if comment.get("commentType") == "FUNCTION" and not function:
            function = value
        elif comment.get("commentType") == "SUBCELLULAR LOCATION" and not subcellular:
            locations = comment.get("subcellularLocations") or []
            if locations:
                subcellular = locations[0].get("location", {}).get("value", "")
            else:
                subcellular = value

    pdb_ids = [
        x.get("id", "")
        for x in raw.get("uniProtKBCrossReferences", []) or []
        if x.get("database") == "PDB" and x.get("id")
    ]

    sequence_block = raw.get("sequence", {}) or {}

    return UniProtEntry(
        accession=raw.get("primaryAccession", ""),
        entry_name=raw.get("uniProtkbId", ""),
        protein_name=protein_name,
        gene_names=gene_names,
        organism=raw.get("organism", {}).get("scientificName", ""),
        length=sequence_block.get("length"),
        sequence=sequence_block.get("value", ""),
        reviewed=raw.get("entryType", "").startswith("UniProtKB reviewed"),
        function=function,
        subcellular_location=subcellular,
        pdb_ids=pdb_ids,
    )


def search_uniprot(
    query: str,
    page_size: int = 25,
    reviewed_only: bool = False,
    organism_id: Optional[int] = None,
    client: Optional[httpx.Client] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Search UniProtKB.

    Args:
        query: A UniProt query string. Plain text works ("lysozyme"); so does
            field syntax ("gene:TP53 AND reviewed:true").
        page_size: Results per page, 1-500.
        reviewed_only: Restrict to Swiss-Prot. Usually what a biochemist
            wants, but off by default so searches do not silently hide
            TrEMBL-only proteins.
        organism_id: NCBI taxonomy id, e.g. 9606 for human.
        client: Inject an `httpx.Client` for testing or connection reuse.
        timeout: Per-request timeout in seconds.

    Returns:
        `{"query": str, "count": int, "hits": [UniProtEntry, ...],
          "provider": "uniprot"}`

    Raises:
        ValueError: If `query` is blank or `page_size` is out of range.
        UniProtError: On a network failure, timeout, or non-2xx response.
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not 1 <= page_size <= 500:
        raise ValueError(f"page_size must be in 1..500, got {page_size}")

    full_query = query.strip()
    if reviewed_only:
        full_query = f"({full_query}) AND reviewed:true"
    if organism_id is not None:
        full_query = f"({full_query}) AND organism_id:{organism_id}"

    params = {"query": full_query, "fields": _FIELDS, "size": page_size,
              "format": "json"}

    owns_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        response = client.get(UNIPROT_SEARCH_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise UniProtError(
            f"UniProt returned {exc.response.status_code} for query {full_query!r}"
        ) from exc
    except httpx.HTTPError as exc:
        raise UniProtError(f"UniProt request failed: {exc}") from exc
    except ValueError as exc:
        raise UniProtError(f"UniProt returned a non-JSON response: {exc}") from exc
    finally:
        if owns_client:
            client.close()

    hits = [_parse_entry(item) for item in payload.get("results", [])]
    logger.info("uniprot search %r returned %d hits", full_query, len(hits))
    return {
        "query": full_query,
        "count": len(hits),
        "hits": hits,
        "provider": "uniprot",
        "provider_display_name": "UniProt",
    }


def fetch_uniprot_entry(
    accession: str,
    client: Optional[httpx.Client] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> UniProtEntry:
    """Fetch one entry by accession.

    Args:
        accession: A UniProt accession such as "P04637".
        client: Inject an `httpx.Client` for testing or connection reuse.
        timeout: Per-request timeout in seconds.

    Returns:
        The parsed entry, including its amino-acid sequence.

    Raises:
        ValueError: If `accession` is blank.
        UniProtError: If the accession is unknown or the request fails.
    """
    if not accession or not accession.strip():
        raise ValueError("accession must be a non-empty string")
    accession = accession.strip().upper()

    owns_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        response = client.get(
            UNIPROT_ENTRY_URL.format(accession=accession),
            params={"fields": _FIELDS, "format": "json"},
        )
        if response.status_code == 404:
            raise UniProtError(f"no UniProt entry for accession {accession!r}")
        response.raise_for_status()
        return _parse_entry(response.json())
    except httpx.HTTPStatusError as exc:
        raise UniProtError(
            f"UniProt returned {exc.response.status_code} for {accession!r}"
        ) from exc
    except httpx.HTTPError as exc:
        raise UniProtError(f"UniProt request failed: {exc}") from exc
    finally:
        if owns_client:
            client.close()
