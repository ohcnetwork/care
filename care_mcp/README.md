# Care MCP

A [Model Context Protocol](https://modelcontextprotocol.io) server for
[CARE](https://github.com/ohcnetwork/care), shipped as a Care backend plugin.

It lets an AI assistant (Claude, Cursor, VS Code, or any MCP client) work with Care
as a specific Care user: look up the user's facilities, find admitted patients,
summarise a patient's record, read diagnoses, medications, observations, notes and
reports, and (if an operator allows it) make changes.

The server runs **inside Care**. Every tool call goes through Care's own API views,
so an assistant sees exactly what the same user would see in Care's web app: the
same querysets, the same `AuthorizationController` checks and the same errors.
Nothing here re-implements Care's permission logic.

## How it works

```
MCP client ──POST /api/care_mcp/mcp/──▶ MCPView (auth, origin check, rate limit)
                                            │ JSON-RPC: initialize, tools/*, prompts/*
                                            ▼
                                       tool handler
                                            │ call_api(user, "GET", "patient/<id>/diagnosis/")
                                            ▼
                         Care's URL resolver → Care's viewset, run as that user
```

- **Transport:** Streamable HTTP (protocol versions `2025-11-25`, `2025-06-18` and
  `2025-03-26`), answered with plain JSON. The server is stateless, so it works
  behind any number of gunicorn workers with no session store.
- **Authentication:** `Authorization: Bearer <token>`, where the token is either a
  personal **Care MCP access token** (recommended: long-lived, revocable, scoped)
  or a regular Care JWT.
- **Read-only by default.** The one write tool is only offered when the operator
  sets `CARE_MCP_ALLOW_WRITES` *and* the token was created with `allow_writes`.

## Install

Add the plug to Care's `plug_config.py`:

```python
care_mcp = Plug(
    name="care_mcp",
    package_name="git+https://github.com/ohcnetwork/care_mcp.git",
    version="@main",
    configs={},
)

plugs = [care_mcp]
```

or, without editing `plug_config.py`, at build time:

```bash
ADDITIONAL_PLUGS='[{"name":"care_mcp","package_name":"git+https://github.com/ohcnetwork/care_mcp.git","version":"@main"}]'
```

Then rebuild the image (`make down && make build && make up`) and run
`make migrate` (the plugin adds one table for access tokens).

For local development, clone this repo inside the Care checkout (a real
directory, not a symlink, so Docker builds can see it) and use
`package_name="care_mcp"` with `version=""`, which installs it in editable mode.
Without Docker, `pip install -e /path/to/care_mcp` into Care's virtualenv works too.

## Create an access token

As a logged-in Care user (with your normal Care JWT):

```bash
curl -X POST https://care.example.org/api/care_mcp/tokens/ \
  -H "Authorization: Bearer $CARE_JWT" -H "Content-Type: application/json" \
  -d '{"name": "Claude Desktop", "expires_in_days": 30}'
```

The response contains `token` (`care_mcp_…`). It is shown once; only its hash is
stored. `GET /api/care_mcp/tokens/` lists your tokens and
`DELETE /api/care_mcp/tokens/<id>/` revokes one. An MCP token cannot be used to
create or revoke tokens.

Operators can also mint one from the shell:

```bash
python manage.py create_mcp_token <username> --name "Claude Desktop" --days 30
```

## Connect a client

The endpoint is `https://<care-host>/api/care_mcp/mcp/`
(`GET /api/care_mcp/config/` returns it).

**Claude Code**

```bash
claude mcp add --transport http care https://care.example.org/api/care_mcp/mcp/ \
  --header "Authorization: Bearer care_mcp_..."
```

**Cursor, VS Code, Windsurf and other clients with remote-server support**

```json
{
  "mcpServers": {
    "care": {
      "url": "https://care.example.org/api/care_mcp/mcp/",
      "headers": { "Authorization": "Bearer care_mcp_..." }
    }
  }
}
```

**Claude Desktop** (through the `mcp-remote` bridge)

```json
{
  "mcpServers": {
    "care": {
      "command": "npx",
      "args": ["mcp-remote", "https://care.example.org/api/care_mcp/mcp/",
               "--header", "Authorization:${CARE_AUTH}"],
      "env": { "CARE_AUTH": "Bearer care_mcp_..." }
    }
  }
}
```

## Tools

| Tool | What it does |
| --- | --- |
| `get_current_user` | The caller, their roles, permissions, facilities and organizations |
| `search_users` | Find staff by name or username |
| `list_facilities`, `get_facility` | Facilities the user can see |
| `search_patients`, `get_patient` | Patients by name or phone; demographics |
| `list_encounters`, `get_encounter` | Visits and admissions at a facility or for a patient (`active_only` for "who is admitted now") |
| `get_patient_summary` | One-call snapshot: demographics, encounter, active diagnoses, symptoms, allergies, active medications, latest observations |
| `list_conditions` | Diagnoses or symptoms |
| `list_allergies` | Allergies and intolerances |
| `list_medications` | Prescriptions, reported medications, or administered doses |
| `list_observations`, `observation_trends` | Vitals and results; recent values per code |
| `list_questionnaire_responses` | Filled forms and assessments |
| `list_diagnostic_reports` | Lab and imaging reports |
| `list_service_requests` | Orders for an encounter or location |
| `get_notes` | Discussion threads with their latest messages |
| `list_api_endpoints`, `care_api_get` | Discover and read any other Care API v1 endpoint |
| `care_api_request` | POST/PUT/PATCH/DELETE any Care API v1 endpoint (only when writes are enabled) |

Prompts: `patient_summary` (clinical summary of a patient) and `shift_handover`
(handover notes for a facility's admitted patients).

Tool errors come back as tool results with `isError: true` and a hint (for example,
a 403 on clinical data tells the model to pass the `encounter_id` that grants
access), so the model can recover on its own.

## Settings

Resolution order: `PLUGIN_CONFIGS["care_mcp"][key]` → environment variable → default.

| Setting | Default | Meaning |
| --- | --- | --- |
| `CARE_MCP_ENABLED` | `True` | Master switch for the endpoint |
| `CARE_MCP_ALLOW_WRITES` | `False` | Offer the write tool to tokens created with `allow_writes` |
| `CARE_MCP_MAX_RESPONSE_CHARS` | `50000` | Truncate longer tool results |
| `CARE_MCP_TOKEN_DEFAULT_EXPIRY_DAYS` | `30` | Lifetime of a new token |
| `CARE_MCP_TOKEN_MAX_EXPIRY_DAYS` | `90` | Longest lifetime a user may ask for |
| `CARE_MCP_RATE_LIMIT` | `120/m` | Per-user request limit; `""` disables it |
| `CARE_MCP_ALLOWED_ORIGINS` | `""` | Comma-separated browser origins allowed to call the endpoint |

## Security notes

- The assistant acts with the full read access of the token's user. Create tokens
  for the least-privileged account that does the job.
- Credential, login, MFA, OTP and batch endpoints are unreachable through the
  generic API tools.
- Requests that carry an `Origin` header not in `CARE_MCP_ALLOWED_ORIGINS` are
  rejected, which stops a malicious web page from driving a local client's
  connection (DNS rebinding). Desktop and CLI clients send no `Origin`.
- Every tool call is logged (`care_mcp` logger: tool, user, outcome; arguments are
  not logged). Writes made through `care_api_request` run through Care's own views
  as the token's user, like any other API request.
- Patient data leaves Care when an assistant reads it. Only connect clients and
  model providers your deployment's data-protection rules allow.

## Not yet supported

- OAuth 2.1 authorization (needed for clients such as claude.ai custom connectors
  that only support OAuth). Bearer tokens cover Claude Code, Claude Desktop,
  Cursor and VS Code today.
- Patient-portal (OTP) users: the server only serves staff accounts.

## Development

```bash
make lint   # ruff check + ruff format --check
```

The tests run inside Care. From the Care checkout, with this repo installed
(`pip install -e /path/to/care_mcp`) and the plug registered, either in
`plug_config.py` or through `ADDITIONAL_PLUGS`:

```bash
ADDITIONAL_PLUGS='[{"name":"care_mcp","package_name":"care_mcp","version":""}]' \
  python manage.py test care_mcp --keepdb
```
