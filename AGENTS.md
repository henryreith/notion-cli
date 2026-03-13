# AGENTS.md — notion-agent-cli

This file is auto-read by AI coding assistants (Claude Code, Gemini CLI, GitHub Copilot, Cursor).
It provides agent-first context for working with and extending `notion-agent-cli`.

---

## What This Project Is

`notion-agent-cli` is a zero-overhead CLI for the Notion API, optimised for:

- **AI agent subprocess calls** — no MCP context overhead (saves 3,000–6,000 tokens/session)
- **Shell scripts and automation pipelines**
- **Human-readable output** with machine-parseable JSON mode

npm: `notion-agent-cli` | Binaries: `notion` + `notion-agent` (alias)

---

## Build & Test

```bash
npm install          # install dependencies
npm run build        # compile TypeScript → dist/
npm test             # run unit tests (vitest)
./dist/cli.js --help # verify build
```

---

## Architecture

- `src/cli.ts` — Commander root, registers all subcommands
- `src/client.ts` — wraps `@notionhq/client`, reads token, exports `normaliseId()`
- `src/errors.ts` — `ExitCode` enum + `die()` function (all exits go through here)
- `src/coerce.ts` — `coerceValue()`, `parseKV()`, `markdownToBlocks()`, `buildTypedFilter()`
- `src/schema.ts` — `SchemaCache` (15-min TTL disk cache) + `PropertyResolver`
- `src/output.ts` — `printJSON()`, `printTable()`, `printIds()`, `printId()`
- `src/modes.ts` — `getMode()`, `confirm()` — auto/interactive/ci
- `src/config.ts` — `getToken()`, `setToken()` — env var + config file
- `src/commands/` — one file per command group

---

## Key Rules

1. **All exits via `die(ExitCode.X, message)`** — never `process.exit()` directly
2. **All API calls via `createNotionClient()`** — never construct `Client` directly in commands
3. **All property writes via `PropertyResolver.resolveAll()`** — respects type coercion
4. **Token**: env `NOTION_API_KEY` takes priority over config file
5. **IDs**: always call `normaliseId()` before passing to SDK
6. **Errors to stderr as JSON**: `{"error": "message"}`

---

## Common Patterns

### Add a property write command
```typescript
const schema = await resolver.getSchema(dbId, client)
const properties = resolver.resolveAll(raw, schema)
await client.pages.create({ parent: { database_id: dbId }, properties })
```

### Handle --data flag
```typescript
import { readDataInput } from '../coerce.js'
const data = opts.data ? readDataInput(opts.data) : {}
```

### Rate-limited batch loop
```typescript
for (let i = 0; i < rows.length; i++) {
  await doWork(rows[i])
  if (i < rows.length - 1) await sleep(350) // 3 req/sec
}
```

---

## Token / Auth

```bash
export NOTION_API_KEY=secret_xxxx   # highest priority
notion auth setup                   # interactive wizard
notion auth set-token secret_xxxx   # programmatic
```

Config file: `~/.config/notion-agent/config.json`
Schema cache: `~/.cache/notion-agent/schemas/<db-id>.json`

---

## Exit Codes

| Code | Name | When |
|------|------|------|
| 0 | SUCCESS | OK |
| 1 | AUTH | No/invalid token |
| 2 | NOT_FOUND | Resource missing |
| 3 | VALIDATION | Bad input |
| 4 | API | Notion API error |
| 5 | EXISTS | Already exists |
| 6 | AMBIGUOUS | Upsert >1 match |
| 7 | DRY_RUN | Dry run only |
