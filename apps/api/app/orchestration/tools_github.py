from typing import Dict, Any, List
import httpx

from app.core.config import settings
from app.orchestration.credentials import resolve_credential
from app.orchestration.http import call_with_retry, friendly_error

_GITHUB_API = "https://api.github.com"


async def _github_token(db=None, user_id: str = "") -> str:
    """Resolve a GitHub access token: env override first, then the encrypted
    OAuth token stored on the user's connection record."""
    return await resolve_credential(
        db, user_id, "github", settings.GITHUB_PERSONAL_ACCESS_TOKEN, ("access_token",)
    )


async def _gh_call(
    token: str,
    method: str,
    url: str,
    params: Dict[str, Any] | None = None,
    json_body: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Perform a GitHub API call with bounded retry + backoff and friendly
    user-facing errors (details stay in the logs)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await call_with_retry(
                client,
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
                friendly_name="GitHub",
            )
        if resp.status_code in (401, 403):
            return {
                "error": "GitHub authentication failed. Reconnect the source in Sources."
            }
        if resp.status_code == 404:
            return {
                "error": "GitHub resource not found. Check the repository/owner arguments."
            }
        if resp.status_code == 429:
            return {
                "error": "GitHub is rate-limiting requests right now. Wait a moment and try again."
            }
        if resp.status_code >= 500:
            return {"error": "GitHub is having a temporary outage. Try again shortly."}
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        return friendly_error("GitHub", e, context="request")


async def _gh_get(token: str, url: str, params: Dict[str, Any] | None = None) -> Any:
    return await _gh_call(token, "GET", url, params=params)


def _evidence_issue(i: Dict[str, Any], snippet: str = "") -> Dict[str, Any]:
    return {
        "source": "github",
        "type": "issue",
        "id": str(i.get("number", "")),
        "title": i.get("title", ""),
        "url": i.get("html_url", ""),
        "timestamp": i.get("updated_at"),
        "content": (i.get("body") or snippet or "")[:1000],
    }


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

    if tool_name == "github_list_repositories":
        owner = arguments.get("owner", "")
        url = (
            f"{_GITHUB_API}/orgs/{owner}/repos"
            if owner
            else f"{_GITHUB_API}/user/repos"
        )
        params: Dict[str, Any] = {}
        visibility = arguments.get("visibility")
        if visibility and visibility != "all":
            params["visibility"] = visibility
        data = await _gh_get(token, url, params)
        if isinstance(data, dict) and data.get("error"):
            return data
        repos = data if isinstance(data, list) else []
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
            "evidence": [
                {
                    "source": "github",
                    "type": "repository",
                    "id": r["full_name"],
                    "title": r["full_name"],
                    "url": r["html_url"],
                    "timestamp": None,
                    "content": (r.get("description") or "")[:500],
                }
                for r in repos[:5]
            ],
        }

    elif tool_name == "github_search_issues":
        parts = [arguments.get("query", "")]
        if arguments.get("repository"):
            parts.append(f"repo:{arguments['repository']}")
        if arguments.get("labels"):
            parts.append("label:" + ",".join(arguments["labels"]))
        if arguments.get("state") and arguments["state"] != "all":
            parts.append(f"state:{arguments['state']}")
        if arguments.get("author"):
            parts.append(f"author:{arguments['author']}")
        data = await _gh_get(
            token,
            f"{_GITHUB_API}/search/issues",
            {
                "q": " ".join(parts),
                "per_page": min(int(arguments.get("limit", 20)), 50),
            },
        )
        if data.get("error"):
            return data
        items = data.get("items", [])
        return {
            "issues": [
                {
                    "number": i["number"],
                    "title": i["title"],
                    "state": i["state"],
                    "labels": [label["name"] for label in i.get("labels", [])],
                    "author": (i.get("user") or {}).get("login"),
                    "assignee": (
                        (i.get("assignee") or {}).get("login")
                        if i.get("assignee")
                        else None
                    ),
                    "created_at": i["created_at"],
                    "updated_at": i.get("updated_at"),
                    "url": i["html_url"],
                    "repository": i.get("repository_url", "").replace(
                        f"{_GITHUB_API}/repos/", ""
                    ),
                    "body": (i.get("body") or "")[:1000],
                    "comments": i.get("comments", 0),
                }
                for i in items
            ],
            "total": data.get("total_count", 0),
            "evidence": [_evidence_issue(i) for i in items[:5]],
        }

    elif tool_name == "github_get_issue":
        repo = arguments.get("repository", "")
        number = arguments.get("issue_number", 0)
        if not repo or not number:
            return {"error": "repository and issue_number are required"}
        i = await _gh_get(token, f"{_GITHUB_API}/repos/{repo}/issues/{number}")
        if i.get("error"):
            return i
        return {
            "number": i["number"],
            "title": i["title"],
            "state": i["state"],
            "labels": [label["name"] for label in i.get("labels", [])],
            "author": (i.get("user") or {}).get("login"),
            "assignee": (
                (i.get("assignee") or {}).get("login") if i.get("assignee") else None
            ),
            "created_at": i["created_at"],
            "url": i["html_url"],
            "repository": repo,
            "body": i.get("body") or "",
            "comments": i.get("comments", 0),
            "evidence": [_evidence_issue(i)],
        }

    elif tool_name == "github_get_issue_comments":
        repo = arguments.get("repository", "")
        number = arguments.get("issue_number", 0)
        if not repo or not number:
            return {"error": "repository and issue_number are required"}
        data = await _gh_get(
            token,
            f"{_GITHUB_API}/repos/{repo}/issues/{number}/comments",
            {"per_page": 50},
        )
        if isinstance(data, dict) and data.get("error"):
            return data
        comments = data if isinstance(data, list) else []
        return {
            "comments": [
                {
                    "author": (c.get("user") or {}).get("login"),
                    "created_at": c["created_at"],
                    "body": (c.get("body") or "")[:1000],
                    "url": c["html_url"],
                }
                for c in comments
            ],
            "total": len(comments),
            "evidence": [
                {
                    "source": "github",
                    "type": "comment",
                    "id": str(c.get("id", "")),
                    "title": f"Comment by {(c.get('user') or {}).get('login', '')} on #{number}",
                    "url": c.get("html_url", ""),
                    "timestamp": c.get("created_at"),
                    "content": (c.get("body") or "")[:1000],
                }
                for c in comments[:5]
            ],
        }

    elif tool_name == "github_search_code":
        parts = [arguments.get("query", "")]
        if arguments.get("repository"):
            parts.append(f"repo:{arguments['repository']}")
        data = await _gh_get(
            token,
            f"{_GITHUB_API}/search/code",
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
        repo = arguments.get("repository", "")
        title = arguments.get("title", "")
        if not repo or not title:
            return {"error": "repository and title are required"}
        body: Dict[str, Any] = {"title": title}
        if arguments.get("body"):
            body["body"] = arguments["body"]
        if arguments.get("labels"):
            body["labels"] = arguments["labels"]
        created = await _gh_call(
            token, "POST", f"{_GITHUB_API}/repos/{repo}/issues", json_body=body
        )
        if created.get("error"):
            return created
        return {
            "created": True,
            "issue_number": created.get("number"),
            "title": created.get("title"),
            "url": created.get("html_url"),
            "repository": repo,
            "evidence": [
                {
                    "source": "github",
                    "type": "issue",
                    "id": str(created.get("number", "")),
                    "title": created.get("title", ""),
                    "url": created.get("html_url", ""),
                    "timestamp": created.get("created_at"),
                    "content": (created.get("body") or "")[:1000],
                }
            ],
        }

    return {"error": f"Unknown GitHub tool: {tool_name}"}


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
            "description": (
                "Create a new GitHub issue. This is a WRITE action and always "
                "requires explicit user confirmation before it executes."
            ),
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
