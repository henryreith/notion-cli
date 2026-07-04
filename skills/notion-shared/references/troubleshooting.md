# Troubleshooting notion-agent-cli

Read this when a `notion` command fails. Errors are always JSON on stderr:
`{"error": "message", "hint": "..."}` — the exit code tells you which class of
failure you're in.

## Contents

- [Exit code → diagnosis → fix](#exit-code--diagnosis--fix)
- [Exit 1: authentication](#exit-1-authentication)
- [403 / "hasn't been shared": connecting pages to the integration](#403--hasnt-been-shared)
- [Exit 3: validation failures](#exit-3-validation-failures)
- [Rate limits (429)](#rate-limits-429)
- [Stale schema cache](#stale-schema-cache)

## Exit code → diagnosis → fix

| Exit | Meaning | First thing to try |
|------|---------|--------------------|
| 1 | Auth failed / permission denied | `notion auth test`; check `NOTION_API_KEY`; share the page with the integration |
| 2 | Not found | Verify the ID (`notion search "<name>"`); the resource may be in trash |
| 3 | Validation | Read the error — bad ID/URL, bad JSON in `--data`, unknown property, non-numeric number, or a delete without `--confirm` |
| 4 | API error | Inspect stderr; includes 429 rate limiting and malformed request bodies |
| 5 | Already exists | The resource exists (e.g. duplicate profile name) |
| 6 | Ambiguous upsert | `--match` found >1 row — add more `--match PROP:VALUE` conditions |
| 7 | Dry run | Not an error — `--dry-run` completed without writing |

## Exit 1: authentication

```bash
notion auth status    # which token is active and where it came from
notion auth test      # live connectivity check
```

Token resolution order: `NOTION_API_KEY` env → `NOTION_PROFILE` env / `--profile`
→ default profile in `~/.config/notion-agent/config.json`. An env var silently
overrides profiles — if the "wrong workspace" answers, check `env | grep NOTION`.

Tokens start with `ntn_` (older ones `secret_`). Regenerate at
https://www.notion.so/my-integrations if revoked.

## 403 / "hasn't been shared"

A valid token still can't see anything until pages are connected to the
integration. In Notion: open the page → `...` menu → **Connections** →
select your integration. Connecting a parent page grants access to all its
children — connect one top-level page rather than dozens of leaves.

Quick test after connecting:
```bash
notion search --limit 3   # should return the newly shared pages
```

## Exit 3: validation failures

- **"Not a valid Notion ID or URL"** — the CLI accepts a 32-char hex ID, a
  hyphenated UUID, or a notion.so URL. Copy the page URL directly from Notion.
- **"Invalid JSON in --data"** — quote the JSON for your shell; prefer
  `--data @file.json` for anything non-trivial.
- **"Refusing without confirmation in non-interactive mode"** — deletes need
  `--confirm` from scripts/agents (or `NOTION_AUTO_CONFIRM=1` for a trusted pipeline).
- **Unknown property** — property names are matched case-insensitively against
  the schema; run `notion db schema <db-id> --output properties` and use the
  exact name.
- **"Invalid number value"** — a `number` property received non-numeric input.

## Rate limits (429)

Notion allows ~3 requests/second. `db batch-add` self-throttles at 350ms per
row; if you build your own loop, do the same. On exit 4 with a rate-limit
message, wait a few seconds and retry — the CLI does not retry for you.

## Stale schema cache

Schemas cache for 15 minutes at `~/.cache/notion-agent/schemas/`. If you just
added a property or select option outside the CLI and writes are being dropped:

```bash
notion db schema <db-id> --refresh   # force re-fetch
```

`db add-option` and `db update-schema` invalidate the cache automatically.
