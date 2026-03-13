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

registerAuth(program)
registerDb(program)
registerPage(program)
registerBlock(program)
registerComment(program)
registerSearch(program)
registerUser(program)

program.parseAsync(process.argv).catch((err: Error) => {
  process.stderr.write(JSON.stringify({ error: err.message }) + '\n')
  process.exit(4)
})
