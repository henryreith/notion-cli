import { homedir } from 'os'
import { join } from 'path'
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs'

const CONFIG_DIR = join(homedir(), '.config', 'notion-agent')
const CONFIG_FILE = join(CONFIG_DIR, 'config.json')

interface Config {
  token?: string
}

function readConfig(): Config {
  if (!existsSync(CONFIG_FILE)) return {}
  try {
    return JSON.parse(readFileSync(CONFIG_FILE, 'utf-8')) as Config
  } catch {
    return {}
  }
}

function writeConfig(config: Config): void {
  mkdirSync(CONFIG_DIR, { recursive: true })
  writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), 'utf-8')
}

export function getToken(): string | undefined {
  return process.env['NOTION_API_KEY'] ?? readConfig().token
}

export function setToken(token: string): void {
  const config = readConfig()
  config.token = token
  writeConfig(config)
}

export function getConfigPath(): string {
  return CONFIG_FILE
}
