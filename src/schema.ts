import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync, unlinkSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'
import type { Client } from '@notionhq/client'
import { coerceValue } from './coerce.js'

const CACHE_DIR = join(homedir(), '.cache', 'notion-agent', 'schemas')
const TTL_MS = 15 * 60 * 1000 // 15 minutes

export interface PropertySchema {
  id: string
  name: string
  type: string
  [key: string]: unknown
}

export interface DatabaseSchema {
  id: string
  title: string
  properties: Record<string, PropertySchema>
  fetchedAt: number
}

export class SchemaCache {
  private cacheDir: string

  constructor(cacheDir?: string) {
    this.cacheDir = cacheDir ?? CACHE_DIR
  }

  private filePath(dbId: string): string {
    const normalised = dbId.replace(/-/g, '')
    return join(this.cacheDir, `${normalised}.json`)
  }

  get(dbId: string): DatabaseSchema | null {
    const fp = this.filePath(dbId)
    if (!existsSync(fp)) return null
    try {
      const stat = statSync(fp)
      if (Date.now() - stat.mtimeMs > TTL_MS) return null
      return JSON.parse(readFileSync(fp, 'utf-8')) as DatabaseSchema
    } catch {
      return null
    }
  }

  set(dbId: string, schema: DatabaseSchema): void {
    mkdirSync(this.cacheDir, { recursive: true })
    writeFileSync(this.filePath(dbId), JSON.stringify(schema, null, 2), 'utf-8')
  }

  invalidate(dbId: string): void {
    const fp = this.filePath(dbId)
    if (existsSync(fp)) unlinkSync(fp)
  }
}

export const schemaCache = new SchemaCache()

export class PropertyResolver {
  async getSchema(
    dbId: string,
    client: Client,
    opts: { noCache?: boolean; refresh?: boolean } = {}
  ): Promise<DatabaseSchema> {
    if (!opts.noCache && !opts.refresh) {
      const cached = schemaCache.get(dbId)
      if (cached) return cached
    }
    const db = await client.dataSources.retrieve({ data_source_id: dbId }) as any
    const schema = rawToSchema(db)
    if (!opts.noCache) {
      schemaCache.set(dbId, schema)
    }
    return schema
  }

  findProperty(schema: DatabaseSchema, name: string): PropertySchema | null {
    // Case-insensitive search
    const lower = name.toLowerCase()
    for (const prop of Object.values(schema.properties)) {
      if (prop.name.toLowerCase() === lower) return prop
    }
    return null
  }

  resolve(propName: string, value: string | string[], schema: DatabaseSchema): unknown {
    const prop = this.findProperty(schema, propName)
    if (!prop) return null
    return coerceValue(value, prop.type)
  }

  resolveAll(
    raw: Record<string, string | string[]>,
    schema: DatabaseSchema
  ): Record<string, unknown> {
    const result: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(raw)) {
      if (value == null) continue
      const prop = this.findProperty(schema, key)
      if (!prop) continue
      const coerced = coerceValue(value, prop.type)
      if (coerced != null) result[prop.name] = coerced
    }
    return result
  }
}

export const propertyResolver = new PropertyResolver()

export function rawToSchema(db: any): DatabaseSchema {
  const title = db.title?.[0]?.plain_text ?? db.id
  const properties: Record<string, PropertySchema> = {}
  for (const [, prop] of Object.entries(db.properties ?? {})) {
    const p = prop as any
    properties[p.name] = {
      id: p.id,
      name: p.name,
      type: p.type,
      ...(p[p.type] ? { options: (p[p.type] as any).options } : {}),
    }
  }
  return { id: db.id, title, properties, fetchedAt: Date.now() }
}
