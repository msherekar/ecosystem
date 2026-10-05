"""UniProt REST client.

Uses `httpx.MockTransport` so the suite is hermetic — these tests must not
depend on network access or on UniProt being up.
"""

import json

import httpx
import pytest

from gliaent.protein.uniprot import (
    UniProtEntry,
    UniProtError,
    fetch_uniprot_entry,
    search_uniprot,
)

# Shaped like a real /uniprotkb/search response, trimmed to the fields the
# client requests.
P61626 = {
    "primaryAccession": "P61626",
    "uniProtkbId": "LYSC_HUMAN",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Lysozyme C"}}
    },
    "genes": [{"geneName": {"value": "LYZ"}, "synonyms": [{"value": "LZM"}]}],
    "organism": {"scientificName": "Homo sapiens"},
    "sequence": {"value": "KVFERCELARTLKRLGMDGYRGISLANWMCLAKWESGYNTRA", "length": 148},
    "comments": [
        {
            "commentType": "FUNCTION",
            "texts": [{"value": "Bacteriolytic enzyme."}],
        },
        {
            "commentType": "SUBCELLULAR LOCATION",
            "subcellularLocations": [{"location": {"value": "Secreted"}}],
        },
    ],
    "uniProtKBCrossReferences": [
        {"database": "PDB", "id": "1REX"},
        {"database": "PDB", "id": "1LZ1"},
        {"database": "AlphaFoldDB", "id": "P61626"},
    ],
}

# A sparse TrEMBL entry: no recommended name, no genes, no comments.
SPARSE = {
    "primaryAccession": "A0A000",
    "uniProtkbId": "A0A000_9XXXX",
    "entryType": "UniProtKB unreviewed (TrEMBL)",
    "sequence": {"value": "MKV", "length": 3},
}


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _ok(payload):
    return lambda request: httpx.Response(200, json=payload)


class TestSearch:
    def test_parses_a_full_entry(self):
        result = search_uniprot(
            "lysozyme", client=_client(_ok({"results": [P61626]}))
        )
        assert result["count"] == 1
        entry = result["hits"][0]
        assert entry.accession == "P61626"
        assert entry.entry_name == "LYSC_HUMAN"
        assert entry.protein_name == "Lysozyme C"
        assert entry.gene == "LYZ"
        assert entry.gene_names == ["LYZ", "LZM"]
        assert entry.organism == "Homo sapiens"
        assert entry.length == 148
        assert entry.reviewed is True
        assert entry.function == "Bacteriolytic enzyme."
        assert entry.subcellular_location == "Secreted"

    def test_the_query_actually_reaches_the_api(self):
        """The mock this replaces ignored the query entirely."""
        seen = {}

        def handler(request):
            seen["query"] = dict(httpx.QueryParams(request.url.query))["query"]
            return httpx.Response(200, json={"results": []})

        search_uniprot("lysozyme", client=_client(handler))
        assert "lysozyme" in seen["query"]

    def test_results_are_not_canned(self):
        """Different queries must be able to return different things."""
        def handler(request):
            query = dict(httpx.QueryParams(request.url.query))["query"]
            payload = {"results": [P61626]} if "lysozyme" in query else {"results": []}
            return httpx.Response(200, json=payload)

        client = _client(handler)
        assert search_uniprot("lysozyme", client=client)["count"] == 1
        assert search_uniprot("not_a_protein", client=client)["count"] == 0

    def test_extracts_pdb_ids_only(self):
        entry = search_uniprot("x", client=_client(_ok({"results": [P61626]})))["hits"][0]
        assert entry.pdb_ids == ["1REX", "1LZ1"]
        assert entry.has_structure

    def test_sparse_trembl_entry_does_not_crash(self):
        entry = search_uniprot("x", client=_client(_ok({"results": [SPARSE]})))["hits"][0]
        assert entry.accession == "A0A000"
        assert entry.reviewed is False
        assert entry.protein_name == ""
        assert entry.gene == ""
        assert entry.pdb_ids == []
        assert not entry.has_structure

    def test_empty_results_is_a_count_of_zero_not_an_error(self):
        result = search_uniprot("zzzz", client=_client(_ok({"results": []})))
        assert result["count"] == 0
        assert result["hits"] == []

    def test_reviewed_only_filter_is_applied(self):
        seen = {}

        def handler(request):
            seen["query"] = dict(httpx.QueryParams(request.url.query))["query"]
            return httpx.Response(200, json={"results": []})

        search_uniprot("lysozyme", reviewed_only=True, client=_client(handler))
        assert "reviewed:true" in seen["query"]

    def test_organism_filter_is_applied(self):
        seen = {}

        def handler(request):
            seen["query"] = dict(httpx.QueryParams(request.url.query))["query"]
            return httpx.Response(200, json={"results": []})

        search_uniprot("lysozyme", organism_id=9606, client=_client(handler))
        assert "organism_id:9606" in seen["query"]

    def test_url_uses_the_current_uniprotkb_path(self):
        entry = search_uniprot("x", client=_client(_ok({"results": [P61626]})))["hits"][0]
        # The old code built /uniprot/<acc>, which now only redirects.
        assert entry.url == "https://www.uniprot.org/uniprotkb/P61626"

    def test_to_dict_is_json_serialisable(self):
        entry = search_uniprot("x", client=_client(_ok({"results": [P61626]})))["hits"][0]
        json.dumps(entry.to_dict())


