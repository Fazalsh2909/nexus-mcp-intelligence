from typing import Dict, Any, List
import httpx

from app.core.config import settings


async def _github_token(db=None, user_id: str = "") -> str:
    """Resolve a GitHub access token: env override first, then the stored
    OAuth token on the user's connection record."""
    if settings.GITHUB_PERSONAL_ACCESS_TOKEN:
        return settings.GITHUB_PERSONAL_ACCESS_TOKEN

    if db is not None and user_id:
        from sqlalchemy import select

        from app.models.models import Connection

        result = await db.execute(
            select(Connection).where(
                Connection.user_id == user_id,
                Connection.integration_type == "github",
                Connection.status == "connected",
            )
        )
        conn = result.scalar_one_or_none()
        if conn and conn.metadata_json:
            return str(conn.metadata_json.get("access_token") or "")
    return ""


async def _gh_get(token: str, url: str, params: Dict[str, Any] | None = None) -> Any:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code == 401:
            return {
                "error": "GitHub authentication failed. Reconnect the source in Sources."
            }
        if resp.status_code == 404:
            return {
                "error": "GitHub resource not found. Check the repository/owner arguments."
            }
        resp.raise_for_status()
        return resp.json()


async def execute_github_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str = "",
    organization_id: str = "",
    db=None,
) -> Dict[str, Any]:
    token = await _github_token(db=db, user_id=user_id)
    if not token:
        return {
            "error": (
                "GitHub is not connected. Click Connect on the Sources page to "
                "authorize the app, or set GITHUB_PERSONAL_ACCESS_TOKEN in .env."
            )
        }

    try:
        if tool_name == "github_list_repositories":
            owner = arguments.get("owner", "")
            url = (
                f"https://api.github.com/orgs/{owner}/repos"
                if owner
                else "https://api.github.com/user/repos"
            )
            params: Dict[str, Any] = {}
            visibility = arguments.get("visibility")
            if visibility and visibility != "all":
                params["visibility"] = visibility
            repos = await _gh_get(token, url, params)
            if isinstance(repos, dict) and repos.get("error"):
                return repos
            return {
                "repositories": [
                    {
                        "name": r["name"],
                        "full_name": r["full_name"],
                        "description": r.get("description"),
                        "private": r["private"],
                        "url": r["html_url"],
                        "default_branch": r.get("default_branch"),
                    }
                    for r in repos
                ],
                "total": len(repos),
            }

        elif tool_name == "github_search_issues":
            parts = [arguments.get("query", "")]
            if arguments.get("repository"):
                parts.append(f"repo:{arguments['repository']}")
            if arguments.get("state") and arguments["state"] != "all":
                parts.append(f"state:{arguments['state']}")
            if arguments.get("labels"):
                for label in arguments["labels"]:
                    parts.append(f'label:"{label}"')
            if arguments.get("author"):
                parts.append(f"author:{arguments['author']}")
            data = await _gh_get(
                token,
                "https://api.github.com/search/issues",
                {
                    "q": " ".join(parts),
                    "per_page": min(int(arguments.get("limit", 20)), 50),
                },
            )
            if data.get("error"):
                return data
            return {
                "issues": [
                    {
                        "number": i["number"],
                        "title": i["title"],
                        "state": i["state"],
                        "labels": [label["name"] for label in i.get("labels", [])],
                        "author": (i.get("user") or {}).get("login"),
                        "assignee": (i.get("assignee") or {}).get("login")
                        if i.get("assignee")
                        else None,
                        "created_at": i["created_at"],
                        "updated_at": i.get("updated_at"),
                        "url": i["html_url"],
                        "repository": i.get("repository_url", "").replace(
                            "https://api.github.com/repos/", ""
                        ),
                        "body": (i.get("body") or "")[:1000],
                        "comments": i.get("comments", 0),
                    }
                    for i in data.get("items", [])
                ],
                "total": data.get("total_count", 0),
            }

        elif tool_name == "github_get_issue":
            repo = arguments.get("repository", "")
            number = arguments.get("issue_number", 0)
            if not repo or not number:
                return {"error": "repository and issue_number are required"}
            i = await _gh_get(
                token, f"https://api.github.com/repos/{repo}/issues/{number}"
            )
            if i.get("error"):
                return i
            return {
                "number": i["number"],
                "title": i["title"],
                "state": i["state"],
                "labels": [label["name"] for label in i.get("labels", [])],
                "author": (i.get("user") or {}).get("login"),
                "assignee": (i.get("assignee") or {}).get("login")
                if i.get("assignee")
                else None,
                "created_at": i["created_at"],
                "url": i["html_url"],
                "repository": repo,
                "body": i.get("body") or "",
                "comments": i.get("comments", 0),
            }

        elif tool_name == "github_get_issue_comments":
            repo = arguments.get("repository", "")
            number = arguments.get("issue_number", 0)
            if not repo or not number:
                return {"error": "repository and issue_number are required"}
            data = await _gh_get(
                token,
                f"https://api.github.com/repos/{repo}/issues/{number}/comments",
                {"per_page": 50},
            )
            if isinstance(data, dict) and data.get("error"):
                return data
            return {
                "comments": [
                    {
                        "author": (c.get("user") or {}).get("login"),
                        "created_at": c["created_at"],
                        "body": (c.get("body") or "")[:1000],
                        "url": c["html_url"],
                    }
                    for c in data
                ],
                "total": len(data),
            }

        elif tool_name == "github_search_code":
            parts = [arguments.get("query", "")]
            if arguments.get("repository"):
                parts.append(f"repo:{arguments['repository']}")
            data = await _gh_get(
                token,
                "https://api.github.com/search/code",
                {
                    "q": " ".join(parts),
                    "per_page": min(int(arguments.get("limit", 10)), 50),
                },
            )
            if data.get("error"):
                return data
            return {
                "results": [
                    {
                        "repository": i["repository"]["full_name"],
                        "path": i["path"],
                        "url": i["html_url"],
                    }
                    for i in data.get("items", [])
                ],
                "total": data.get("total_count", 0),
            }

        elif tool_name == "github_create_issue":
            return {
                "error": (
                    "Write actions are disabled. GitHub issues can only be "
                    "created after the workspace is connected with write scope."
                )
            }

        return {"error": f"Unknown GitHub tool: {tool_name}"}
    except httpx.HTTPError as e:
        return {"error": f"GitHub request failed: {str(e)}"}


