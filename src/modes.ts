import { createInterface } from 'readline'

export type Mode = 'auto' | 'interactive' | 'ci'

export function getMode(flagMode?: string): Mode {
  const m = flagMode ?? process.env['NOTION_MODE']
  if (m === 'auto' || m === 'interactive' || m === 'ci') return m
  return process.stdout.isTTY ? 'interactive' : 'auto'
}

export async function confirm(message: string, mode?: Mode): Promise<boolean> {
  const resolvedMode = mode ?? getMode()
  if (resolvedMode === 'auto' || resolvedMode === 'ci') return true
  return new Promise(resolve => {
    const rl = createInterface({ input: process.stdin, output: process.stdout })
    rl.question(`${message} [y/N] `, answer => {
      rl.close()
      resolve(answer.toLowerCase() === 'y' || answer.toLowerCase() === 'yes')
    })
  })
}
