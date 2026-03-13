import { Command } from 'commander'
import { createInterface } from 'readline'
import { getToken, setToken, getConfigPath } from '../config.js'
import { createNotionClient } from '../client.js'
import { die, ExitCode } from '../errors.js'
import { printJSON } from '../output.js'

export function registerAuth(program: Command): void {
  const auth = program.command('auth').description('Manage Notion API authentication')

  auth
    .command('setup')
    .description('Interactive setup wizard for first-time configuration')
    .action(async () => {
      console.log('\nWelcome to notion-agent-cli!\n')
      console.log('To connect to Notion, you need an integration token.\n')
      console.log('Step 1: Create a Notion integration')
      console.log('  Opening https://www.notion.so/my-integrations in your browser...')
      console.log('  (Press Enter if it doesn\'t open automatically)\n')

      try {
        const { default: open } = await import('open')
        await open('https://www.notion.so/my-integrations')
      } catch {
        // non-TTY or browser unavailable
      }

      console.log('Step 2: Click "+ New integration", give it a name, select a workspace.\n')
      console.log('Step 3: Copy the "Internal Integration Secret" (starts with secret_...)\n')
      console.log('Step 4: Paste your integration token here:')

      const rl = createInterface({ input: process.stdin, output: process.stdout })
      const token = await new Promise<string>(resolve => {
        rl.question('> ', answer => {
          rl.close()
          resolve(answer.trim())
        })
      })

      if (!token) {
        die(ExitCode.VALIDATION, 'No token provided')
      }

      console.log('\nStep 5: Connect pages/databases to your integration')
      console.log('  In Notion, open any page → "..." menu → "Connect to" → select your integration.\n')
      console.log('Testing connection...')

      process.env['NOTION_API_KEY'] = token
      const client = createNotionClient()
      try {
        const me = await client.users.me({}) as any
        const workspace = me.bot?.workspace_name ?? 'unknown workspace'
        console.log(`✓ Connected as: ${me.name ?? me.id} (workspace: ${workspace})`)
      } catch {
        die(ExitCode.AUTH, 'Token verification failed. Check the token and try again.')
      }

      setToken(token)
      console.log(`\nToken saved to ${getConfigPath()}`)
      console.log('Run `notion auth status` to check at any time.')
    })

  auth
    .command('set-token <token>')
    .description('Store an integration token directly')
    .action((token: string) => {
      setToken(token)
      console.log(`Token saved to ${getConfigPath()}`)
    })

  auth
    .command('test')
    .description('Verify the current token works')
    .action(async () => {
      const client = createNotionClient()
      try {
        const me = await client.users.me({}) as any
        const workspace = me.bot?.workspace_name ?? 'unknown'
        console.log(`✓ Connected as: ${me.name ?? me.id} (workspace: ${workspace})`)
      } catch (err: any) {
        die(ExitCode.AUTH, 'Authentication failed', { details: err?.message })
      }
    })

  auth
    .command('status')
    .description('Show token prefix and workspace info')
    .option('--output <format>', 'Output format: json or text', 'text')
    .action(async (opts: { output: string }) => {
      const token = getToken()
      if (!token) {
        die(ExitCode.AUTH, 'No token configured. Run: notion auth setup')
      }

      const prefix = token.slice(0, 12) + '...'
      const source = process.env['NOTION_API_KEY'] ? 'env:NOTION_API_KEY' : `file:${getConfigPath()}`

      try {
        const client = createNotionClient()
        const me = await client.users.me({}) as any
        const workspace = me.bot?.workspace_name ?? 'unknown'
        if (opts.output === 'json') {
          printJSON({ token_prefix: prefix, source, user: me.name ?? me.id, workspace })
        } else {
          console.log(`Token: ${prefix} (${source})`)
          console.log(`User: ${me.name ?? me.id}`)
          console.log(`Workspace: ${workspace}`)
        }
      } catch {
        if (opts.output === 'json') {
          printJSON({ token_prefix: prefix, source, error: 'token_invalid' })
        } else {
          console.log(`Token: ${prefix} (${source}) — INVALID`)
        }
        process.exit(ExitCode.AUTH)
      }
    })
}
