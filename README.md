# eggNOG-MCP

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://eggnogdb.org/)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Database: eggNOG 7](https://img.shields.io/badge/database-eggNOG%207-orange.svg)](https://eggnogdb.org/)

> **[中文文档](./README_zh.md)** | **English**

> ⚠️ **Disclaimer:** This is a **community-maintained, unofficial** MCP server for the eggNOG database. It is not affiliated with, endorsed by, or maintained by the eggNOG team or EMBL. The official eggNOG database is available at [https://eggnogdb.org/](https://eggnogdb.org/).

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides AI assistants with access to the [eggNOG 7 database](https://eggnogdb.org/) — a comprehensive resource for orthology assignments and functional predictions for comparative genomics.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Available Tools](#available-tools)
- [Available Resources](#available-resources)
- [Usage Examples](#usage-examples)
- [Project Structure](#project-structure)
- [Development](#development)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Overview

[eggNOG](https://eggnogdb.org/) (evolutionary genealogy of genes: Non-supervised Orthologous Groups) is a database of orthology relationships, functional annotations, and phylogenetic trees covering **12,000+ annotated species**, **59 million+ protein sequences**, and **3.1 million+ orthologous groups**.

**eggNOG-MCP** bridges the eggNOG database and Large Language Models (LLMs) by implementing the Model Context Protocol. Once configured, any MCP-compatible AI assistant (such as Claude Desktop, Cursor, or custom agents) can query eggNOG directly through natural language.

The server communicates with eggNOG's native JSON API (`/e7api/`) for reliable, structured data access — no HTML scraping required.

### What can you do with eggNOG-MCP?

- 🔬 Look up a protein by its eggNOG ID and retrieve its functional annotation
- 🧬 Query an orthologous group (OG) to understand evolutionary relationships
- 📋 List all proteins within an OG, grouped by species
- 🔗 Retrieve pairwise orthologs for a protein across species
- 🔍 Search the eggNOG database by protein name, UniProt ID, or family name
- 📊 Get database statistics (species, proteins, trees, OGs counts)
- 📥 List all downloadable bulk data files
- 🏷️ Annotate a protein with KEGG KO terms and GO terms with confidence scores
- 🧫 Browse all members of a protein family

---

## Features

| Feature | Description |
|---------|-------------|
| **Protein Lookup** | Retrieve protein family, predicted functions, and OGs for any eggNOG protein ID |
| **OG Query** | Look up orthologous group details including evolutionary origin, member counts, and functional annotation |
| **OG Content** | List all proteins within an OG, grouped by species |
| **Orthologs** | Retrieve pairwise orthologs for a protein across all species |
| **Protein Family** | Browse all species and proteins within a protein family cluster |
| **Database Search** | Search by protein name, UniProt ID, or family name |
| **Functional Annotation** | Get structured KEGG KO and GO term annotations with confidence scores |
| **Database Statistics** | Access current eggNOG 7 release statistics |
| **Downloads Index** | List all bulk-downloadable data files with URLs and descriptions |
| **Taxon Lookup** | Look up taxonomic information by NCBI taxonomy ID |
| **MCP Resources** | Expose version info, stats, and downloads as MCP resources |
| **JSON API** | Uses eggNOG's native `/e7api/` JSON endpoints for reliable data access |
| **Async HTTP** | Built on `httpx` for efficient async HTTP requests |
| **Error Resilient** | All tools return structured error messages instead of crashing |

---

## Quick Start

```bash
# Install
pip install eggnog-mcp

# Run (stdio transport — for use with MCP clients)
eggnog-mcp
```

Or run directly with Python:

```bash
python -m eggnog_mcp.server
```

---

## Installation

### Option 1: Install from source (recommended for development)

```bash
git clone https://github.com/ZengZichao/eggNOG-MCP.git
cd eggNOG-MCP
pip install -e .
```

### Option 2: Install dependencies only

```bash
pip install -r requirements.txt
```

### Requirements

- Python ≥ 3.10
- `mcp` ≥ 2.0.0 (Model Context Protocol SDK)
- `httpx` ≥ 0.27.0 (async HTTP client)

---

## Configuration

### Claude Desktop

Add the following to your `claude_desktop_config.json` file:

```json
{
  "mcpServers": {
    "eggnog-mcp": {
      "command": "eggnog-mcp",
      "args": []
    }
  }
}
```

If you installed from source without adding to PATH, use the full path:

```json
{
  "mcpServers": {
    "eggnog-mcp": {
      "command": "python",
      "args": ["-m", "eggnog_mcp.server"],
      "env": {
        "PYTHONPATH": "/path/to/eggNOG-MCP/src"
      }
    }
  }
}
```

### Cursor IDE

Add to your Cursor MCP settings:

```json
{
  "mcpServers": {
    "eggnog-mcp": {
      "command": "eggnog-mcp"
    }
  }
}
```

### Generic MCP Client

The server uses **stdio transport** by default. Start it with:

```bash
eggnog-mcp
```

The server communicates via stdin/stdout using the MCP protocol.

### TLS / Network Issues

If you encounter TLS connection errors when connecting to `https://eggnogdb.org`, you can modify the client initialization in `src/eggnog_mcp/client.py` to use HTTP or disable SSL verification:

```python
# Option 1: Use HTTP
_global_client = eggNOGClient(base_url="http://eggnogdb.org")

# Option 2: Disable SSL verification (HTTPS)
_global_client = eggNOGClient(verify_ssl=False)
```

---

## Available Tools

### 1. `get_protein`

Look up detailed information for a protein in the eggNOG database.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `protein_id` | `str` | Yes | eggNOG protein ID in `taxid.seqid` format |

**Example:**
```
protein_id = "9606.ENSP00000269305"
```

**Returns:** Protein name, species, taxid, UniProt ID, Pfam domains, KEGG KO terms, orthologous groups list, predicted functions (KEGG KO + GO terms with confidence), selected OG details.

---

### 2. `get_orthologous_group`

Look up information for an orthologous group (OG).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `og_id` | `str` | Yes | OG ID in `family@taxid\|level` format |

**Example:**
```
og_id = "P53@33154|A-1"
```

**Returns:** OG ID, protein family, evolutionary origin, taxonomic lineage, protein count, species count, functional annotation (KEGG KO + GO slim), all OGs in the same family.

---

### 3. `get_og_content`

Retrieve the list of proteins within an orthologous group.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `og_id` | `str` | Yes | OG ID in `family@taxid\|level` format |
| `max_species` | `int` | No | Maximum number of species to include (default: 50) |

**Example:**
```
og_id = "P53@33154|A-1", max_species = 10
```

**Returns:** Total species count, total protein count, species list with protein IDs.

---

### 4. `get_orthologs`

Retrieve pairwise orthologs for a protein.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `protein_id` | `str` | Yes | eggNOG protein ID in `taxid.seqid` format |
| `max_species` | `int` | No | Maximum number of species to include (default: 50) |

**Example:**
```
protein_id = "9606.ENSP00000269305", max_species = 10
```

**Returns:** Total ortholog species count, orthologs grouped by species with protein IDs.

---

### 5. `search_eggnog`

Search the eggNOG database for proteins or orthologous groups.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | `str` | Yes | Search query (≥ 3 characters) |

**Example:**
```
query = "P53"
query = "P04637"
query = "TP53"
```

**Returns:** List of matching proteins and OGs with type, ID, label, and URL.

---

### 6. `annotate_protein`

Annotate a protein with functional information (KEGG KO + GO terms).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `protein_id` | `str` | Yes | eggNOG protein ID in `taxid.seqid` format |

**Example:**
```
protein_id = "9606.ENSP00000269305"
```

**Returns:** Structured annotation with KEGG KO terms, GO slim terms, KEGG gene symbols, protein family, Pfam domains, orthologous groups, and selected OG details.

---

### 7. `get_protein_family`

Retrieve protein family (cluster) content from eggNOG.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `family_name` | `str` | Yes | Protein family / cluster name |
| `max_species` | `int` | No | Maximum number of species to include (default: 50) |

**Example:**
```
family_name = "P53", max_species = 10
```

**Returns:** Total species count, total protein count, species list with protein IDs, species summary.

---

### 8. `get_database_stats`

Retrieve summary statistics of the eggNOG 7 database.

**Parameters:** None

**Returns:** Annotated species count, protein sequences count, phylogenetic trees count, orthologous groups count.

---

### 9. `list_downloads`

List all downloadable bulk data files.

**Parameters:** None

**Returns:** List of files with filenames, URLs, and descriptions (protein sequences, OG info, trees, taxonomic info, etc.).

---

### 10. `get_taxid_info`

Look up taxonomic information for an NCBI taxonomy ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `taxid` | `int` | Yes | NCBI taxonomy ID |

**Example:**
```
taxid = 9606
```

**Returns:** Taxonomic lookup guidance, download URL for the taxid info TSV file, and column format description.

---

## Available Resources

| Resource URI | Description |
|--------------|-------------|
| `eggnog://version` | Server version and database info |
| `eggnog://database/stats` | Cached database statistics |
| `eggnog://database/downloads` | List of downloadable files |

---

## Usage Examples

### Example 1: Annotate Human P53

```
User:     "What is the functional annotation of human P53 in eggNOG?"
Assistant: [calls annotate_protein with protein_id="9606.ENSP00000269305"]
```

**Result includes:**
- Protein family: `P53`
- KEGG KO terms: `K04451` (TP53, 11.47%), `K10148` (TP73, 14.34%), `K10149` (TP63, 19.80%)
- GO terms: `GO:0006355` (regulation of transcription, 68.83%), `GO:0006351` (transcription, 68.83%)
- Pfam domains: `P53_TAD`, `TAD2`, `P53`, `P53_tetramer`
- 35 orthologous groups spanning 438 species

### Example 2: Search for P53

```
User:     "Search eggNOG for P53"
Assistant: [calls search_eggnog with query="P53"]
```

**Result:** 10 matches including proteins (e.g. `PPP5_HUMAN`) and OGs (e.g. `P53@33154|A-1`).

### Example 3: Query an Orthologous Group

```
User:     "Tell me about the P53 orthologous group at the Opisthokonta level"
Assistant: [calls get_orthologous_group with og_id="P53@33154|A-1"]
```

**Result:** Evolutionary origin (Opisthokonta), 1,081 proteins, 438 species, KEGG KO and GO annotations, full family OG list.

### Example 4: List Proteins in an OG

```
User:     "Show me the proteins in the P53 OG at the Opisthokonta level"
Assistant: [calls get_og_content with og_id="P53@33154|A-1", max_species=5]
```

### Example 5: Get Orthologs

```
User:     "What are the orthologs of human P53?"
Assistant: [calls get_orthologs with protein_id="9606.ENSP00000269305"]
```

### Example 6: Database Statistics

```
User:     "How many species are in eggNOG?"
Assistant: [calls get_database_stats]
```

**Result:** 12k+ annotated species, 59M+ protein sequences, 1.1M+ phylogenetic trees, 3.1M+ orthologous groups.

---

## Project Structure

```
eggNOG-MCP/
├── pyproject.toml              # Project configuration & dependencies
├── requirements.txt            # pip requirements
├── LICENSE                     # MIT License
├── .gitignore                  # Git ignore rules
├── README.md                   # English documentation (this file)
├── README_zh.md                # Chinese documentation
├── src/
│   └── eggnog_mcp/
│       ├── __init__.py         # Package initialization
│       ├── version.py          # Version info
│       ├── client.py           # eggNOG API client (async HTTP, JSON API)
│       └── server.py           # MCP server & tool definitions (10 tools)
└── tests/
    └── test_client.py          # Unit tests for the API client
```

---

## Development

### Setup

```bash
# Clone and install in development mode
git clone https://github.com/ZengZichao/eggNOG-MCP.git
cd eggNOG-MCP
pip install -e ".[dev]"
```

### Linting

```bash
ruff check src/
ruff format src/
```

### Running Tests

```bash
# Run the full test suite
pytest tests/ -v
```

### Testing the Server

```bash
# Run the server and verify it starts
eggnog-mcp

# Or test with the MCP inspector
npx @modelcontextprotocol/inspector eggnog-mcp
```

### API Endpoints Used

The client communicates with eggNOG's native JSON API:

| Endpoint | Description |
|----------|-------------|
| `/e7api/protein/{id}/` | Protein details + OGs + functions |
| `/e7api/og/{id}/` | Orthologous group details |
| `/e7api/og_content/{id}/` | Proteins within an OG |
| `/e7api/clu_content/{name}/` | Proteins within a family cluster |
| `/e7api/orthologs/{id}/` | Pairwise orthologs for a protein |
| `/e7api/suggest_entries/{query}/` | Search / autocomplete |
| `/stats/` | Database statistics (HTML) |

---

## License

This project is licensed under the [MIT License](./LICENSE).

The eggNOG database itself is maintained by the eggNOG Team at EMBL. Please refer to [https://eggnogdb.org/](https://eggnogdb.org/) for database usage terms and citation requirements.

> **Note:** This is an unofficial, community-maintained project. It is not affiliated with or endorsed by the eggNOG team or EMBL.

---

## Acknowledgements

- **eggNOG Team** — For creating and maintaining the eggNOG database. Visit [https://eggnogdb.org/](https://eggnogdb.org/) for more information.
- **Anthropic** — For the Model Context Protocol specification and SDK.
- **Huerta-Cepas J, et al.** — *eggNOG 7.0: comparative genomics at the scale of 12,000+ genomes.* Please cite the original eggNOG publications when using this tool in research.

### Key References

- Huerta-Cepas, J., et al. (2023). eggNOG 7.0: comparative genomics at the scale of 12,000+ genomes. *Briefings in Bioinformatics*, 24(1), bbac483.
- The Model Context Protocol specification: [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)

---

<div align="center">
  <sub>Built for the bioinformatics and AI communities.</sub>
</div>
