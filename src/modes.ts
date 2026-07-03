import { createInterface } from 'readline'
import { die, ExitCode } from './errors.js'

export type Mode = 'auto' | 'interactive' | 'ci'

export function getMode(flagMode?: string): Mode {
  const m = flagMode ?? process.env['NOTION_MODE']
  if (m === 'auto' || m === 'interactive' || m === 'ci') return m
  return process.stdout.isTTY ? 'interactive' : 'auto'
}

function promptYesNo(message: string): Promise<boolean> {
  return new Promise(resolve => {
    const rl = createInterface({ input: process.stdin, output: process.stdout })
    rl.question(`${message} [y/N] `, answer => {
      rl.close()
      resolve(answer.toLowerCase() === 'y' || answer.toLowerCase() === 'yes')
    })
  })
}

// Gate for destructive commands. Interactive mode prompts y/N; non-interactive
// (auto/ci) refuses unless --confirm was passed or NOTION_AUTO_CONFIRM=1 is set,
// so a script or agent can never delete by accident but never hangs either.
export async function confirmDestructive(message: string, confirmed: boolean): Promise<boolean> {
  if (confirmed) return true
  if (process.env['NOTION_AUTO_CONFIRM'] === '1') return true
  if (getMode() === 'interactive') {
    return promptYesNo(message)
  }
  die(ExitCode.VALIDATION, `Refusing without confirmation in non-interactive mode: ${message}`, {
    hint: 'Re-run with --confirm, or set NOTION_AUTO_CONFIRM=1 for trusted pipelines.',
  })
}
