import { describe, it, expect, afterEach } from 'vitest'
import {
  getToken,
  listProfiles,
  addProfile,
  removeProfile,
  renameProfile,
  setDefaultProfile,
  updateProfile,
  getActiveProfileName,
  getConfigPath,
} from '../../src/config.js'

describe('config exports', () => {
  it('exports all required functions', () => {
    expect(typeof getToken).toBe('function')
    expect(typeof listProfiles).toBe('function')
    expect(typeof addProfile).toBe('function')
    expect(typeof removeProfile).toBe('function')
    expect(typeof renameProfile).toBe('function')
    expect(typeof setDefaultProfile).toBe('function')
    expect(typeof updateProfile).toBe('function')
    expect(typeof getActiveProfileName).toBe('function')
    expect(typeof getConfigPath).toBe('function')
  })

  it('getConfigPath returns a config.json path', () => {
    const path = getConfigPath()
    expect(path).toContain('config.json')
    expect(path).toContain('notion-agent')
  })

  it('listProfiles returns an array', () => {
    expect(Array.isArray(listProfiles())).toBe(true)
  })
})

describe('token resolution priority', () => {
  const savedApiKey = process.env['NOTION_API_KEY']
  const savedProfile = process.env['NOTION_PROFILE']

  afterEach(() => {
    if (savedApiKey === undefined) delete process.env['NOTION_API_KEY']
    else process.env['NOTION_API_KEY'] = savedApiKey
    if (savedProfile === undefined) delete process.env['NOTION_PROFILE']
    else process.env['NOTION_PROFILE'] = savedProfile
  })

  it('NOTION_API_KEY env always wins', () => {
    process.env['NOTION_API_KEY'] = 'secret_env_priority'
    expect(getToken()).toBe('secret_env_priority')
  })

  it('getToken does not throw when nothing is configured', () => {
    delete process.env['NOTION_API_KEY']
    delete process.env['NOTION_PROFILE']
    expect(() => getToken()).not.toThrow()
  })

  it('getActiveProfileName returns undefined when NOTION_API_KEY is set', () => {
    process.env['NOTION_API_KEY'] = 'secret_test'
    expect(getActiveProfileName()).toBeUndefined()
  })
})

describe('removeProfile error handling', () => {
  it('throws when removing non-existent profile', () => {
    expect(() => removeProfile('__nonexistent_profile_xyz__')).toThrow('Profile not found')
  })
})

describe('renameProfile error handling', () => {
  it('throws when renaming non-existent profile', () => {
    expect(() => renameProfile('__nonexistent_xyz__', 'anything')).toThrow('Profile not found')
  })
})

describe('setDefaultProfile error handling', () => {
  it('throws when setting default to non-existent profile', () => {
    expect(() => setDefaultProfile('__nonexistent_xyz__')).toThrow('Profile not found')
  })
})

describe('updateProfile error handling', () => {
  it('throws when updating non-existent profile', () => {
    expect(() => updateProfile('__nonexistent_xyz__', { workspace: 'x' })).toThrow('Profile not found')
  })
})
