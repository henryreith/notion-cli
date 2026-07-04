#!/usr/bin/env node
import { Command } from 'commander'
import { die, ExitCode, handleApiError } from './errors.js'
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
  .version('0.2.2')
  .option('--mode <mode>', 'Operating mode: auto|interactive|ci')
  .option('--profile <name>', 'Use a named profile (overrides NOTION_PROFILE env)')

// Propagate global flags to env before subcommands run
program.hook('preAction', (thisCommand) => {
  const opts = thisCommand.opts()
  if (opts.mode && !['auto', 'interactive', 'ci'].includes(opts.mode)) {
    die(ExitCode.VALIDATION, `Invalid --mode: ${opts.mode}. Expected auto, interactive, or ci.`)
  }
  if (opts.mode) {
    process.env['NOTION_MODE'] = opts.mode
  }
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
  // Maps ValidationError → 3, 401/403 → 1, 404 → 2, 429 + everything else → 4
  handleApiError(err)
})