class TestSearchErrors:
    @pytest.mark.parametrize("query", ["", "   "])
    def test_blank_query_rejected(self, query):
        with pytest.raises(ValueError, match="non-empty"):
            search_uniprot(query)

    @pytest.mark.parametrize("size", [0, -1, 501])
    def test_page_size_out_of_range_rejected(self, size):
        with pytest.raises(ValueError, match="page_size"):
            search_uniprot("lysozyme", page_size=size)

    def test_server_error_raises_rather_than_returning_empty(self):
        """A failure must not be indistinguishable from "no hits"."""
        handler = lambda request: httpx.Response(500, text="boom")
        with pytest.raises(UniProtError, match="500"):
            search_uniprot("lysozyme", client=_client(handler))

    def test_network_failure_raises(self):
        def handler(request):
            raise httpx.ConnectError("no route to host")

        with pytest.raises(UniProtError, match="request failed"):
            search_uniprot("lysozyme", client=_client(handler))

    def test_non_json_response_raises(self):
        handler = lambda request: httpx.Response(200, text="<html>nope</html>")
        with pytest.raises(UniProtError, match="non-JSON"):
            search_uniprot("lysozyme", client=_client(handler))


class TestFetchEntry:
    def test_fetches_by_accession(self):
        entry = fetch_uniprot_entry("P61626", client=_client(_ok(P61626)))
        assert isinstance(entry, UniProtEntry)
        assert entry.accession == "P61626"
        assert entry.sequence.startswith("KVFERCELAR")

    def test_accession_is_normalised(self):
        seen = {}

        def handler(request):
            seen["path"] = request.url.path
            return httpx.Response(200, json=P61626)

        fetch_uniprot_entry("  p61626 ", client=_client(handler))
        assert seen["path"].endswith("/P61626")

    def test_unknown_accession_raises(self):
        handler = lambda request: httpx.Response(404, text="not found")
        with pytest.raises(UniProtError, match="no UniProt entry"):
            fetch_uniprot_entry("P99999", client=_client(handler))

    def test_blank_accession_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            fetch_uniprot_entry("")


class TestStreamlitAdapter:
    """The module-level adapter must not leak exceptions into `hits`."""

    def test_error_path_still_provides_an_empty_hits_list(self, monkeypatch):
        import gliaent.protein.uniprot as core

        def boom(*args, **kwargs):
            raise UniProtError("upstream down")

        monkeypatch.setattr(core, "search_uniprot", boom)
        # Import inside the test: the adapter imports streamlit at module load.
        pytest.importorskip("streamlit")
        from modules.search.uniprot import uniprot_search

        result = uniprot_search("lysozyme")
        assert result["hits"] == []
        assert "upstream down" in result["error"]
