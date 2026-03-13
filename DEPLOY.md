# Publishing to npm

## First Publish

```bash
# 1. Login to npm (create account at https://www.npmjs.com if needed)
npm login

# 2. Verify the package looks correct
npm pack --dry-run    # shows all files that will be included

# 3. Publish
npm publish --access public

# 4. Verify
npm info notion-agent-cli
```

## Subsequent Releases

```bash
npm version patch   # 0.1.0 → 0.1.1
# or
npm version minor   # 0.1.0 → 0.2.0
# or
npm version major   # 0.1.0 → 1.0.0

git push && git push --tags
```

`npm version` automatically:
- Bumps the version in `package.json`
- Creates a git commit (`v0.x.x`)
- Creates a git tag (`v0.x.x`)

## Automated Publishing (GitHub Actions)

The workflow at `.github/workflows/publish.yml` triggers on `v*` tags:

```bash
git tag v0.2.0
git push origin v0.2.0
# → CI runs tests, then publishes to npm
```

### Required Setup

Add an `NPM_TOKEN` secret to the GitHub repo:
1. Generate token at [https://www.npmjs.com/settings/tokens](https://www.npmjs.com/settings/tokens) (Automation type)
2. Go to repo **Settings → Secrets and variables → Actions**
3. Add secret named `NPM_TOKEN`

## What Gets Published

`package.json` controls what's included via the `files` field. Run `npm pack --dry-run` to
verify the contents before publishing. The `dist/` build output must exist — run
`npm run build` first if needed.

## Version Numbering

Follow [semver](https://semver.org/):
- **patch** (`0.1.x`) — bug fixes, no API changes
- **minor** (`0.x.0`) — new commands or flags, backwards compatible
- **major** (`x.0.0`) — breaking changes (removed commands, changed output format)
