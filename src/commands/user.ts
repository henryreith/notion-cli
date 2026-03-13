import { Command } from 'commander'
import { createNotionClient, normaliseId, collectPaginatedAPI } from '../client.js'
import { printJSON, printIds } from '../output.js'

export function registerUser(program: Command): void {
  const user = program.command('user').description('User commands')

  // user list
  user.command('list')
    .description('List all users')
    .option('--output <format>', 'Output format: json|ids', 'json')
    .action(async (opts: { output: string }) => {
      const client = createNotionClient()
      const results = await collectPaginatedAPI(client.users.list, {})

      if (opts.output === 'ids') {
        printIds(results as Array<{ id: string }>)
      } else {
        printJSON(results)
      }
    })

  // user get
  user.command('get <user-id>')
    .description('Retrieve a user')
    .action(async (userId: string) => {
      const client = createNotionClient()
      const result = await client.users.retrieve({ user_id: normaliseId(userId) })
      printJSON(result)
    })

  // user me
  user.command('me')
    .description('Get the bot user for the current token')
    .action(async () => {
      const client = createNotionClient()
      const result = await client.users.me({})
      printJSON(result)
    })
}
