# My Mock Interview auth.md

## Overview

My Mock Interview provides authentication and registration protocols for AI agents to interact with interview preparation, mock interview sessions, and resume analysis APIs.

- **Audience**: AI Agents, Code Assistants, and Automated Systems
- **Resource Identifier**: `https://interview.nevatal.id`
- **Authorization Server**: `https://interview.nevatal.id`
- **Registration Endpoint**: `https://interview.nevatal.id/api/agent/register`
- **Token Endpoint**: `https://interview.nevatal.id/api/auth/token`
- **Supported Methods**: Bearer Token (`Authorization: Bearer <token>`)
- **Supported Scopes**: `read`, `write`, `interview`, `mcp`

## Agent Registration Flow

Agents can register or provision an API token:

```http
POST /api/agent/register HTTP/1.1
Host: interview.nevatal.id
Content-Type: application/json

{
  "client_name": "MyInterviewAgent",
  "client_uri": "https://example.com/agent"
}
```

Response:
```json
{
  "access_token": "interview_agent_token_sample",
  "token_type": "Bearer",
  "expires_in": 2592000,
  "scope": "read write interview mcp"
}
```

## Discovery Endpoints

- OAuth Authorization Server Metadata: [/.well-known/oauth-authorization-server](https://interview.nevatal.id/.well-known/oauth-authorization-server)
- OpenID Connect Configuration: [/.well-known/openid-configuration](https://interview.nevatal.id/.well-known/openid-configuration)
- OAuth Protected Resource Metadata: [/.well-known/oauth-protected-resource](https://interview.nevatal.id/.well-known/oauth-protected-resource)
- API Catalog: [/.well-known/api-catalog](https://interview.nevatal.id/.well-known/api-catalog)
- MCP Server Card: [/.well-known/mcp/server-card.json](https://interview.nevatal.id/.well-known/mcp/server-card.json)
- A2A Agent Card: [/.well-known/agent-card.json](https://interview.nevatal.id/.well-known/agent-card.json)
- Agent Skills Discovery: [/.well-known/agent-skills/index.json](https://interview.nevatal.id/.well-known/agent-skills/index.json)
