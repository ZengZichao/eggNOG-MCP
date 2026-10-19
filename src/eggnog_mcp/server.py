"""
eggNOG-MCP Server.

This module implements the Model Context Protocol (MCP) server that exposes
eggNOG database tools to LLM clients.  It uses the official ``mcp`` Python
SDK (MCPServer, mcp >= 2.0) for protocol handling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from mcp.server.mcpserver import MCPServer

from .client import close_client, get_client
from .version import __version__

logger = logging.getLogger("eggnog_mcp.server")

# ---------------------------------------------------------------------------
# Create the MCP server
# ---------------------------------------------------------------------------
mcp = MCPServer(
    name="eggNOG-MCP",
    version=__version__,
    instructions=(
        "eggNOG-MCP provides tools to query the eggNOG 7 database "
        "(https://eggnogdb.org) for orthology assignments, functional "
        "annotations, protein family information, and database statistics. "
        "Use these tools to look up proteins, orthologous groups, search the "
        "database, and retrieve functional annotations (KEGG KO, GO terms)."
    ),
)

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_protein(protein_id: str) -> str:
    """Look up detailed information for a protein in the eggNOG database.

    Retrieves protein family membership, predicted functions (KEGG KO terms
    and GO terms with confidence scores), and the list of orthologous
    groups (OGs) associated with the protein.

    Parameters
    ----------
    protein_id : str
        The eggNOG protein identifier in the format ``taxid.seqid``.
        Examples:
          - ``9606.ENSP00000269305``  (human P53 / TP53)
          - ``9606.ENSP00000330696``  (human P2RX7)
          - ``460265.Mnod_3996``      (nitrogen fixation protein)

    Returns
    -------
    str
        JSON string with protein family, function predictions, and OG list.
    """
    client = await get_client()
    data = await client.get_protein(protein_id)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_orthologous_group(og_id: str) -> str:
    """Look up information for an orthologous group (OG) in eggNOG.

    Retrieves the evolutionary origin, protein count, species count,
    functional annotation (KEGG KO and GO slim terms), and the list of
    all OGs in the same protein family.

    Parameters
    ----------
    og_id : str
        The orthologous group identifier in the format
        ``family@taxid|level``.
        Examples:
          - ``P53@33154|A-1``    (P53 family, Opisthokonta level)
          - ``P53@7742|IM-18``   (P53 family, Gnathostomata level)

    Returns
    -------
    str
        JSON string with OG details including evolutionary origin, counts,
        and functional annotation.
    """
    client = await get_client()
    data = await client.get_orthologous_group(og_id)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_og_content(og_id: str, max_species: int = 50) -> str:
    """Retrieve the list of proteins within an orthologous group.

    Returns the species and their protein members for the specified OG.
    The result is capped at ``max_species`` to avoid excessively large
    responses.

    Parameters
    ----------
    og_id : str
        The orthologous group identifier in ``family@taxid|level`` format.
        Example: ``P53@33154|A-1``
    max_species : int, optional
        Maximum number of species to include (default 50).

    Returns
    -------
    str
        JSON string with species list, protein counts, and protein IDs.
    """
    client = await get_client()
    data = await client.get_og_content(og_id, max_species=max_species)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_orthologs(protein_id: str, max_species: int = 50) -> str:
    """Retrieve pairwise orthologs for a protein.

    Returns the orthologous proteins grouped by species for the given
    eggNOG protein ID.

    Parameters
    ----------
    protein_id : str
        The eggNOG protein identifier in ``taxid.seqid`` format.
        Example: ``9606.ENSP00000269305``
    max_species : int, optional
        Maximum number of species to include (default 50).

    Returns
    -------
    str
        JSON string with orthologs grouped by species.
    """
    client = await get_client()
    data = await client.get_orthologs(protein_id, max_species=max_species)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def search_eggnog(query: str) -> str:
    """Search the eggNOG database for proteins or protein families.

    Performs a text search across the eggNOG database.  The query must be
    at least 3 characters long.  The query can be a protein name
    (e.g. ``P53``), a UniProt ID (e.g. ``P04637``), or a protein family
    name.

    Parameters
    ----------
    query : str
        Search query string (minimum 3 characters).
        Examples:
          - ``P53``
          - ``P04637``
          - ``TP53``
          - ``P2RX7``

    Returns
    -------
    str
        JSON string with a list of search results (type, ID, label, URL).
    """
    client = await get_client()
    data = await client.search(query)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def annotate_protein(protein_id: str) -> str:
    """Annotate a protein with functional information from eggNOG.

    Returns a structured functional annotation for the given protein,
    including KEGG KO terms, GO slim terms, protein family, Pfam domains,
    and orthologous groups.  This is a higher-level convenience wrapper
    around ``get_protein`` that emphasises the annotation results.

    Parameters
    ----------
    protein_id : str
        The eggNOG protein identifier in the format ``taxid.seqid``.
        Examples:
          - ``9606.ENSP00000269305``  (human P53)
          - ``4932.YJR154W``          (yeast)

    Returns
    -------
    str
        JSON string with KEGG KO terms, GO terms, and cross-references.
    """
    client = await get_client()
    data = await client.annotate_protein(protein_id)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_protein_family(family_name: str, max_species: int = 50) -> str:
    """Retrieve protein family (cluster) content from eggNOG.

    Returns the list of species and proteins grouped under the given
    protein family name (also called a cluster).

    Parameters
    ----------
    family_name : str
        The protein family / cluster name.
        Examples: ``P53``, ``P53_tetramer``, ``P53_TAD``
    max_species : int, optional
        Maximum number of species to include (default 50).

    Returns
    -------
    str
        JSON string with species list, protein counts, and protein IDs.
    """
    client = await get_client()
    data = await client.get_protein_family(family_name, max_species=max_species)
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_database_stats() -> str:
    """Retrieve summary statistics of the eggNOG 7 database.

    Returns the number of annotated species, protein sequences,
    phylogenetic trees, and orthologous groups in the current eggNOG
    release.

    Returns
    -------
    str
        JSON string with database statistics.
    """
    client = await get_client()
    data = await client.get_database_stats()
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_downloads() -> str:
    """List downloadable data files from the eggNOG 7 database.

    Returns a list of all bulk-downloadable files (protein sequences,
    OG info, phylogenetic trees, taxonomic info, etc.) with their
    URLs and descriptions.

    Returns
    -------
    str
        JSON string with download file information.
    """
    client = await get_client()
    data = await client.list_downloads()
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_taxid_info(taxid: int) -> str:
    """Look up taxonomic information for an NCBI taxonomy ID.

    Provides guidance on retrieving taxonomic information for a given
    NCBI taxonomy ID from the eggNOG database.  The full taxonomic
    data is available in the downloadable ``e7.taxid_info.tsv.gz`` file.

    Parameters
    ----------
    taxid : int
        NCBI taxonomy ID.
        Examples:
          - ``9606``   (Homo sapiens)
          - ``4932``   (Saccharomyces cerevisiae)
          - ``44689``  (Danio rerio)

    Returns
    -------
    str
        JSON string with taxonomic lookup information and download URL.
    """
    client = await get_client()
    data = await client.get_taxid_info(taxid)
    return json.dumps(data, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
@mcp.resource("eggnog://version")
def version_info() -> str:
    """Return the eggNOG-MCP server version."""
    return json.dumps(
        {
            "server": "eggNOG-MCP",
            "version": __version__,
            "database": "eggNOG 7",
            "database_url": "https://eggnogdb.org/",
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource("eggnog://database/stats")
async def database_stats_resource() -> str:
    """Return cached database statistics."""
    client = await get_client()
    data = await client.get_database_stats()
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.resource("eggnog://database/downloads")
async def database_downloads_resource() -> str:
    """Return the list of downloadable files."""
    client = await get_client()
    data = await client.list_downloads()
    return json.dumps(data, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Run the eggNOG-MCP server with stdio transport."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    logger.info("Starting eggNOG-MCP server v%s", __version__)

    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    finally:
        # Clean up the HTTP client
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(close_client())
            loop.close()
        except Exception as e:  # noqa: BLE001
            logger.debug("Error during client cleanup: %s", e)


if __name__ == "__main__":
    main()
