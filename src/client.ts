import { Client, collectPaginatedAPI, iteratePaginatedAPI } from '@notionhq/client'
import { getToken } from './config.js'
import { die, ExitCode, ValidationError } from './errors.js'

export { collectPaginatedAPI, iteratePaginatedAPI }

export function normaliseId(input: string): string {
  const candidate = input.trim()

  // Notion URLs end with the ID (optionally prefixed by the page slug, e.g.
  // notion.so/My-Page-Title-<32hex>). Strip query/fragment, take the trailing ID.
  if (/^https?:\/\//i.test(candidate) || candidate.includes('notion.so') || candidate.includes('notion.site')) {
    const path = candidate.split(/[?#]/)[0]!
    const hyphenated = path.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\/?$/i)
    if (hyphenated) return hyphenated[1]!.replace(/-/g, '').toLowerCase()
    const plain = path.match(/([0-9a-f]{32})\/?$/i)
    if (plain) return plain[1]!.toLowerCase()
    throw new ValidationError(`Could not extract a Notion ID from URL: "${input}"`)
  }

  // Bare ID: 32-char hex, with or without UUID hyphens
  const stripped = candidate.replace(/-/g, '')
  if (!/^[0-9a-f]{32}$/i.test(stripped)) {
    throw new ValidationError(`Not a valid Notion ID or URL: "${input}" (expected a 32-char hex ID, UUID, or notion.so URL)`)
  }
  return stripped.toLowerCase()
}

export function createNotionClient(): Client {
  const token = getToken()
  if (!token) {
    die(ExitCode.AUTH, 'No Notion API token found. Run: notion auth setup')
  }
  return new Client({ auth: token })
}
