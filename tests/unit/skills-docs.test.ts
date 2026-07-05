import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'fs'
import { join, relative } from 'path'
import { parse as parseYaml } from 'yaml'
import { Command } from 'commander'
import { registerAuth } from '../../src/commands/auth.js'
import { registerDb } from '../../src/commands/db.js'
import { registerPage } from '../../src/commands/page.js'
import { registerBlock } from '../../src/commands/block.js'
import { registerComment } from '../../src/commands/comment.js'
import { registerSearch } from '../../src/commands/search.js'
import { registerUser } from '../../src/commands/user.js'

// Docs-drift guard: every `notion ...` invocation in a bash code block across
// the skills and command docs must reference a real subcommand and real flags.
// This test exists because five documented-but-wrong behaviors shipped before it.

const ROOT = join(__dirname, '..', '..')

// --- Ground truth: build the same program cli.ts builds -------------------

function buildProgram(): Command {
  const program = new Command()
  program
    .name('notion')
    .option('--mode <mode>')
    .option('--profile <name>')
  registerAuth(program)
  registerDb(program)
  registerPage(program)
  registerBlock(program)
  registerComment(program)
  registerSearch(program)
  registerUser(program)
  return program
}

interface CommandInfo {
  path: string
  flags: Set<string>
}

function collectCommands(cmd: Command, prefix: string[], globalFlags: Set<string>, out: Map<string, CommandInfo>): void {
  for (const sub of cmd.commands) {
    const path = [...prefix, sub.name()]
    const flags = new Set<string>(globalFlags)
    for (const opt of sub.options) {
      if (opt.long) flags.add(opt.long)
      if (opt.short) flags.add(opt.short)
      // Commander's --no-<x> options also accept the negated long form only;
      // the positive form is the attribute — register what's typed in docs.
    }
    out.set(path.join(' '), { path: path.join(' '), flags })
    collectCommands(sub, path, globalFlags, out)
  }
}

function groundTruth(): Map<string, CommandInfo> {
  const program = buildProgram()
  const globalFlags = new Set<string>(['--mode', '--profile', '--help', '-h', '--version', '-V'])
  const out = new Map<string, CommandInfo>()
  collectCommands(program, [], globalFlags, out)
  return out
}

// --- Extraction: pull `notion ...` invocations from markdown --------------

function mdFiles(dir: string): string[] {
  const results: string[] = []
  for (const entry of readdirSync(dir)) {
    const fp = join(dir, entry)
    if (statSync(fp).isDirectory()) results.push(...mdFiles(fp))
    else if (entry.endsWith('.md')) results.push(fp)
  }
  return results
}

interface Invocation {
  file: string
  line: number
  text: string
}

// Only fenced blocks in shell-ish languages — json/python/typescript blocks
// mention "notion" in ways that aren't CLI invocations.
const SHELL_FENCES = new Set(['bash', 'sh', 'shell', 'zsh', ''])

