import { homedir } from 'os'
import { join } from 'path'
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs'

const CONFIG_DIR = join(homedir(), '.config', 'notion-agent')
const CONFIG_FILE = join(CONFIG_DIR, 'config.json')

export interface Profile {
  token: string
  workspace?: string
  user?: string
  added_at: string
}

interface ConfigV2 {
  version: 2
  default_profile: string
  profiles: Record<string, Profile>
}

// Legacy v1 format
interface ConfigV1 {
  token?: string
}

function readRawConfig(): ConfigV2 | ConfigV1 {
  if (!existsSync(CONFIG_FILE)) return {}
  try {
    return JSON.parse(readFileSync(CONFIG_FILE, 'utf-8'))
  } catch {
    return {}
  }
}

function migrateToV2(raw: ConfigV1): ConfigV2 {
  const config: ConfigV2 = {
    version: 2,
    default_profile: 'default',
    profiles: {},
  }
  if (raw.token) {
    config.profiles['default'] = {
      token: raw.token,
      added_at: new Date().toISOString(),
    }
  }
  return config
}

function readConfig(): ConfigV2 {
  const raw = readRawConfig()
  if ((raw as ConfigV2).version === 2) return raw as ConfigV2
  return migrateToV2(raw as ConfigV1)
}

function writeConfig(config: ConfigV2): void {
  mkdirSync(CONFIG_DIR, { recursive: true })
  writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), 'utf-8')
}

export function getToken(profileName?: string): string | undefined {
  // Priority 1: NOTION_API_KEY env always wins
  if (process.env['NOTION_API_KEY']) return process.env['NOTION_API_KEY']

  // Priority 2: resolve named profile (arg > NOTION_PROFILE env > default_profile)
  const config = readConfig()
  const name = profileName ?? process.env['NOTION_PROFILE'] ?? config.default_profile
  return config.profiles[name]?.token
}

export function setToken(token: string): void {
  const config = readConfig()
  const name = config.default_profile || 'default'
  if (!config.profiles[name]) {
    config.profiles[name] = { token, added_at: new Date().toISOString() }
  } else {
    config.profiles[name]!.token = token
  }
  config.default_profile = name
  writeConfig(config)
}

export function getConfigPath(): string {
  return CONFIG_FILE
}

export function listProfiles(): Array<{ name: string; isDefault: boolean; profile: Profile }> {
  const config = readConfig()
  return Object.entries(config.profiles).map(([name, profile]) => ({
    name,
    isDefault: name === config.default_profile,
    profile,
  }))
}

export function addProfile(name: string, profile: Profile): void {
  const config = readConfig()
  config.profiles[name] = profile
  // First profile becomes default automatically
  if (Object.keys(config.profiles).length === 1) {
    config.default_profile = name
  }
  writeConfig(config)
}

export function removeProfile(name: string): void {
  const config = readConfig()
  if (!config.profiles[name]) throw new Error(`Profile not found: ${name}`)
  delete config.profiles[name]
  if (config.default_profile === name) {
    config.default_profile = Object.keys(config.profiles)[0] ?? ''
  }
  writeConfig(config)
}

export function renameProfile(oldName: string, newName: string): void {
  const config = readConfig()
  if (!config.profiles[oldName]) throw new Error(`Profile not found: ${oldName}`)
  if (config.profiles[newName]) throw new Error(`Profile already exists: ${newName}`)
  config.profiles[newName] = config.profiles[oldName]!
  delete config.profiles[oldName]
  if (config.default_profile === oldName) config.default_profile = newName
  writeConfig(config)
}

export function setDefaultProfile(name: string): void {
  const config = readConfig()
  if (!config.profiles[name]) throw new Error(`Profile not found: ${name}`)
  config.default_profile = name
  writeConfig(config)
}

export function updateProfile(name: string, updates: Partial<Profile>): void {
  const config = readConfig()
  if (!config.profiles[name]) throw new Error(`Profile not found: ${name}`)
  config.profiles[name] = { ...config.profiles[name]!, ...updates }
  writeConfig(config)
}

export function getActiveProfileName(): string | undefined {
  if (process.env['NOTION_API_KEY']) return undefined
  const config = readConfig()
  return process.env['NOTION_PROFILE'] ?? config.default_profile
}
