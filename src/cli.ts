#!/usr/bin/env node
import { Command } from 'commander'
import { registerAuth } from './commands/auth.js'
import { registerDb } from './commands/db.js'
import { registerPage } from './commands/page.js'
import { registerBlock } from './commands/block.js'
import { registerComment } from './commands/comment.js'
import { registerSearch } from './commands/search.js'
import { registerUser } from './commands/user.js'

const program = new Command()

program
  .name('notion')
  .description('Zero-overhead CLI for the Notion API')
  .version('0.1.0')
  .option('--mode <mode>', 'Operating mode: auto|interactive|ci')
  .option('--profile <name>', 'Use a named profile (overrides NOTION_PROFILE env)')

// Propagate --profile to env before subcommands run
program.hook('preAction', (thisCommand) => {
  const opts = thisCommand.opts()
  if (opts.profile) {
    process.env['NOTION_PROFILE'] = opts.profile
  }
})

registerAuth(program)
registerDb(program)
registerPage(program)
registerBlock(program)
registerComment(program)
registerSearch(program)
registerUser(program)

program.parseAsync(process.argv).catch((err: unknown) => {
  const e = err as any
  if (e?.status === 403 || e?.code === 'restricted_resource') {
    process.stderr.write(JSON.stringify({
      error: "Permission denied — this page/database hasn't been shared with your integration.",
      hint: "In Notion: open the page → '...' menu → Connections → [your integration name]",
    }) + '\n')
    process.exit(1)
  }
  process.stderr.write(JSON.stringify({ error: (err as Error).message ?? String(err) }) + '\n')
  process.exit(4)
})
