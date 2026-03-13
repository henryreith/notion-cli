# Contributing

## Dev Setup

```bash
git clone https://github.com/henryreith/notion-cli
cd notion-cli
npm install
npm run build
npm test
./dist/cli.js --version   # → 0.1.0
```

## Project Structure

```
src/
  cli.ts            # Commander root — registers all subcommands
  client.ts         # createNotionClient(), normaliseId()
  errors.ts         # ExitCode enum (0–7), die()
  output.ts         # printJSON / printTable / printIds / printId
  coerce.ts         # buildFilter(), coerceProperties(), parseKV(), markdownToBlocks()
  schema.ts         # SchemaCache (15-min TTL) + PropertyResolver
  modes.ts          # getMode(), confirm()
  config.ts         # readToken(), writeToken()
  commands/
    auth.ts         # auth setup, set-token, test, status
    db.ts           # all db subcommands
    page.ts         # all page subcommands
    block.ts        # all block subcommands
    comment.ts      # comment add, list
    search.ts       # search
    user.ts         # user list, get, me
tests/
  unit/             # vitest unit tests (no network)
  integration/      # live API tests (skipped unless NOTION_TEST_DB_ID is set)
  fixtures/         # JSON test data
```

## Running Tests

```bash
npm test                  # all unit tests
npm run test:watch        # watch mode
npm run build             # TypeScript → dist/
```

### Integration Tests

Integration tests require a live Notion workspace. Set these env vars to run them:

```bash
export NOTION_API_KEY=secret_xxxx...
export NOTION_TEST_DB_ID=<database-id>   # a test database in your workspace
npm test
```

Integration tests are skipped automatically when `NOTION_TEST_DB_ID` is not set.

## Making Changes

1. Edit source in `src/`
2. Run `npm run build` to compile
3. Test manually: `./dist/cli.js <command>`
4. Run `npm test` to verify unit tests pass
5. Open a PR

## SDK Notes

This project uses `@notionhq/client` v5.x. Key v5 differences from v4:

- `databases.query` is **removed** — use `dataSources.query({ data_source_id })`
- Schema/properties are on `dataSources`, not `databases`
- `pages.move(pageId, parentId)` is available directly
- See `src/commands/db.ts` for usage examples

## Exit Codes

All commands exit with a consistent code:

| Code | Constant | When |
|------|----------|------|
| 0 | SUCCESS | OK |
| 1 | AUTH | Token missing or invalid |
| 2 | NOT_FOUND | Resource doesn't exist |
| 3 | VALIDATION | Bad input (unknown property, bad filter) |
| 4 | API | Notion API error |
| 5 | EXISTS | Duplicate create |
| 6 | AMBIGUOUS | Upsert matched >1 row |
| 7 | DRY_RUN | `--dry-run` completed without writing |
