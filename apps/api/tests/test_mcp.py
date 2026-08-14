import pytest

from app.orchestration import mcp_client
from app.orchestration.tools import TOOL_DEFINITIONS, WRITE_TOOLS, execute_tool

# One event loop for the whole module so the cached async engine's pooled
# connections stay bound to a live loop across tests.
pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _db_available() -> bool:
    try:
        from sqlalchemy import text

        from app.db.session import async_session

        async with async_session() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


class TestMcpDiscovery:
    async def test_discovery_matches_registry(self):
        discovered = await mcp_client.discover_tools()
        names = {t["function"]["name"] for t in discovered}
        registry = {t["function"]["name"] for t in TOOL_DEFINITIONS}
        assert names == registry
        assert len(names) >= 20
        await mcp_client.close_all()

    async def test_every_server_is_represented(self):
        discovered = await mcp_client.discover_tools()
        names = {t["function"]["name"] for t in discovered}
        for prefix in ("slack_", "github_", "hubspot_", "postgres_"):
            assert any(n.startswith(prefix) for n in names)
        await mcp_client.close_all()

    async def test_unknown_tool_routing_raises(self):
        with pytest.raises(ValueError):
            await mcp_client.call_tool("not_a_tool", {})


class TestMcpInvocation:
    async def test_call_tool_through_mcp_without_connection(self):
        if not await _db_available():
            pytest.skip("database not reachable")
        result = await mcp_client.call_tool(
            "github_list_repositories",
            {},
            user_id="00000000-0000-0000-0000-000000000000",
        )
        assert isinstance(result, dict)
        assert "error" in result
        await mcp_client.close_all()

    async def test_execute_tool_routes_through_gateway(self):
        if not await _db_available():
            pytest.skip("database not reachable")
        result = await execute_tool(
            "github_list_repositories",
            {},
            user_id="00000000-0000-0000-0000-000000000000",
        )
        assert isinstance(result, dict)
        assert "error" in result
        await mcp_client.close_all()

    async def test_write_tool_registered_and_gated(self):
        names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
        assert "github_create_issue" in names
        assert WRITE_TOOLS <= names
        assert "github_create_issue" in WRITE_TOOLS
