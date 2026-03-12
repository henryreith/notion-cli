# Design Decisions

## HTTP Client: httpx over requests
httpx is async-compatible for future upgrades and has better timeout/retry ergonomics.

## Output: Rich over tabulate
Rich is already needed for progress bars in batch-add; no extra dependency.

## Schema cache: disk-based JSON, 15-min TTL
Avoids redundant API calls in rapid command sequences while staying fresh.

## Click over argparse
Composable command groups, automatic help generation, type coercion built in.

## Sync-only in v0.1
Subprocess callers expect synchronous behavior. Async adds complexity with no benefit for v0.1.
