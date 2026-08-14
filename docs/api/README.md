# Nexus API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

All endpoints (except `/health`, `/ready`, `/metrics`) require authentication via JWT token.

```
Authorization: Bearer <token>
```

## Endpoints

### Health

#### `GET /health`

Returns health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "nexus-api"
}
```

#### `GET /ready`

Returns readiness status.

**Response:**
```json
{
  "status": "ready"
}
```

### Authentication

#### `POST /api/v1/auth/register`

Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "name": "User Name",
  "password": "password123"
}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "organization_id": "uuid",
  "is_active": true
}
```

#### `POST /api/v1/auth/login`

Login and receive JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

### Sources

#### `GET /api/v1/sources/`

List all connected data sources.

**Response:**
```json
[
  {
    "id": "uuid",
    "integration_type": "github",
    "status": "connected",
    "last_synced_at": "2026-03-13T00:00:00Z"
  }
]
```

#### `POST /api/v1/sources/{type}/connect`

Connect a data source.

**Response:**
```json
{
  "status": "connected",
  "integration_type": "github"
}
```

#### `POST /api/v1/sources/{type}/disconnect`

Disconnect a data source.

**Response:**
```json
{
  "status": "disconnected",
  "integration_type": "github"
}
```

#### `POST /api/v1/sources/{type}/test`

Test a connection.

**Response:**
```json
{
  "status": "ok",
  "integration_type": "github",
  "message": "Connection test passed"
}
```

### Chat

#### `GET /api/v1/chat/sessions`

List chat sessions.

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "Sprint blockers investigation",
    "created_at": "2026-03-13T00:00:00Z"
  }
]
```

#### `POST /api/v1/chat/sessions`

Create a new chat session.

**Request:**
```json
{
  "title": "Optional title"
}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "New conversation",
  "created_at": "2026-03-13T00:00:00Z"
}
```

#### `GET /api/v1/chat/sessions/{id}`

Get a chat session with messages.

**Response:**
```json
{
  "id": "uuid",
  "title": "Session title",
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "What blockers were discussed?",
      "created_at": "2026-03-13T00:00:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "Based on my search...",
      "sources": [
        {
          "type": "slack",
          "url": "#",
          "title": "Slack messages"
        }
      ],
      "created_at": "2026-03-13T00:00:01Z"
    }
  ]
}
```

#### `POST /api/v1/chat/sessions/{id}/messages`

Send a message and receive streaming response.

**Request:**
```json
{
  "content": "What blockers were discussed?"
}
```

**Response:** Server-Sent Events stream

```
data: {"type": "thinking", "content": "Analyzing your question..."}

data: {"type": "tool_start", "tool": "slack_search_messages", "description": "Searching Slack..."}

data: {"type": "tool_result", "tool": "slack_search_messages", "duration_ms": 421}

data: {"type": "token", "content": "Based"}

data: {"type": "token", "content": " on"}

data: {"type": "sources", "sources": [{"type": "slack", "url": "#", "title": "Slack messages"}]}

data: {"type": "done"}
```

### Analytics

#### `GET /api/v1/analytics/`

Get analytics data.

**Response:**
```json
{
  "total_queries": 1248,
  "successful_queries": 1208,
  "failed_queries": 40,
  "avg_latency_ms": 3200.0,
  "avg_tool_calls_per_query": 2.7,
  "total_tokens": 847293,
  "estimated_cost": 18.42,
  "most_used_tools": [
    {"tool": "slack_search_messages", "count": 412},
    {"tool": "github_search_issues", "count": 389}
  ]
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

### HTTP Status Codes

- `200` — Success
- `201` — Created
- `400` — Bad request
- `401` — Unauthorized
- `403` — Forbidden
- `404` — Not found
- `429` — Rate limited
- `500` — Internal server error
