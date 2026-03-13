import { Client, collectPaginatedAPI, iteratePaginatedAPI } from '@notionhq/client'
import { getToken } from './config.js'
import { die, ExitCode } from './errors.js'

export { collectPaginatedAPI, iteratePaginatedAPI }

export function normaliseId(input: string): string {
  // Extract ID from Notion URL
  const urlMatch = input.match(/notion\.so\/(?:[^/]+\/)?([a-f0-9]{32})/)
  if (urlMatch) return urlMatch[1]!
  const urlMatchHyphen = input.match(/notion\.so\/(?:[^/]+\/)?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/)
  if (urlMatchHyphen) return urlMatchHyphen[1]!.replace(/-/g, '')
  // Strip hyphens from UUID format
  return input.replace(/-/g, '')
}

export function createNotionClient(): Client {
  const token = getToken()
  if (!token) {
    die(ExitCode.AUTH, 'No Notion API token found. Run: notion auth setup')
  }
  return new Client({ auth: token })
}
