"""
Unit tests for eggNOG-MCP client helper functions and API methods.

These tests use mock HTTP responses to avoid hitting the real eggNOG server,
making them fast, deterministic, and safe to run in CI.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from eggnog_mcp.client import (
    _clean_text,
    _format_go_terms,
    _format_kegg_terms,
    _format_og_groups,
    _format_og_list,
    _parse_stats_html,
    close_client,
    eggNOGClient,
    get_client,
)

# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestCleanText:
    def test_strips_span_tags(self):
        assert _clean_text("hello <span class='hl'>world</span>") == "hello world"

    def test_strips_multiple_span_tags(self):
        assert _clean_text("<span>test</span> <span>value</span>") == "test value"

    def test_no_tags(self):
        assert _clean_text("plain text") == "plain text"

    def test_empty_string(self):
        assert _clean_text("") == ""

    def test_strips_whitespace(self):
        assert _clean_text("  hello  ") == "hello"


class TestFormatKeggTerms:
    def test_full_entries(self):
        data = [["K04451", 0.1147, "TP53", "tumor protein p53"]]
        result = _format_kegg_terms(data)
        assert len(result) == 1
        assert result[0]["ko_id"] == "K04451"
        assert result[0]["confidence"] == 0.1147
        assert result[0]["symbol"] == "TP53"
        assert result[0]["description"] == "tumor protein p53"

    def test_partial_entries(self):
        data = [["K04451", 0.1147]]
        result = _format_kegg_terms(data)
        assert len(result) == 1
        assert result[0]["ko_id"] == "K04451"
        assert result[0]["confidence"] == 0.1147
        assert "symbol" not in result[0]
        assert "description" not in result[0]

    def test_empty_list(self):
        assert _format_kegg_terms([]) == []

    def test_none(self):
        assert _format_kegg_terms(None) == []

    def test_invalid_entries(self):
        assert _format_kegg_terms(["invalid"]) == []
        assert _format_kegg_terms([[]]) == []


class TestFormatGoTerms:
    def test_full_entries(self):
        data = [["GO:0006355", 0.6883, "regulation of transcription"]]
        result = _format_go_terms(data)
        assert len(result) == 1
        assert result[0]["go_id"] == "GO:0006355"
        assert result[0]["confidence"] == 0.6883
        assert result[0]["description"] == "regulation of transcription"

    def test_partial_entries(self):
        data = [["GO:0006355", 0.6883]]
        result = _format_go_terms(data)
        assert len(result) == 1
        assert result[0]["go_id"] == "GO:0006355"
        assert "description" not in result[0]

    def test_empty(self):
        assert _format_go_terms([]) == []
        assert _format_go_terms(None) == []


class TestFormatOgList:
    def test_full_entries(self):
        data = [{"n": "P53@33154|A-1", "l": "33154", "ns": 438, "nm": 1081,
                 "lca": "Opisthokonta", "name": "Opisthokonta"}]
        result = _format_og_list(data)
        assert len(result) == 1
        assert result[0]["og_id"] == "P53@33154|A-1"
        assert result[0]["taxonomic_level"] == "33154"
        assert result[0]["species_count"] == 438
        assert result[0]["protein_count"] == 1081

    def test_empty(self):
        assert _format_og_list([]) == []
        assert _format_og_list(None) == []

    def test_non_dict_entries(self):
        assert _format_og_list(["invalid"]) == []


class TestFormatOgGroups:
    def test_nested_groups(self):
        data = {"P53": [{"n": "P53@33154|A-1", "ns": 438, "nm": 1081,
                         "lca": "Opisthokonta", "name": "Opisthokonta"}]}
        result = _format_og_groups(data)
        assert len(result) == 1
        assert result[0]["protein_family"] == "P53"
        assert result[0]["og_id"] == "P53@33154|A-1"

    def test_multiple_groups(self):
        data = {
            "P53": [{"n": "P53@33154|A-1", "ns": 438, "nm": 1081}],
            "P53_tetramer": [{"n": "P53_tetramer@33154|A-1", "ns": 100, "nm": 200}],
        }
        result = _format_og_groups(data)
        assert len(result) == 2

    def test_empty(self):
        assert _format_og_groups({}) == []
        assert _format_og_groups(None) == []


class TestParseStatsHtml:
    def test_parse_full_html(self):
        html = """
        <p class="text-3xl font-bold text-yellow-600">12k+</p>
        <p class="text-gray-700 text-sm mt-1">Annotated Species</p>
        <p class="text-3xl font-bold text-yellow-600">59M+</p>
        <p class="text-gray-700 text-sm mt-1">Protein Sequences</p>
        <p class="text-3xl font-bold text-yellow-600">1.1M+</p>
        <p class="text-gray-700 text-sm mt-1">Phylogenetic Trees</p>
        <p class="text-3xl font-bold text-yellow-600">3.1M+</p>
        <p class="text-gray-700 text-sm mt-1">Orthologous Groups</p>
        """
        stats = _parse_stats_html(html)
        assert stats["annotated_species"] == "12k+"
        assert stats["protein_sequences"] == "59M+"
        assert stats["phylogenetic_trees"] == "1.1M+"
        assert stats["orthologous_groups"] == "3.1M+"
        assert stats["version"] == "eggNOG 7"

    def test_parse_empty_html(self):
        stats = _parse_stats_html("")
        assert "annotated_species" not in stats
        assert stats["version"] == "eggNOG 7"


# ---------------------------------------------------------------------------
# Client tests with mocked HTTP
# ---------------------------------------------------------------------------

class TestEggNOGClient:
    @pytest.fixture
    def client(self):
        return eggNOGClient()

    @pytest.mark.asyncio
    async def test_get_protein_success(self, client):
        mock_data = {
            "focus_prot": {
                "bestname": "TP53",
                "sp": "HUMAN",
                "taxid": "9606",
                "ukb": "P04637",
                "pfam": ["P53_TAD", "P53"],
                "ko": ["K04451"],
                "ogs": {"P53": [{"n": "P53@33154|A-1", "ns": 438, "nm": 1081,
                                  "lca": "Opisthokonta", "name": "Opisthokonta"}]},
            },
            "focus_og": {
                "n": "P53@9606|40E2",
                "lca": "Mammalia",
                "nm": 50,
                "ns": 10,
                "nlin": ["Eukaryota", "Mammalia"],
                "top_func": {
                    "kegg_ko": [["K04451", 0.11, "TP53", "tumor protein p53"]],
                    "GOslim": [["GO:0006355", 0.68, "regulation of transcription"]],
                    "kegg_gsymbol": ["TP53"],
                },
            },
            "focus_clu": {
                "n": "P53",
                "ogs": [{"nm": 1081, "ns": 438}],
            },
        }

        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            result = await client.get_protein("9606.ENSP00000269305")

        assert result["protein_id"] == "9606.ENSP00000269305"
        assert result["protein_name"] == "TP53"
        assert result["species"] == "HUMAN"
        assert result["taxid"] == "9606"
        assert result["uniprot_id"] == "P04637"
        assert "orthologous_groups" in result
        assert result["orthologous_groups"][0]["og_id"] == "P53@33154|A-1"
        assert "predicted_functions" in result
        assert result["predicted_functions"]["kegg_ko"][0]["ko_id"] == "K04451"

    @pytest.mark.asyncio
    async def test_get_protein_http_error(self, client):
        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_request = MagicMock()
            mock_request.url = "https://eggnogdb.org/e7api/protein/invalid/"
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.request = mock_request
            mock_fetch.side_effect = httpx.HTTPStatusError(
                "Not Found", request=mock_request, response=mock_response
            )
            result = await client.get_protein("invalid.id")

        assert "error" in result
        assert "HTTP 404" in result["error"]

    @pytest.mark.asyncio
    async def test_get_protein_connect_error(self, client):
        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = httpx.ConnectError("Connection refused")
            result = await client.get_protein("9606.ENSP00000269305")

        assert "error" in result
        assert "Connection error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_orthologous_group_success(self, client):
        mock_data = {
            "focus_og": {
                "clu": "P53",
                "lca": "Opisthokonta",
                "nlin": ["Eukaryota", "Opisthokonta"],
                "nm": 1081,
                "ns": 438,
                "name": "Opisthokonta",
                "top_func": {
                    "kegg_ko": [["K04451", 0.11, "TP53", "tumor protein p53"]],
                    "GOslim": [["GO:0006355", 0.68, "regulation of transcription"]],
                    "kegg_gsymbol": ["TP53"],
                },
            },
            "focus_clu": {
                "n": "P53",
                "ogs": [{"n": "P53@33154|A-1", "l": "33154", "ns": 438, "nm": 1081,
                          "lca": "Opisthokonta", "name": "Opisthokonta"}],
            },
        }

        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            result = await client.get_orthologous_group("P53@33154|A-1")

        assert result["og_id"] == "P53@33154|A-1"
        assert result["protein_family"] == "P53"
        assert result["evolutionary_origin"] == "Opisthokonta"
        assert result["protein_count"] == 1081
        assert result["species_count"] == 438
        assert "functional_annotation" in result
        assert "family_orthologous_groups" in result

    @pytest.mark.asyncio
    async def test_get_og_content_success(self, client):
        mock_data = {
            "prots": {
                "HUMAN": ["9606.ENSP00000269305", "9606.ENSP00000269305"],
                "MOUSE": ["10090.ENSMUSP00000123456"],
            }
        }

        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            result = await client.get_og_content("P53@33154|A-1", max_species=50)

        assert result["og_id"] == "P53@33154|A-1"
        assert result["total_species"] == 2
        assert result["total_proteins"] == 3  # 2 + 1
        assert len(result["species"]) == 2
        assert result["species"][0]["species"] == "HUMAN"
        assert result["species"][0]["protein_count"] == 2
        assert result["species"][0]["unique_protein_count"] == 1
        assert result["truncated"] is False

    @pytest.mark.asyncio
    async def test_get_og_content_truncation(self, client):
        prots = {f"species_{i}": [f"{i}.prot"] for i in range(100)}
        mock_data = {"prots": prots}

        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            result = await client.get_og_content("test@1|A-1", max_species=10)

        assert result["truncated"] is True
        assert len(result["species"]) == 10
        assert result["total_species"] == 100

    @pytest.mark.asyncio
    async def test_get_orthologs_success(self, client):
        mock_data = {
            "orthologs": {
                "MOUSE": ["10090.ENSMUSP00000123456", "10090.ENSMUSP00000123457"],
                "RATNO": ["10116.ENSRNOP00000123456"],
            }
        }

        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            result = await client.get_orthologs("9606.ENSP00000269305")

        assert result["protein_id"] == "9606.ENSP00000269305"
        assert result["total_ortholog_species"] == 2
        assert result["total_orthologs"] == 3
        assert len(result["orthologs_by_species"]) == 2

    @pytest.mark.asyncio
    async def test_search_too_short(self, client):
        result = await client.search("ab")
        assert "error" in result
        assert "at least 3 characters" in result["error"]

    @pytest.mark.asyncio
    async def test_search_success(self, client):
        mock_data = {
            "result": [
                {
                    "groupName": "proteins",
                    "items": [
                        {"type": "protein", "name": "9606.ENSP00000269305",
                         "text": "<span>P53</span> human tumor protein"},
                    ],
                },
            ],
            "etime": "0.123",
        }

        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            result = await client.search("P53")

        assert result["query"] == "P53"
        assert result["total"] == 1
        assert result["results"][0]["id"] == "9606.ENSP00000269305"
        assert result["results"][0]["label"] == "P53 human tumor protein"
        assert result["search_time"] == "0.123"

    @pytest.mark.asyncio
    async def test_get_database_stats_success(self, client):
        html = """
        <p class="text-3xl font-bold text-yellow-600">12k+</p>
        <p class="text-gray-700 text-sm mt-1">Annotated Species</p>
        <p class="text-3xl font-bold text-yellow-600">59M+</p>
        <p class="text-gray-700 text-sm mt-1">Protein Sequences</p>
        <p class="text-3xl font-bold text-yellow-600">1.1M+</p>
        <p class="text-gray-700 text-sm mt-1">Phylogenetic Trees</p>
        <p class="text-3xl font-bold text-yellow-600">3.1M+</p>
        <p class="text-gray-700 text-sm mt-1">Orthologous Groups</p>
        """

        with patch.object(client, "_fetch_text", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = html
            result = await client.get_database_stats()

        assert result["annotated_species"] == "12k+"
        assert result["protein_sequences"] == "59M+"
        assert result["version"] == "eggNOG 7"

    @pytest.mark.asyncio
    async def test_get_database_stats_connect_error_fallback(self, client):
        with patch.object(client, "_fetch_text", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = httpx.ConnectError("Connection refused")
            result = await client.get_database_stats()

        assert result["version"] == "eggNOG 7"
        assert result["annotated_species"] == "12k+"
        assert "note" in result
        assert "cached values" in result["note"]

    @pytest.mark.asyncio
    async def test_list_downloads(self, client):
        result = await client.list_downloads()
        assert result["version"] == "eggNOG 7"
        assert len(result["files"]) == 7
        assert "e7.proteins.fa.gz" in [f["file"] for f in result["files"]]

    @pytest.mark.asyncio
    async def test_get_taxid_info(self, client):
        result = await client.get_taxid_info(9606)
        assert result["taxid"] == 9606
        assert "download_url" in result
        assert "e7.taxid_info.tsv.gz" in result["download_url"]

    @pytest.mark.asyncio
    async def test_annotate_protein_success(self, client):
        mock_data = {
            "focus_prot": {
                "bestname": "TP53",
                "sp": "HUMAN",
                "taxid": "9606",
                "ukb": "P04637",
                "pfam": ["P53_TAD", "P53"],
                "ko": ["K04451"],
                "ogs": {"P53": [{"n": "P53@33154|A-1", "ns": 438, "nm": 1081,
                                  "lca": "Opisthokonta", "name": "Opisthokonta"}]},
            },
            "focus_og": {
                "n": "P53@9606|40E2",
                "lca": "Mammalia",
                "nm": 50,
                "ns": 10,
                "nlin": ["Eukaryota", "Mammalia"],
                "top_func": {
                    "kegg_ko": [["K04451", 0.11, "TP53", "tumor protein p53"]],
                    "GOslim": [["GO:0006355", 0.68, "regulation of transcription"]],
                    "kegg_gsymbol": ["TP53"],
                },
            },
            "focus_clu": {
                "n": "P53",
                "ogs": [{"nm": 1081, "ns": 438}],
            },
        }

        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            result = await client.annotate_protein("9606.ENSP00000269305")

        assert result["protein_id"] == "9606.ENSP00000269305"
        assert result["protein_name"] == "TP53"
        assert "kegg_ko_terms" in result
        assert result["kegg_ko_terms"][0]["ko_id"] == "K04451"
        assert "go_terms" in result

    @pytest.mark.asyncio
    async def test_annotate_protein_error(self, client):
        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_request = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_fetch.side_effect = httpx.HTTPStatusError(
                "Not Found", request=mock_request, response=mock_response
            )
            result = await client.annotate_protein("invalid.id")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_protein_family_success(self, client):
        mock_data = {
            "prots": {
                "HUMAN": ["9606.ENSP00000269305"],
                "MOUSE": ["10090.ENSMUSP00000123456"],
            },
            "sp": {"total": 2},
        }

        with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_data
            result = await client.get_protein_family("P53")

        assert result["protein_family"] == "P53"
        assert result["total_species"] == 2
        assert result["total_proteins"] == 2
        assert len(result["species"]) == 2
        assert "species_summary" in result

    @pytest.mark.asyncio
    async def test_close_client(self, client):
        await client._get_client()  # Initialize
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_client_when_not_initialized(self, client):
        # Should not raise when closing an uninitialized client
        await client.close()
        assert client._client is None


# ---------------------------------------------------------------------------
# Global client tests
# ---------------------------------------------------------------------------

class TestGlobalClient:
    @pytest.mark.asyncio
    async def test_get_client_singleton(self):
        # Reset global client
        await close_client()
        c1 = await get_client()
        c2 = await get_client()
        assert c1 is c2
        await close_client()

    @pytest.mark.asyncio
    async def test_close_client(self):
        await close_client()
        c = await get_client()
        await close_client()
        # After close, get_client should create a new one
        c2 = await get_client()
        assert c is not c2
        await close_client()
