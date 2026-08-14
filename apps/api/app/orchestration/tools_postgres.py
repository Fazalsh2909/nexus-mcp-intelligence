from typing import Dict, Any, List
import re
import asyncpg

from app.core.config import settings

postgres_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "postgres_list_tables",
            "description": "List all tables in the connected database",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "postgres_describe_table",
            "description": "Get the schema of a specific table",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to describe",
                    },
                },
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "postgres_query",
            "description": "Run a read-only SELECT query against the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT query (read-only)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max rows to return",
                        "default": 100,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "postgres_count",
            "description": "Count rows in a table with optional filter",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Table to count"},
                    "where": {"type": "string", "description": "Optional WHERE clause"},
                },
                "required": ["table_name"],
            },
        },
    },
]

DANGEROUS_PATTERNS = [
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE)\b",
    r";\s*\w",
    r"--",
    r"/\*",
]


def _validate_query(query: str) -> bool:
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT") and not query_upper.startswith("WITH"):
        return False
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            return False
    return True


async def _pg_dsn() -> str:
    """Connection string for the analytics database.

    Uses MCP_POSTGRES_* overrides when set, otherwise falls back to the
    application DATABASE_URL credentials.
    """
    if settings.MCP_POSTGRES_USER and settings.MCP_POSTGRES_PASSWORD:
        return (
            f"postgresql://{settings.MCP_POSTGRES_USER}:{settings.MCP_POSTGRES_PASSWORD}"
            f"@{settings.MCP_POSTGRES_HOST}:{settings.MCP_POSTGRES_PORT}/{settings.MCP_POSTGRES_DB}"
        )
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


async def _pg_connect():
    return await asyncpg.connect(await _pg_dsn(), timeout=10)


def _rows_to_records(rows: List[asyncpg.Record], limit: int) -> List[Dict[str, Any]]:
    records = [dict(r) for r in rows[:limit]]
    for rec in records:
        for k, v in rec.items():
            if hasattr(v, "isoformat"):
                rec[k] = v.isoformat()
    return records


async def execute_postgres_tool(
    tool_name: str, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        conn = await _pg_connect()
    except Exception as e:
        return {"error": f"PostgreSQL connection failed: {str(e)}"}

    try:
        if tool_name == "postgres_list_tables":
            rows = await conn.fetch(
                """
                SELECT table_name AS name, table_schema AS schema
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
                """
            )
            tables = [dict(r) for r in rows]
            return {"tables": tables, "total": len(tables)}

        elif tool_name == "postgres_describe_table":
            table = arguments.get("table_name", "")
            if not table:
                return {"error": "table_name is required"}
            rows = await conn.fetch(
                """
                SELECT column_name AS column, data_type AS type,
                       is_nullable = 'NO' AS nullable
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
                """,
                table,
            )
            columns = [dict(r) for r in rows]
            if not columns:
                return {"error": f"Table '{table}' not found"}
            return {"table": table, "columns": columns}

        elif tool_name == "postgres_query":
            query = arguments.get("query", "")
            if not _validate_query(query):
                return {"error": "Query rejected: only SELECT statements are allowed"}
            limit = int(arguments.get("limit", 100))
            rows = await conn.fetch(query)
            records = _rows_to_records(rows, limit)
            cols = list(records[0].keys()) if records else []
            return {
                "columns": cols,
                "rows": records,
                "row_count": len(rows),
                "truncated": len(rows) > limit,
            }

        elif tool_name == "postgres_count":
            table = arguments.get("table_name", "")
            if not table:
                return {"error": "table_name is required"}
            where = arguments.get("where", "")
            sql = f"SELECT count(*) AS count FROM {table}"
            if where:
                sql += f" WHERE {where}"
            row = await conn.fetchrow(sql)
            return {"table": table, "count": row["count"]}

        return {"error": f"Unknown PostgreSQL tool: {tool_name}"}
    except Exception as e:
        return {"error": f"PostgreSQL query failed: {str(e)}"}
    finally:
        await conn.close()