function extractInvocations(file: string): Invocation[] {
  const lines = readFileSync(file, 'utf-8').split('\n')
  const out: Invocation[] = []
  let inFence = false
  let fenceLang = ''
  let pending: { text: string; line: number } | null = null

  const flush = () => {
    if (!pending) return
    // A joined line may contain a pipeline of several notion commands —
    // validate each segment separately.
    for (const segment of pending.text.split('|')) {
      const m = segment.match(/notion\s+(.*)$/)
      if (m) out.push({ file, line: pending.line, text: 'notion ' + m[1]!.trim() })
    }
    pending = null
  }

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i]!
    const fence = raw.match(/^```(\w*)/)
    if (fence) {
      flush()
      inFence = !inFence
      fenceLang = inFence ? fence[1]!.toLowerCase() : ''
      continue
    }
    if (!inFence || !SHELL_FENCES.has(fenceLang)) continue

    const line = raw.trim()
    if (pending) {
      // continuation of a backslash-wrapped command
      pending.text += ' ' + line.replace(/\\$/, '').trim()
      if (!line.endsWith('\\')) flush()
      continue
    }

    // find `notion <args>` at start of line, after $( or after a pipe
    const m = line.match(/(?:^|\$\(|\|\s*(?:xargs\s+-I\{\}\s+)?)notion\s+(.*)$/)
    if (!m) continue
    if (line.startsWith('#')) continue
    pending = { text: 'notion ' + m[1]!, line: i + 1 }
    if (!line.endsWith('\\')) flush()
  }
  flush()
  return out
}

function tokenize(invocation: string): string[] {
  // strip $(...) command substitutions' closing parens, quotes kept simple:
  // we only need command words and --flags, not argument values.
  return invocation
    .replace(/\)+\s*$/, '')
    .split(/\s+/)
    .filter(Boolean)
}

// --- The test --------------------------------------------------------------

const FILES = [
  ...mdFiles(join(ROOT, 'skills')),
  join(ROOT, 'docs', 'commands.md'),
  join(ROOT, 'docs', 'agent-patterns.md'),
]

// --- Agent Skills spec compliance (agentskills.io/specification) -----------

describe('skills comply with the Agent Skills spec', () => {
  const skillDirs = readdirSync(join(ROOT, 'skills')).filter(d =>
    statSync(join(ROOT, 'skills', d)).isDirectory()
  )

  it('found the skill directories', () => {
    expect(skillDirs.length).toBeGreaterThanOrEqual(8)
  })

  for (const dir of skillDirs) {
    it(`${dir}: SKILL.md meets the spec`, () => {
      const content = readFileSync(join(ROOT, 'skills', dir, 'SKILL.md'), 'utf-8')
      const lines = content.split('\n')

      // frontmatter block present and VALID YAML (regex alone missed real
      // parse failures from unquoted colons — skills-ref caught them)
      expect(lines[0], 'must start with frontmatter').toBe('---')
      const end = lines.indexOf('---', 1)
      expect(end, 'frontmatter must close').toBeGreaterThan(0)
      const fm = parseYaml(lines.slice(1, end).join('\n')) as Record<string, unknown>

      // name: 1-64 chars, lowercase/digits/hyphens, no leading/trailing/double hyphen,
      // and must match the parent directory name
      const name = fm['name'] as string | undefined
      expect(name, 'name is required').toBeTruthy()
      expect(name).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*$/)
      expect(name!.length).toBeLessThanOrEqual(64)
      expect(name, 'name must match directory').toBe(dir)

      // description: required, 1-1024 chars
      const description = fm['description'] as string | undefined
      expect(description, 'description is required').toBeTruthy()
      expect(description!.length).toBeGreaterThanOrEqual(1)
      expect(description!.length).toBeLessThanOrEqual(1024)

      // compatibility: optional, max 500 chars
      const compatibility = fm['compatibility'] as string | undefined
      if (compatibility) expect(compatibility.length).toBeLessThanOrEqual(500)

      // metadata: optional string map per spec
      if (fm['metadata']) expect(typeof fm['metadata']).toBe('object')

      // body: keep under the spec's recommended 500 lines
      expect(lines.length, 'SKILL.md should stay under 500 lines').toBeLessThan(500)
    })
  }
})

describe('skills and docs match the actual CLI', () => {
  const truth = groundTruth()

  it('collected ground truth from commander', () => {
    expect(truth.has('db query')).toBe(true)
    expect(truth.get('db query')!.flags.has('--filter')).toBe(true)
  })

  for (const file of FILES) {
    const rel = relative(ROOT, file)
    const invocations = extractInvocations(file)

    it(`${rel}: documented commands and flags exist`, () => {
      const problems: string[] = []

      for (const inv of invocations) {
        const tokens = tokenize(inv.text)
        // tokens[0] === 'notion'; find the deepest matching subcommand path
        let matched: CommandInfo | undefined
        let depth = 0
        for (let take = Math.min(3, tokens.length - 1); take >= 1; take--) {
          const words = tokens.slice(1, 1 + take)
          // stop at first non-word (placeholder, flag, value)
          if (!words.every(w => /^[a-z-]+$/.test(w))) continue
          const key = words.join(' ')
          if (truth.has(key)) {
            matched = truth.get(key)!
            depth = take
            break
          }
        }
        if (!matched) {
          problems.push(`${rel}:${inv.line} unknown command: ${inv.text}`)
          continue
        }
        for (const token of tokens.slice(1 + depth)) {
          const flag = token.match(/^(--[a-z][a-z-]*)/)?.[1]
          if (flag && !matched.flags.has(flag)) {
            problems.push(`${rel}:${inv.line} unknown flag ${flag} for "${matched.path}": ${inv.text}`)
          }
        }
      }

      expect(problems, problems.join('\n')).toEqual([])
    })
  }
})
