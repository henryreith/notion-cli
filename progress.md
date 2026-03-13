# notion-agent-cli Progress

## Milestones (Node.js/TypeScript Rewrite)

| Milestone | Feature | Status |
|-----------|---------|--------|
| M0 | Research & planning | COMPLETE |
| M1 | Scaffold: package.json, tsconfig, CLI skeleton, auth commands | COMPLETE |
| M2 | Core infrastructure: client.ts, errors.ts, output.ts, coerce.ts, modes.ts | COMPLETE |
| M3 | Schema module: SchemaCache (TTL disk cache), PropertyResolver | COMPLETE |
| M4 | db read commands: schema, query, info | COMPLETE |
| M5 | db write commands: add, upsert, update-row, add-option, batch-add, create, delete, update-schema | COMPLETE |
| M6 | page commands: create, get, get-property, set, append, delete, restore, move | COMPLETE |
| M7 | block commands: list, get, append, update, delete | COMPLETE |
| M8 | comment, search, user commands | COMPLETE |
| M9 | Integration tests + CI/CD (GitHub Actions for Node.js) | COMPLETE |
| M10 | Polish: skills, AGENTS.md, README, npm publish setup | COMPLETE |

## Step 0 — Repo Cleanup (2026-03-13)

- Deleted Python source: `notion/`, `tests/`, `pyproject.toml`
- Rewrote `CLAUDE.md` for Node.js architecture
- Updated `.gitignore` for Node.js
- Updated `AGENTS.md` for Node.js
- Updated `README.md` with npm install instructions

## M1–M10 Implementation (2026-03-13)

Full Node.js/TypeScript rewrite completed in a single session.

### Files Created

**Config & Build:**
- `package.json` — `notion-agent-cli`, bin: `notion` + `notion-agent`
- `tsconfig.json` — strict, ES2022, NodeNext modules
- `vitest.config.ts` — unit test config (excludes integration/)

**Source (`src/`):**
- `errors.ts` — `ExitCode` enum (0–7), `die()` function
- `config.ts` — `getToken()`, `setToken()`, `getConfigPath()` using native fs
- `client.ts` — `createNotionClient()`, `normaliseId()`, re-exports `collectPaginatedAPI`
- `output.ts` — `printJSON()`, `printTable()`, `printIds()`, `printId()`
- `modes.ts` — `getMode()`, `confirm()` — auto/interactive/ci
- `coerce.ts` — `parseKV()`, `readDataInput()`, `buildTypedFilter()`, `coerceValue()`, `markdownToBlocks()`, `looksLikeMarkdown()`
- `schema.ts` — `SchemaCache` (15-min TTL, `~/.cache/notion-agent/schemas/`), `PropertyResolver`
- `index.ts` — re-exports public API
- `cli.ts` — Commander root entry point
- `commands/auth.ts` — setup wizard, set-token, test, status
- `commands/db.ts` — all 10 db subcommands
- `commands/page.ts` — all 8 page subcommands
- `commands/block.ts` — all 5 block subcommands
- `commands/comment.ts` — add, list
- `commands/search.ts` — search with filter, sort, pagination
- `commands/user.ts` — list, get, me

**Tests (`tests/`):**
- `unit/coerce.test.ts` — parseKV, coerceValue (all 10 types), markdownToBlocks, buildTypedFilter
- `unit/schema.test.ts` — SchemaCache (hit/miss/TTL/invalidate), PropertyResolver
- `unit/output.test.ts` — printJSON, printId, printIds
- `unit/modes.test.ts` — getMode with flag/env/TTY detection
- `unit/auth.test.ts` — token env priority, normaliseId
- `integration/kb-pipeline.test.ts` — 12-step live API test (skipped without env vars)
- `fixtures/batch-5.json` — test fixture for batch-add

**CI/CD:**
- `.github/workflows/ci.yml` — Node.js 18/20/22 matrix
- `.github/workflows/publish.yml` — npm OIDC publish on v* tags

### Implementation Notes

- `conf` package replaced with native `fs` + JSON for simpler implementation (no ESM compat issues)
- `db list-templates` exits with code 4 — not exposed in `@notionhq/client` v5 SDK
- `db delete` uses `databases.update({ archived: true })` (SDK doesn't have a dedicated delete)
- `page move` uses `pages.update({ parent: { page_id: newParent } })`
- `block append` with `--type` + `--text` builds typed block bodies
- `buildTypedFilter` handles all 10 property types with correct filter key selection
- `markdownToBlocks` handles: h1/h2/h3, bullet/numbered lists, blockquote, code, divider, paragraph
- Rate limiting in `batch-add`: 350ms sleep between requests (3 req/sec)
- Schema cache uses file mtime for TTL (900s) — no embedded timestamp comparison needed
