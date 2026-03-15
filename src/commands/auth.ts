import { Command } from 'commander'
import { createInterface } from 'readline'
import {
  getToken,
  setToken,
  getConfigPath,
  listProfiles,
  addProfile,
  removeProfile,
  renameProfile,
  setDefaultProfile,
  updateProfile,
  getActiveProfileName,
} from '../config.js'
import { createNotionClient } from '../client.js'
import { die, ExitCode } from '../errors.js'
import { printJSON } from '../output.js'

async function promptToken(): Promise<string> {
  const rl = createInterface({ input: process.stdin, output: process.stdout })
  return new Promise<string>(resolve => {
    rl.question('Paste your integration token (secret_...): ', answer => {
      rl.close()
      resolve(answer.trim())
    })
  })
}

async function verifyToken(token: string): Promise<{ name: string; workspace: string }> {
  process.env['NOTION_API_KEY'] = token
  const client = createNotionClient()
  const me = await client.users.me({}) as any
  const workspace = me.bot?.workspace_name ?? 'unknown'
  return { name: me.name ?? me.id, workspace }
}

export function registerAuth(program: Command): void {
  const auth = program.command('auth').description('Manage Notion API authentication')

  auth
    .command('setup')
    .description('Interactive setup wizard for first-time configuration')
    .option('--name <profile>', 'Profile name to create (default: "default")')
    .action(async (opts: { name?: string }) => {
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

      const token = await promptToken()
      if (!token) die(ExitCode.VALIDATION, 'No token provided')

      console.log('\nStep 5: Connect pages/databases to your integration')
      console.log('  In Notion, open any page → "..." menu → "Connect to" → select your integration.\n')
      console.log('Testing connection...')

      let me: { name: string; workspace: string }
      try {
        me = await verifyToken(token)
        console.log(`✓ Connected as: ${me.name} (workspace: ${me.workspace})`)
      } catch {
        die(ExitCode.AUTH, 'Token verification failed. Check the token and try again.')
      }

      const profileName = opts.name ?? 'default'
      addProfile(profileName, {
        token,
        workspace: me!.workspace,
        user: me!.name,
        added_at: new Date().toISOString(),
      })
      // Also persist as default for setToken-compatible code paths
      setDefaultProfile(profileName)

      console.log(`\nProfile "${profileName}" saved to ${getConfigPath()}`)
      console.log('Run `notion auth status` to check at any time.')
    })

  auth
    .command('set-token <token>')
    .description('Store an integration token directly (writes to active/default profile)')
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
      const activeProfile = getActiveProfileName()
      const source = process.env['NOTION_API_KEY']
        ? 'env:NOTION_API_KEY'
        : `profile:${activeProfile ?? 'unknown'} (${getConfigPath()})`

      try {
        const client = createNotionClient()
        const me = await client.users.me({}) as any
        const workspace = me.bot?.workspace_name ?? 'unknown'
        if (opts.output === 'json') {
          printJSON({ token_prefix: prefix, source, profile: activeProfile, user: me.name ?? me.id, workspace })
        } else {
          console.log(`Token: ${prefix} (${source})`)
          if (activeProfile) console.log(`Profile: ${activeProfile}`)
          console.log(`User: ${me.name ?? me.id}`)
          console.log(`Workspace: ${workspace}`)
        }
      } catch {
        if (opts.output === 'json') {
          printJSON({ token_prefix: prefix, source, profile: activeProfile, error: 'token_invalid' })
        } else {
          console.log(`Token: ${prefix} (${source}) — INVALID`)
        }
        process.exit(ExitCode.AUTH)
      }
    })

  // auth profile subcommand group
  const profile = auth.command('profile').description('Manage named authentication profiles')

  profile
    .command('list')
    .description('List all profiles (* marks current default)')
    .option('--output <format>', 'Output format: json or text', 'text')
    .action((opts: { output: string }) => {
      const profiles = listProfiles()
      if (opts.output === 'json') {
        printJSON(profiles.map(p => ({
          name: p.name,
          default: p.isDefault,
          workspace: p.profile.workspace,
          user: p.profile.user,
          added_at: p.profile.added_at,
        })))
      } else {
        if (profiles.length === 0) {
          console.log('No profiles configured. Run: notion auth setup')
          return
        }
        for (const p of profiles) {
          const marker = p.isDefault ? '* ' : '  '
          const workspace = p.profile.workspace ? ` (${p.profile.workspace})` : ''
          const user = p.profile.user ? ` — ${p.profile.user}` : ''
          console.log(`${marker}${p.name}${workspace}${user}`)
        }
      }
    })

  profile
    .command('add <name>')
    .description('Add a named profile')
    .option('--token <token>', 'Integration token (prompts if omitted)')
    .action(async (name: string, opts: { token?: string }) => {
      const existing = listProfiles().find(p => p.name === name)
      if (existing) die(ExitCode.EXISTS, `Profile already exists: ${name}`)

      let token = opts.token
      if (!token) {
        token = await promptToken()
      }
      if (!token) die(ExitCode.VALIDATION, 'No token provided')

      console.log('Testing connection...')
      let me: { name: string; workspace: string }
      try {
        me = await verifyToken(token)
        console.log(`✓ Connected as: ${me.name} (workspace: ${me.workspace})`)
      } catch {
        die(ExitCode.AUTH, 'Token verification failed. Check the token and try again.')
      }

      // Restore NOTION_API_KEY after verification (we set it in verifyToken)
      delete process.env['NOTION_API_KEY']

      addProfile(name, {
        token,
        workspace: me!.workspace,
        user: me!.name,
        added_at: new Date().toISOString(),
      })
      console.log(`Profile "${name}" added. Run: notion auth profile use ${name}`)
    })

  profile
    .command('remove <name>')
    .description('Remove a named profile')
    .action((name: string) => {
      try {
        removeProfile(name)
        console.log(`Profile "${name}" removed.`)
      } catch (err: any) {
        die(ExitCode.NOT_FOUND, err.message)
      }
    })

  profile
    .command('rename <old-name> <new-name>')
    .description('Rename a profile')
    .action((oldName: string, newName: string) => {
      try {
        renameProfile(oldName, newName)
        console.log(`Profile "${oldName}" renamed to "${newName}".`)
      } catch (err: any) {
        die(ExitCode.VALIDATION, err.message)
      }
    })

  profile
    .command('use <name>')
    .description('Set a profile as the default')
    .action((name: string) => {
      try {
        setDefaultProfile(name)
        console.log(`Default profile set to "${name}".`)
      } catch (err: any) {
        die(ExitCode.NOT_FOUND, err.message)
      }
    })

  profile
    .command('update <name>')
    .description('Update workspace/user metadata for a profile (re-fetches from API)')
    .action(async (name: string) => {
      const profiles = listProfiles()
      const found = profiles.find(p => p.name === name)
      if (!found) die(ExitCode.NOT_FOUND, `Profile not found: ${name}`)

      process.env['NOTION_API_KEY'] = found.profile.token
      const client = createNotionClient()
      try {
        const me = await client.users.me({}) as any
        const workspace = me.bot?.workspace_name ?? 'unknown'
        delete process.env['NOTION_API_KEY']
        updateProfile(name, { workspace, user: me.name ?? me.id })
        console.log(`Profile "${name}" updated: ${me.name ?? me.id} @ ${workspace}`)
      } catch {
        die(ExitCode.AUTH, `Token for profile "${name}" is invalid`)
      }
    })
}
