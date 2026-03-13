# notion-agent-cli — Project Memory

## Status: COMPLETE (2026-03-13)

All 13 milestones implemented. The project is production-ready and PyPI-publishable.

## Architecture Summary

- **Entry point:** `notion/__main__.py` → `notion/cli.py` (Click group registering all subcommands)
- **Commands:** `notion/commands/` — `db.py`, `page.py`, `block.py`, `comment.py`, `search.py`, `user.py`, `auth.py`
- **Client:** `notion/client.py` — thin httpx wrapper with `_normalise_id`, `paginate`, rate-limit awareness
- **Schema layer:** `notion/schema.py` — `PropertyResolver`, `coerce_value`, `markdown_to_blocks`, file-based schema cache
- **Modes:** `notion/modes.py` — `get_mode()` (interactive/auto/ci), `confirm()` helper
- **Errors:** `notion/errors.py` — typed exit codes 0–7

## Key Design Decisions

- Zero MCP overhead: subprocess-callable, all output to stdout as JSON
- Exit codes are semantic (see `notion/errors.py`): 0=ok, 1=auth, 2=not found, 3=validation, 4=api, 5=exists, 6=ambiguous, 7=dry-run
- Schema cache stored in `~/.cache/notion-agent/schemas/<db-id>.json` (bypassed with `--no-cache`)
- Rate limiting: 0.34s sleep between writes in batch operations (3 req/sec)
- `--output` flag on most commands: `json` (default), `table`, `ids`, `id`, `properties`, `options`

## Test Suite

- **140 unit/integration-mock tests** in `tests/` (excluding `tests/integration/`)
- **18-step live integration pipeline** in `tests/integration/test_kb_pipeline.py` (skipped without real API keys)
- Run unit tests: `pytest tests/ --ignore=tests/integration -v`
- Run integration tests: `NOTION_API_KEY=... NOTION_TEST_PARENT_ID=... pytest tests/integration/ -v -s`

## Build & Release

- Package name: `notion-agent-cli` (PyPI), module name: `notion`
- Build: `python -m build` → `dist/notion_agent_cli-0.1.0.tar.gz` + `.whl`
- Publish: `git tag v0.1.0 && git push origin v0.1.0` → triggers `.github/workflows/publish.yml`
- CI: `.github/workflows/ci.yml` runs on push/PR to main across Python 3.10/3.11/3.12

## Milestones Completed

M1 (scaffold) → M2 (auth) → M3 (db schema) → M4 (db query) → M5 (db add) →
M6 (db upsert + update-row) → M7 (add-option) → M8 (page commands) →
M9 (batch-add + cache fix) → M10 (block/comment/search/user + db create/delete) →
M11 (modes + edge cases) → M12 (integration test suite) → M13 (polish + PyPI prep)