github_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "github_list_repositories",
            "description": "List repositories for a user or organization",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "GitHub user or organization",
                    },
                    "visibility": {
                        "type": "string",
                        "enum": ["public", "private", "all"],
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_search_issues",
            "description": "Search GitHub issues across repositories",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "repository": {
                        "type": "string",
                        "description": "Optional repo in owner/repo format",
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by labels",
                    },
                    "state": {"type": "string", "enum": ["open", "closed", "all"]},
                    "author": {"type": "string", "description": "Filter by author"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_get_issue",
            "description": "Get details of a specific GitHub issue",
            "parameters": {
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Repo in owner/repo format",
                    },
                    "issue_number": {"type": "integer", "description": "Issue number"},
                },
                "required": ["repository", "issue_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_get_issue_comments",
            "description": "Get comments on a GitHub issue",
            "parameters": {
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Repo in owner/repo format",
                    },
                    "issue_number": {"type": "integer", "description": "Issue number"},
                },
                "required": ["repository", "issue_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_create_issue",
            "description": "Create a new GitHub issue. REQUIRES USER CONFIRMATION.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Repo in owner/repo format",
                    },
                    "title": {"type": "string", "description": "Issue title"},
                    "body": {"type": "string", "description": "Issue body"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Labels to apply",
                    },
                },
                "required": ["repository", "title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_search_code",
            "description": "Search code in GitHub repositories",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Code search query"},
                    "repository": {
                        "type": "string",
                        "description": "Optional repo in owner/repo format",
                    },
                },
                "required": ["query"],
            },
        },
    },
]
