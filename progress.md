# notion-agent-cli Progress

## Milestones

| Milestone | Feature | Status |
|-----------|---------|--------|
| M9 | `notion db batch-add` + cache isolation fix | COMPLETE |
| M10 | Remaining commands (block, comment, search, user) + db create/delete | COMPLETE |
| M11 | Modes + Edge Case Hardening | COMPLETE |
| M12 | Integration Test Suite (18-step KB pipeline) | COMPLETE |
| M13 | Polish + PyPI Prep | COMPLETE |

## M13 Notes

- **`pyproject.toml`:** Added `authors = [{name = "Henry Reith"}]`, `[project.urls]` block with Homepage/Repository/Issues, and `build>=1.0` to dev dependencies.

- **`.github/workflows/ci.yml`:** Created CI workflow that runs tests on Python 3.10/3.11/3.12 on push/PR to main, excluding integration tests.

- **`.github/workflows/publish.yml`:** Created PyPI publish workflow triggered on `v*` tags using trusted publishing (OIDC, no secrets needed).

- **`DEPLOY.md`:** Created deployment guide covering manual PyPI upload, GitHub Actions tag-based release, installation verification, and Homebrew formula template.

- **`README.md`:** Replaced stub with comprehensive documentation including badges, why-not-MCP rationale, full command reference, output formats, exit codes table, and agent integration example.

- **Build verified:** `python -m build` produces `dist/notion_agent_cli-0.1.0.tar.gz` and `dist/notion_agent_cli-0.1.0-py3-none-any.whl` cleanly.

- **All 140 tests pass.**

## M12 Notes

- **`tests/integration/test_kb_pipeline.py`:** Replaced placeholder with full 18-step `TestKBPipeline` class covering: auth, DB create, schema fetch, add select options, idempotent add-option, 3x add entries, query all, query filter, upsert create, upsert update, batch-add dry-run, page get, page append, search, user me, cleanup/delete DB. Auto-skipped unless `NOTION_API_KEY` and `NOTION_TEST_PARENT_ID` are set.

- **`tests/integration/__init__.py`:** Confirmed present from M1.

## M11 Notes

- **`notion/modes.py`:** Updated `get_mode()` to validate `NOTION_MODE` env var against allowed values (`interactive`, `auto`, `ci`) — invalid values now fall through to TTY detection. Updated `confirm()` signature: `mode` param now defaults to `None` (calls `get_mode()` internally instead of hardcoding `"auto"`).

- **`tests/test_modes.py`:** Replaced placeholder with 12 tests covering `get_mode()` (explicit flag priority, env var, env var override, invalid env fallthrough, TTY detection) and `confirm()` (auto/ci always True, interactive prompts, cancellation, no-mode uses get_mode).

- **`notion/commands/db.py`:** Added `--no-cache` flag to `add` and `upsert` commands. When `--no-cache` is set, the schema cache is neither read nor written.

- **`notion/schema.py`:** `PropertyResolver.resolve_all()` now skips properties with `None` values instead of passing them to the coercion layer.

- **`notion/client.py`:** `_normalise_id` already handled all four edge cases correctly (URL with slug, URL without slug, UUID with hyphens, plain 32-char hex). No changes needed.

- **All 140 tests pass** (129 previously + 9 new modes tests + 2 from test count growth).

## M10 Notes

- **`notion/commands/block.py`:** Implemented `list`, `get`, `append`, `update`, `delete`. Uses `client.paginate("GET", ...)` for listing children. `append` builds a `type_map` for common block types, falling back to paragraph. `delete` calls `client.delete()` and returns `{"status": "deleted", "id": ...}`.

- **`notion/commands/comment.py`:** Implemented `add` (POST `/comments`) and `list` (GET `/comments?block_id=...` via `client.paginate` with `params=`).

- **`notion/commands/search.py`:** Implemented `search` command with `--type`, `--sort`, `--limit`, `--page-all`, `--output` options. Registered as a standalone command (not a group) in `cli.py`.

- **`notion/commands/user.py`:** Implemented `list`, `get`, `me`. `list` paginates GET `/users`, `get` fetches `/users/{uid}`, `me` fetches `/users/me`.

- **`db create`:** Replaced stub in `db.py`. Accepts `parent_id`, `title`, optional `--data` (JSON for extra properties), `--output json|id`. Always adds `Name: {title: {}}` as the default title property.

- **`db delete`:** Replaced stub. Archives the database via PATCH `{"archived": True}`. Respects `--confirm` flag; in interactive mode prompts for confirmation.

- **Test files:** Replaced placeholder test files for `test_block.py`, `test_comment.py`, `test_search.py`, `test_user.py` with full test suites. Used valid 32-char hex IDs throughout to avoid `_normalise_id` pass-through issues.

- **All 129 tests pass.**

## M9 Notes

- **Cache isolation fix:** Added `isolate_schema_cache` autouse fixture to `tests/conftest.py` that monkeypatches `notion.schema.CACHE_DIR` to a per-test `tmp_path / "schemas"` directory. This prevents stale schemas from `~/.cache/notion-agent/schemas/` contaminating subsequent tests (was causing `test_add_multi_select_comma_separated` to exit 3).

- **`notion db batch-add` implementation:** Replaced the `NotImplementedError` stub in `notion/commands/db.py` with the full implementation:
  - Accepts `--data` as inline JSON array, `@file`, or `-` (stdin)
  - Fetches schema once, validates all rows before any writes
  - `--dry-run` flag: validates only, exits 7 (no writes)
  - `--continue-on-error` flag: skips failed rows and continues
  - Rate limiting: `time.sleep(0.34)` between requests (3 req/sec)
  - Added `import time` at the top of `db.py`

- **`tests/test_batch.py`:** Full test suite with 6 tests covering inline JSON, file input, dry-run, dry-run with validation errors, continue-on-error, and rate limiting. Uses `result.stdout` (not `result.output`) to avoid Click 8.2+ stderr-mixing in the test runner.
