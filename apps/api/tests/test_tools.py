import pytest

from app.core.config import settings
from app.orchestration.tools_slack import execute_slack_tool
from app.orchestration.tools_github import execute_github_tool
from app.orchestration.tools_hubspot import execute_hubspot_tool
from app.orchestration.tools_postgres import execute_postgres_tool


class TestToolsWithoutCredentials:
    @pytest.mark.asyncio
    async def test_slack_returns_not_connected_error(self, monkeypatch):
        monkeypatch.setattr(settings, "SLACK_BOT_TOKEN", "")
        result = await execute_slack_tool("slack_search_messages", {"query": "auth"})
        assert "error" in result
        assert "not connected" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_github_returns_not_connected_error(self, monkeypatch):
        monkeypatch.setattr(settings, "GITHUB_PERSONAL_ACCESS_TOKEN", "")
        result = await execute_github_tool("github_list_repositories", {})
        assert "error" in result
        assert "not connected" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_hubspot_returns_not_connected_error(self, monkeypatch):
        monkeypatch.setattr(settings, "HUBSPOT_ACCESS_TOKEN", "")
        result = await execute_hubspot_tool("hubspot_search_contacts", {"name": "test"})
        assert "error" in result
        assert "not configured" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_postgres_returns_connection_error(self, monkeypatch):
        monkeypatch.setattr(settings, "MCP_POSTGRES_USER", "")
        monkeypatch.setattr(
            settings,
            "DATABASE_URL",
            "postgresql+asyncpg://nexus:nexus@127.0.0.1:1/nexus",
        )
        result = await execute_postgres_tool("postgres_list_tables", {})
        assert "error" in result
