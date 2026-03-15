#!/usr/bin/env node
// Runs as the `version` npm lifecycle hook.
// Reads the new version from package.json and patches src/cli.ts and the
// plugin manifest so they all stay in sync, then stages the changes so they
// are included in the version commit that `npm version` creates.

import { readFileSync, writeFileSync } from 'fs'
import { execSync } from 'child_process'
import { createRequire } from 'module'

const require = createRequire(import.meta.url)
const { version } = require('../package.json')

function patch(file, find, replace) {
  const content = readFileSync(file, 'utf8')
  if (!find.test(content)) {
    process.stderr.write(`sync-version: pattern not found in ${file}\n`)
    process.exit(1)
  }
  writeFileSync(file, content.replace(find, replace))
}

// src/cli.ts — .version('x.y.z')
patch(
  'src/cli.ts',
  /\.version\('[^']+'\)/,
  `.version('${version}')`,
)

// .claude-plugin/plugin.json
patch(
  '.claude-plugin/plugin.json',
  /"version": "[^"]+"/,
  `"version": "${version}"`,
)

// Stage the patched files so npm version includes them in its commit
execSync('git add src/cli.ts .claude-plugin/plugin.json')

process.stdout.write(`sync-version: synced all files to v${version}\n`)
