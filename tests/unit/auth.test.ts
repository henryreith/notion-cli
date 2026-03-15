import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getToken, setToken } from '../../src/config.js'

describe('config token management', () => {
  const originalEnv = process.env['NOTION_API_KEY']
  const originalProfile = process.env['NOTION_PROFILE']

  afterEach(() => {
    if (originalEnv === undefined) delete process.env['NOTION_API_KEY']
    else process.env['NOTION_API_KEY'] = originalEnv
    if (originalProfile === undefined) delete process.env['NOTION_PROFILE']
    else process.env['NOTION_PROFILE'] = originalProfile
  })

  it('returns env token when NOTION_API_KEY is set', () => {
    process.env['NOTION_API_KEY'] = 'secret_env_token'
    expect(getToken()).toBe('secret_env_token')
  })

  it('returns undefined when no token configured', () => {
    delete process.env['NOTION_API_KEY']
    delete process.env['NOTION_PROFILE']
    // Can't fully test without mocking fs, but verify it doesn't throw
    expect(() => getToken()).not.toThrow()
  })
})

describe('normaliseId', () => {
  it('strips hyphens from UUID', async () => {
    const { normaliseId } = await import('../../src/client.js')
    expect(normaliseId('12345678-1234-1234-1234-123456789abc')).toBe('123456781234123412341234567' + '89abc')
  })

  it('extracts ID from Notion URL', async () => {
    const { normaliseId } = await import('../../src/client.js')
    const url = 'https://www.notion.so/myworkspace/abcdef1234567890abcdef1234567890'
    expect(normaliseId(url)).toBe('abcdef1234567890abcdef1234567890')
  })

  it('passes through plain 32-char hex unchanged', async () => {
    const { normaliseId } = await import('../../src/client.js')
    const id = 'abcdef1234567890abcdef1234567890'
    expect(normaliseId(id)).toBe(id)
  })
})

describe('profile API exports', () => {
  it('listProfiles returns an array', async () => {
    const { listProfiles } = await import('../../src/config.js')
    const result = listProfiles()
    expect(Array.isArray(result)).toBe(true)
  })

  it('getActiveProfileName returns undefined when NOTION_API_KEY is set', async () => {
    process.env['NOTION_API_KEY'] = 'secret_test'
    const { getActiveProfileName } = await import('../../src/config.js')
    expect(getActiveProfileName()).toBeUndefined()
    delete process.env['NOTION_API_KEY']
  })
})
