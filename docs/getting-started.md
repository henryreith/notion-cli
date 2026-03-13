# Getting Started

## Installation

```bash
npm install -g notion-agent-cli
```

Requires Node.js ≥18.

## Authentication

Run the interactive setup wizard:

```bash
notion auth setup
```

This prompts for your Notion integration token, saves it to
`~/.config/notion-agent/config.json`, and verifies the connection.

**Or set the token directly:**

```bash
notion auth set-token secret_xxxx...
notion auth test
```

**For scripts and agents** — use an environment variable instead of the config file:

```bash
export NOTION_API_KEY=secret_xxxx...
notion auth test
```

### Creating a Notion Integration Token

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **+ New integration**
3. Give it a name (e.g. "notion-agent-cli"), select your workspace
4. Copy the **Internal Integration Token** (starts with `secret_`)
5. Share any pages/databases you want to access with the integration (open the page → Share → Invite your integration)

## Finding Notion IDs

Every Notion page and database has a 32-character hex ID. You can find it in the URL:

```
https://www.notion.so/My-Page-abc123def456789012345678901234ab
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                  This is the page/database ID
```

The CLI accepts both raw IDs and full URLs — it extracts the ID automatically:

```bash
notion page get https://www.notion.so/My-Page-abc123def456789012345678901234ab
notion page get abc123def456789012345678901234ab
# Both work identically
```

## First Query

```bash
# Show a database schema
notion db schema <db-id>

# Query rows as a table
notion db query <db-id> --output table

# Filter rows
notion db query <db-id> --filter "Status:=:Active" --output table

# Get all rows (pagination handled automatically)
notion db query <db-id> --page-all --output json
```

## Adding Data

```bash
# Add a row with key=value pairs
notion db add <db-id> Name="My Item" Status="Active" Priority="High"

# Add a row from JSON
notion db add <db-id> --data '{"Name": "My Item", "Status": "Active"}'

# Upsert (insert or update based on a match)
notion db upsert <db-id> --match Name:"My Item" Status="Done"
```

## Non-Interactive Mode

For scripts, CI, and AI agents, suppress all prompts:

```bash
export NOTION_MODE=auto
# or per-command:
notion db delete <db-id> --mode auto --confirm
```

## Next Steps

- [Full command reference](commands.md) — all 30+ commands with flags and examples
- [Agent patterns](agent-patterns.md) — subprocess integration, piping, batch workflows
- [MCP vs CLI](mcp-vs-cli.md) — why the CLI is better for AI agents
