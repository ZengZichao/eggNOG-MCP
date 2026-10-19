"""
eggNOG API client.

This module encapsulates all HTTP interactions with the eggNOG 7 database
(https://eggnogdb.org).  eggNOG exposes a set of JSON API endpoints under
``/e7api/`` that are used by the front-end Vue.js application.  This client
targets those endpoints directly, which is far more reliable than scraping
HTML.

API endpoints discovered:
    /e7api/protein/{protid}/         — protein details + OGs + functions
    /e7api/og/{oid}/                  — orthologous group details
    /e7api/og_content/{oid}/          — proteins within an OG
    /e7api/clu_content/{cluid}/       — proteins within a protein family cluster
    /e7api/orthologs/{protid}/        — pairwise orthologs for a protein
    /e7api/suggest_entries/{query}/   — search / autocomplete

The stats page (``/stats/``) embeds summary numbers directly in HTML.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("eggnog_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# eggNOG serves both HTTP and HTTPS.  Some environments (e.g. behind certain
# proxies) may have TLS issues with eggnogdb.org; we default to HTTPS but the
# client can be configured to use HTTP.
DEFAULT_BASE_URL = "https://eggnogdb.org"
DOWNLOAD_URL = f"{DEFAULT_BASE_URL}/public/eggnog7"
API_PREFIX = "/e7api"
DEFAULT_TIMEOUT = 30.0
USER_AGENT = "eggNOG-MCP/0.1.0 (https://eggnogdb.org)"

# Regex to strip <span> highlight tags from search results
_SPAN_RE = re.compile(r"<\/?span[^>]*>")


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def _clean_text(text: str) -> str:
    """Remove HTML span highlight tags from search result text."""
    return _SPAN_RE.sub("", text).strip()


def _format_kegg_terms(kegg_ko: list) -> list[dict[str, Any]]:
    """Format the KEGG KO list from the API into structured dicts.

    API format: ``[[ko_id, confidence, symbol, description], ...]``
    """
    result = []
    for entry in kegg_ko or []:
        if isinstance(entry, list) and len(entry) >= 2:
            item: dict[str, Any] = {
                "ko_id": entry[0],
                "confidence": entry[1],
            }
            if len(entry) >= 3:
                item["symbol"] = entry[2]
            if len(entry) >= 4:
                item["description"] = entry[3]
            result.append(item)
    return result


def _format_go_terms(go_slim: list) -> list[dict[str, Any]]:
    """Format the GO slim list from the API into structured dicts.

    API format: ``[[go_id, confidence, description], ...]``
    """
    result = []
    for entry in go_slim or []:
        if isinstance(entry, list) and len(entry) >= 2:
            item: dict[str, Any] = {
                "go_id": entry[0],
                "confidence": entry[1],
            }
            if len(entry) >= 3:
                item["description"] = entry[2]
            result.append(item)
    return result


def _format_og_list(ogs: list) -> list[dict[str, Any]]:
    """Format a list of OG objects from the API."""
    result = []
    for og in ogs or []:
        if isinstance(og, dict):
            result.append(
                {
                    "og_id": og.get("n", ""),
                    "taxonomic_level": og.get("l", ""),
                    "species_count": og.get("ns", 0),
                    "protein_count": og.get("nm", 0),
                    "evolutionary_origin": og.get("lca", ""),
                    "level_name": og.get("name", ""),
                }
            )
    return result


def _format_og_groups(ogs_dict: dict) -> list[dict[str, Any]]:
    """Format the nested OG dict from the protein API.

    The protein API returns OGs grouped by protein family name:
    ``{"P53": [{n, ns, nm, lca, name}, ...], "P53_tetramer": [...]}`
    """
    result = []
    for family_name, og_list in (ogs_dict or {}).items():
        for og in og_list:
            if isinstance(og, dict):
                result.append(
                    {
                        "protein_family": family_name,
                        "og_id": og.get("n", ""),
                        "taxonomic_level": og.get("l", "") if "l" in og else "",
                        "species_count": og.get("ns", 0),
                        "protein_count": og.get("nm", 0),
                        "evolutionary_origin": og.get("lca", ""),
                        "level_name": og.get("name", ""),
                    }
                )
    return result


# ---------------------------------------------------------------------------
# Stats parsing (from HTML)
# ---------------------------------------------------------------------------
def _parse_stats_html(html: str) -> dict[str, Any]:
    """
    Parse the eggNOG stats page HTML.

    The stats page embeds summary numbers in Tailwind CSS cards:
        <p class="text-3xl font-bold text-yellow-600">12k+</p>
        <p class="text-gray-700 text-sm mt-1">Annotated Species</p>
    """
    stats: dict[str, Any] = {}

    label_map = {
        "Annotated Species": "annotated_species",
        "Protein Sequences": "protein_sequences",
        "Phylogenetic Trees": "phylogenetic_trees",
        "Orthologous Groups": "orthologous_groups",
    }

    # Match: <p ...>12k+</p> ... <p ...>Annotated Species</p>
    for label, key in label_map.items():
        # The value appears in a <p> tag just before the label <p> tag
        pattern = (
            r'<p[^>]*class="[^"]*font-bold[^"]*"[^>]*>\s*'
            r'([\d.,kM+]+)\s*</p>\s*'
            r'<p[^>]*class="[^"]*"[^>]*>\s*'
            + re.escape(label)
            + r'\s*</p>'
        )
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            stats[key] = m.group(1).strip()

    stats["version"] = "eggNOG 7"
    stats["url"] = f"{DEFAULT_BASE_URL}/stats/"
    return stats


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------
class eggNOGClient:
    """Asynchronous HTTP client for the eggNOG database."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self._timeout,
                verify=self._verify_ssl,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json, text/html, */*",
                },
                follow_redirects=True,
            )
        return self._client

    async def _fetch_json(self, path: str, *, params: dict | None = None) -> Any:
        """Fetch a JSON API endpoint and return the parsed result."""
        client = await self._get_client()
        logger.debug("Fetching JSON: %s params=%s", path, params)
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _fetch_text(self, path: str, *, params: dict | None = None) -> str:
        """Fetch a page and return its text content."""
        client = await self._get_client()
        logger.debug("Fetching text: %s params=%s", path, params)
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        return resp.text

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    #  Public API methods
    # ------------------------------------------------------------------
    async def get_protein(self, protein_id: str) -> dict[str, Any]:
        """
        Retrieve detailed information for a specific protein.

        ``protein_id`` should be in the eggNOG format ``taxid.seqid``,
        e.g. ``9606.ENSP00000269305`` (human P53).
        """
        try:
            data = await self._fetch_json(f"{API_PREFIX}/protein/{protein_id}/")
            focus_prot = data.get("focus_prot", {})
            focus_og = data.get("focus_og", {})
            focus_clu = data.get("focus_clu", {})

            # Build the result
            result: dict[str, Any] = {
                "protein_id": protein_id,
                "protein_name": focus_prot.get("bestname", ""),
                "species": focus_prot.get("sp", ""),
                "taxid": focus_prot.get("taxid", ""),
                "uniprot_id": focus_prot.get("ukb", ""),
                "pfam_domains": focus_prot.get("pfam", []),
                "kegg_ko": focus_prot.get("ko", []),
                "url": f"{self.base_url}/protein/{protein_id}/",
            }

            # Orthologous groups
            all_ogs = _format_og_groups(focus_prot.get("ogs", {}))
            if all_ogs:
                result["orthologous_groups"] = all_ogs
                result["protein_family"] = focus_clu.get("n", "")
                result["og_count"] = len(focus_clu.get("ogs", []))
                result["total_proteins_in_family"] = sum(
                    og.get("nm", 0) for og in focus_clu.get("ogs", [])
                )
                result["total_species_in_family"] = sum(
                    og.get("ns", 0) for og in focus_clu.get("ogs", [])
                )

            # Functional annotation from the selected OG
            top_func = focus_og.get("top_func", {})
            if top_func:
                result["predicted_functions"] = {
                    "kegg_ko": _format_kegg_terms(top_func.get("kegg_ko", [])),
                    "go_slim": _format_go_terms(top_func.get("GOslim", [])),
                    "kegg_gene_symbols": top_func.get("kegg_gsymbol", []),
                }
                result["selected_og"] = {
                    "og_id": focus_og.get("n", ""),
                    "evolutionary_origin": focus_og.get("lca", ""),
                    "protein_count": focus_og.get("nm", 0),
                    "species_count": focus_og.get("ns", 0),
                    "taxonomic_lineage": focus_og.get("nlin", []),
                }

            return result

        except httpx.HTTPStatusError as exc:
            return {
                "error": f"HTTP {exc.response.status_code} for protein '{protein_id}'",
                "detail": str(exc),
            }
        except httpx.ConnectError as exc:
            return {
                "error": (
                    f"Connection error for protein '{protein_id}'. "
                    "If you encounter TLS issues, try initializing the client "
                    "with verify_ssl=False."
                ),
                "detail": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "error": f"Failed to retrieve protein '{protein_id}'",
                "detail": str(exc),
            }

    async def get_orthologous_group(self, og_id: str) -> dict[str, Any]:
        """
        Retrieve information about a specific orthologous group (OG).

        ``og_id`` format: ``family@taxid|level``, e.g. ``P53@33154|A-1``.
        """
        try:
            data = await self._fetch_json(f"{API_PREFIX}/og/{quote(og_id, safe='')}/")
            focus_og = data.get("focus_og", {})
            focus_clu = data.get("focus_clu", {})

            result: dict[str, Any] = {
                "og_id": og_id,
                "protein_family": focus_og.get("clu", "") or focus_clu.get("n", ""),
                "evolutionary_origin": focus_og.get("lca", ""),
                "taxonomic_lineage": focus_og.get("nlin", []),
                "protein_count": focus_og.get("nm", 0),
                "species_count": focus_og.get("ns", 0),
                "level_name": focus_og.get("name", ""),
                "url": f"{self.base_url}/og/{og_id}",
            }

            # Functional annotation
            top_func = focus_og.get("top_func", {})
            if top_func:
                result["functional_annotation"] = {
                    "kegg_ko": _format_kegg_terms(top_func.get("kegg_ko", [])),
                    "go_slim": _format_go_terms(top_func.get("GOslim", [])),
                    "kegg_gene_symbols": top_func.get("kegg_gsymbol", []),
                }

            # All OGs in the same protein family
            family_ogs = _format_og_list(focus_clu.get("ogs", []))
            if family_ogs:
                result["family_orthologous_groups"] = family_ogs

            return result

        except httpx.HTTPStatusError as exc:
            return {
                "error": f"HTTP {exc.response.status_code} for OG '{og_id}'",
                "detail": str(exc),
            }
        except httpx.ConnectError as exc:
            return {
                "error": (
                    f"Connection error for OG '{og_id}'. "
                    "If you encounter TLS issues, try initializing the client "
                    "with verify_ssl=False."
                ),
                "detail": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Failed to retrieve OG '{og_id}'", "detail": str(exc)}

    async def get_og_content(self, og_id: str, max_species: int = 50) -> dict[str, Any]:
        """
        Retrieve the list of proteins within an orthologous group.

        Parameters
        ----------
        og_id : str
            OG ID in ``family@taxid|level`` format.
        max_species : int
            Maximum number of species to include (the full list can be very large).
        """
        try:
            data = await self._fetch_json(
                f"{API_PREFIX}/og_content/{quote(og_id, safe='')}/"
            )
            prots = data.get("prots", {})

            species_list = []
            total_proteins = 0
            for i, (species, protein_ids) in enumerate(prots.items()):
                if i >= max_species:
                    break
                unique_proteins = list(set(protein_ids))
                species_list.append(
                    {
                        "species": species,
                        "protein_count": len(protein_ids),
                        "unique_protein_count": len(unique_proteins),
                        "protein_ids": unique_proteins[:20],  # cap per species
                    }
                )
                total_proteins += len(protein_ids)

            return {
                "og_id": og_id,
                "total_species": len(prots),
                "total_proteins": total_proteins,
                "species": species_list,
                "truncated": len(prots) > max_species,
            }
        except httpx.HTTPStatusError as exc:
            return {
                "error": f"HTTP {exc.response.status_code} for OG content '{og_id}'",
                "detail": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "error": f"Failed to retrieve OG content for '{og_id}'",
                "detail": str(exc),
            }

    async def get_orthologs(self, protein_id: str, max_species: int = 50) -> dict[str, Any]:
        """
        Retrieve pairwise orthologs for a protein.

        Parameters
        ----------
        protein_id : str
            eggNOG protein ID in ``taxid.seqid`` format.
        max_species : int
            Maximum number of species to include.
        """
        try:
            data = await self._fetch_json(f"{API_PREFIX}/orthologs/{protein_id}/")
            orthologs = data.get("orthologs", {})

            species_list = []
            total_orthologs = 0
            for i, (species, protein_ids) in enumerate(orthologs.items()):
                if i >= max_species:
                    break
                unique_proteins = list(set(protein_ids))
                species_list.append(
                    {
                        "species": species,
                        "ortholog_count": len(protein_ids),
                        "unique_ortholog_count": len(unique_proteins),
                        "ortholog_protein_ids": unique_proteins[:10],
                    }
                )
                total_orthologs += len(protein_ids)

            return {
                "protein_id": protein_id,
                "total_ortholog_species": len(orthologs),
                "total_orthologs": total_orthologs,
                "orthologs_by_species": species_list,
                "truncated": len(orthologs) > max_species,
            }
        except httpx.HTTPStatusError as exc:
            return {
                "error": f"HTTP {exc.response.status_code} for orthologs of '{protein_id}'",
                "detail": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "error": f"Failed to retrieve orthologs for '{protein_id}'",
                "detail": str(exc),
            }

    async def search(self, query: str) -> dict[str, Any]:
        """
        Search the eggNOG database for proteins or orthologous groups.

        Uses the ``/e7api/suggest_entries/`` endpoint.  The query must be
        at least 3 characters long.
        """
        if len(query) < 3:
            return {
                "query": query,
                "error": "Search query must be at least 3 characters long.",
                "results": [],
            }
        try:
            data = await self._fetch_json(
                f"{API_PREFIX}/suggest_entries/{quote(query, safe='')}/"
            )
            raw_results = data.get("result", [])

            results: list[dict[str, Any]] = []
            for group in raw_results:
                if isinstance(group, dict):
                    group_name = group.get("groupName", "unknown")
                    for item in group.get("items", []):
                        results.append(
                            {
                                "type": item.get("type", group_name),
                                "id": item.get("name", ""),
                                "label": _clean_text(item.get("text", "")),
                                "url": f"{self.base_url}/{item.get('type', 'protein')}/{item.get('name', '')}",
                            }
                        )

            return {
                "query": query,
                "results": results,
                "total": len(results),
                "search_time": data.get("etime", ""),
            }
        except httpx.HTTPStatusError as exc:
            return {
                "query": query,
                "error": f"Search failed with HTTP {exc.response.status_code}",
                "detail": str(exc),
                "results": [],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "query": query,
                "error": f"Search failed for '{query}'",
                "detail": str(exc),
                "results": [],
            }

    async def get_database_stats(self) -> dict[str, Any]:
        """Return summary statistics about eggNOG 7."""
        try:
            html = await self._fetch_text("/stats/")
            stats = _parse_stats_html(html)
            stats["url"] = f"{self.base_url}/stats/"
            return stats
        except httpx.ConnectError:
            # Fallback to known values if the site is unreachable
            return {
                "version": "eggNOG 7",
                "annotated_species": "12k+",
                "protein_sequences": "59M+",
                "phylogenetic_trees": "1.1M+",
                "orthologous_groups": "3.1M+",
                "url": f"{self.base_url}/stats/",
                "note": "Statistics retrieved from cached values (site unreachable).",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "error": "Failed to retrieve database statistics",
                "detail": str(exc),
            }

    async def list_downloads(self) -> dict[str, Any]:
        """Return the list of downloadable data files from eggNOG 7."""
        known_files = [
            {
                "file": "e7.proteins.fa.gz",
                "url": f"{DOWNLOAD_URL}/e7.proteins.fa.gz",
                "description": "All protein sequences covered in eggNOG 7",
            },
            {
                "file": "e7.og_fasta_sequences.tar",
                "url": f"{DOWNLOAD_URL}/e7.og_fasta_sequences.tar",
                "description": "FASTA files for all orthologous groups",
            },
            {
                "file": "e7.og_info_kegg_go.tsv.gz",
                "url": f"{DOWNLOAD_URL}/e7.og_info_kegg_go.tsv.gz",
                "description": (
                    "OG info file: OG name, protein cluster, taxonomic level, "
                    "protein count, species count, protein list, "
                    "KEGG KO terms, KEGG KO symbols, GO slim terms"
                ),
            },
            {
                "file": "e7.protein_families.tsv.gz",
                "url": f"{DOWNLOAD_URL}/e7.protein_families.tsv.gz",
                "description": (
                    "Protein family info: family name, protein count, "
                    "species count, OG count, protein list"
                ),
            },
            {
                "file": "e7.clu2ogs.tsv.gz",
                "url": f"{DOWNLOAD_URL}/e7.clu2ogs.tsv.gz",
                "description": "OGs per protein family cluster",
            },
            {
                "file": "e7.taxid_info.tsv.gz",
                "url": f"{DOWNLOAD_URL}/e7.taxid_info.tsv.gz",
                "description": (
                    "Taxonomic information: new taxid, old taxid, scientific name, "
                    "rank, named lineage, taxid lineage"
                ),
            },
            {
                "file": "e7.trees.tsv.gz",
                "url": f"{DOWNLOAD_URL}/e7.trees.tsv.gz",
                "description": (
                    "Protein family phylogenetic trees in Newick format: "
                    "family name, protein count, tree size, tree"
                ),
            },
        ]
        return {
            "version": "eggNOG 7",
            "files": known_files,
            "downloads_page": f"{self.base_url}/downloads/",
        }

    async def get_taxid_info(self, taxid: int) -> dict[str, Any]:
        """
        Look up taxonomic information for an NCBI taxonomy ID.

        eggNOG does not expose a per-taxon JSON API.  The full taxonomic
        information is available in the downloadable TSV file
        ``e7.taxid_info.tsv.gz``.  This method provides the download URL
        and guidance for local lookup.
        """
        return {
            "taxid": taxid,
            "note": (
                "Per-taxon lookup requires the e7.taxid_info.tsv.gz file. "
                "Download it from the URL below and parse locally. "
                "The TSV columns are: New_Taxid, Old_Taxid, Sci_Name, Rank, "
                "Named_Lineage, Taxid_Lineage."
            ),
            "download_url": f"{DOWNLOAD_URL}/e7.taxid_info.tsv.gz",
            "example_lineage_format": (
                "root,cellular organisms,Eukaryota,...,<species>"
            ),
        }

    async def annotate_protein(self, protein_id: str) -> dict[str, Any]:
        """
        Annotate a protein by its eggNOG ID.

        This is a convenience wrapper that calls ``get_protein`` and
        reformats the result to emphasise the functional annotation.
        """
        data = await self.get_protein(protein_id)
        if "error" in data:
            return data

        annotation: dict[str, Any] = {
            "protein_id": protein_id,
            "protein_name": data.get("protein_name"),
            "species": data.get("species"),
            "taxid": data.get("taxid"),
            "uniprot_id": data.get("uniprot_id"),
            "protein_family": data.get("protein_family"),
            "pfam_domains": data.get("pfam_domains", []),
            "orthologous_groups": data.get("orthologous_groups", []),
        }

        func_data = data.get("predicted_functions", {})
        annotation["kegg_ko_terms"] = func_data.get("kegg_ko", [])
        annotation["go_terms"] = func_data.get("go_slim", [])
        annotation["kegg_gene_symbols"] = func_data.get("kegg_gene_symbols", [])

        selected_og = data.get("selected_og", {})
        if selected_og:
            annotation["selected_og"] = selected_og

        annotation["source_url"] = data.get("url", "")
        return annotation

    async def get_protein_family(self, family_name: str, max_species: int = 50) -> dict[str, Any]:
        """
        Retrieve the protein family (cluster) content.

        This returns the list of species and proteins grouped under the
        given protein family name.
        """
        try:
            data = await self._fetch_json(
                f"{API_PREFIX}/clu_content/{quote(family_name, safe='')}/"
            )
            prots = data.get("prots", {})
            sp = data.get("sp", {})

            species_list = []
            total_proteins = 0
            for i, (species, protein_ids) in enumerate(prots.items()):
                if i >= max_species:
                    break
                unique_proteins = list(set(protein_ids))
                species_list.append(
                    {
                        "species": species,
                        "protein_count": len(protein_ids),
                        "unique_protein_count": len(unique_proteins),
                        "protein_ids": unique_proteins[:20],
                    }
                )
                total_proteins += len(protein_ids)

            result: dict[str, Any] = {
                "protein_family": family_name,
                "total_species": len(prots),
                "total_proteins": total_proteins,
                "species": species_list,
                "truncated": len(prots) > max_species,
            }

            # Include species count summary if available
            if sp:
                result["species_summary"] = sp

            return result
        except httpx.HTTPStatusError as exc:
            return {
                "error": f"HTTP {exc.response.status_code} for protein family '{family_name}'",
                "detail": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "error": f"Failed to retrieve protein family '{family_name}'",
                "detail": str(exc),
            }


# ---------------------------------------------------------------------------
# Convenience factory for the MCP server
# ---------------------------------------------------------------------------
_global_client: eggNOGClient | None = None
_client_lock: asyncio.Lock | None = None


async def get_client() -> eggNOGClient:
    """Return a process-wide singleton client (safe for concurrent coroutines)."""
    global _global_client, _client_lock
    if _global_client is None:
        if _client_lock is None:
            _client_lock = asyncio.Lock()
        async with _client_lock:
            if _global_client is None:
                _global_client = eggNOGClient()
    return _global_client


async def close_client() -> None:
    global _global_client, _client_lock
    if _global_client is not None:
        if _client_lock is None:
            _client_lock = asyncio.Lock()
        async with _client_lock:
            if _global_client is not None:
                await _global_client.close()
                _global_client = None
