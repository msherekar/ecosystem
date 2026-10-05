"""UniProt search — Streamlit display adapter.

The actual client lives in `gliaent.protein.uniprot`, which has no Streamlit
dependency and is unit-tested. This module only adapts it to the search
registry's calling convention and renders results.

This file previously contained a mock that ignored the query and returned
hardcoded p53 and alpha-2-macroglobulin entries with the search string
interpolated into the protein name.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import streamlit as st

_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:  # pragma: no cover - import plumbing
    sys.path.insert(0, str(_SRC))

from gliaent.protein.uniprot import UniProtError, search_uniprot  # noqa: E402


def uniprot_search(query: str, page_size: int = 20) -> Dict[str, Any]:
    """Search UniProt and return registry-shaped results.

    Args:
        query: Free text or UniProt field syntax.
        page_size: Maximum hits to return.

    Returns:
        A dict with `hits` as plain dictionaries, so the display layer and any
        JSON consumer see the same shape. On failure, returns a dict with an
        `error` key AND an empty `hits` list, so callers that index `hits`
        do not raise a KeyError on the error path.
    """
    try:
        result = search_uniprot(query, page_size=page_size)
    except (UniProtError, ValueError) as exc:
        return {
            "count": 0,
            "term": query,
            "hits": [],
            "error": str(exc),
            "provider": "uniprot",
            "provider_display_name": "UniProt",
        }

    return {
        "count": result["count"],
        "term": result["query"],
        "page": 1,
        "page_size": page_size,
        "hits": [entry.to_dict() for entry in result["hits"]],
        "provider": "uniprot",
        "provider_display_name": "UniProt",
    }


def uniprot_display(results: Dict[str, Any]) -> None:
    """Render UniProt results in Streamlit.

    All interpolated values go through Streamlit's default escaping; the
    previous version passed `unsafe_allow_html=True` with protein names and
    descriptions straight from the API.
    """
    if results.get("error"):
        st.error(f"UniProt search failed: {results['error']}")
        return

    hits = results.get("hits", [])
    if not hits:
        st.warning("No UniProt proteins found.")
        return

    for hit in hits:
        st.markdown(f"**{hit.get('protein_name') or hit.get('accession', 'Unknown')}**")

        facts = []
        if hit.get("accession"):
            facts.append(f"**Accession:** `{hit['accession']}`")
        if hit.get("gene"):
            facts.append(f"**Gene:** {hit['gene']}")
        if hit.get("length"):
            facts.append(f"**Length:** {hit['length']} aa")
        if hit.get("organism"):
            facts.append(f"**Organism:** {hit['organism']}")
        # Render both states: the old code only showed a status when the
        # entry was reviewed, so "Unreviewed" was unreachable.
        facts.append(
            f"**Status:** {'Reviewed (Swiss-Prot)' if hit.get('reviewed') else 'Unreviewed (TrEMBL)'}"
        )
        st.markdown(" &nbsp;|&nbsp; ".join(facts))

        if hit.get("function"):
            st.markdown(f"*Function:* {hit['function']}")
        if hit.get("subcellular_location"):
            st.markdown(f"*Location:* {hit['subcellular_location']}")
        if hit.get("pdb_ids"):
            shown = ", ".join(hit["pdb_ids"][:8])
            more = f" (+{len(hit['pdb_ids']) - 8} more)" if len(hit["pdb_ids"]) > 8 else ""
            st.markdown(f"*Structures:* {shown}{more}")

        if hit.get("url"):
            st.markdown(f"[View in UniProt]({hit['url']})")
        st.markdown("---")
