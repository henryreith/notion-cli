# MCP vs CLI: Why the CLI Wins for AI Agents

## The Token Cost Problem

The Notion MCP server is a well-built tool — but it has an unavoidable overhead: every time an
AI agent starts a session, the MCP server loads its full tool manifest into the context window.

That manifest is **3,000–6,000 tokens**, loaded unconditionally, whether the agent calls
Notion zero times or a hundred times.

## How the CLI Avoids This

`notion-agent-cli` is invoked as a subprocess — a shell command — rather than a long-lived MCP
server. The agent's skill definition (the few hundred tokens describing how to use the CLI) is
only loaded when the agent explicitly needs it.

| | MCP Server | notion-agent-cli |
|---|---|---|
| **Token cost** | 3,000–6,000 tokens, always | ~0 when not in use |
| **Skill load cost** | N/A (always loaded) | ~800–1,200 tokens, once per session |
| **Per-call overhead** | 0 (already loaded) | 0 (subprocess) |
| **Server process** | Required (persistent) | None |
| **Setup** | MCP config + server | `npm install -g` |

## Real-World Token Math

Consider an AI agent doing a 50-step workflow where 10 steps call Notion:

**With MCP:**
- Tool manifest loaded: ~4,500 tokens (fixed)
- Per-call overhead: 0
- Total Notion overhead: **~4,500 tokens**

**With notion-agent-cli:**
- Skill loaded once (when first needed): ~1,000 tokens
- Per-call overhead: 0 (subprocess)
- Total Notion overhead: **~1,000 tokens**

**Savings: ~3,500 tokens per session** — more context available for actual work.

At scale (50 agent sessions/day), that's 175,000 tokens/day saved, which translates directly
to reduced API costs and more available context for reasoning.

## Feature Parity + Extras

`notion-agent-cli` covers all the operations available in the Notion MCP server, plus several
higher-level helpers that aren't in MCP:

| Feature | MCP | notion-agent-cli |
|---------|-----|-----------------|
| Query database | ✓ | ✓ |
| Create page | ✓ | ✓ |
| Update page | ✓ | ✓ |
| Search | ✓ | ✓ |
| List users | ✓ | ✓ |
| Comments | ✓ | ✓ |
| **Upsert (insert or update)** | ✗ | ✓ |
| **Batch add (bulk insert)** | ✗ | ✓ |
| **Schema cache (15-min TTL)** | ✗ | ✓ |
| **Auto-create select options** | ✗ | ✓ (`--add-options`) |
| **Markdown read/write** | ✗ | ✓ |
| **Pagination helpers** | ✗ | ✓ (`--page-all`) |
| **Dry-run mode** | ✗ | ✓ (`--dry-run`) |
| **Machine-parseable IDs output** | ✗ | ✓ (`--output ids`) |

## Practical Considerations

**When to use MCP:**
- You're in Claude.ai or another MCP-native environment
- You want point-and-click tool invocation without a shell
- You're doing one-off interactive queries

**When to use notion-agent-cli:**
- You're building an AI agent that runs many sessions
- You're writing shell scripts or automation pipelines
- Token budget matters (it always does)
- You need batch operations, upserts, or schema caching
- You want to pipe Notion data through standard Unix tools

## Same JSON, Same API

Both tools call the official Notion REST API (`api.notion.com/v1`) using the official
`@notionhq/client` SDK. The data you get back is identical. The auth model is identical
(Notion integration token). The only difference is how the tool is invoked and what it
costs in tokens.
