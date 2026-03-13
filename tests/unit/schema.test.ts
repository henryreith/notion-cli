import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mkdtempSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { SchemaCache, PropertyResolver } from '../../src/schema.js'
import type { DatabaseSchema } from '../../src/schema.js'

const FAKE_DB_ID = 'a'.repeat(32)

function makeSchema(): DatabaseSchema {
  return {
    id: FAKE_DB_ID,
    title: 'Test DB',
    fetchedAt: Date.now(),
    properties: {
      Name: { id: 'title', name: 'Name', type: 'title' },
      Status: {
        id: 'status_id',
        name: 'Status',
        type: 'select',
        options: [{ name: 'Active' }, { name: 'Done' }],
      },
      Count: { id: 'count_id', name: 'Count', type: 'number' },
    },
  }
}

describe('SchemaCache', () => {
  let tmpDir: string
  let cache: SchemaCache

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'notion-cache-'))
    cache = new SchemaCache(tmpDir)
  })

  afterEach(() => {
    rmSync(tmpDir, { recursive: true, force: true })
  })

  it('returns null for missing schema', () => {
    expect(cache.get(FAKE_DB_ID)).toBeNull()
  })

  it('stores and retrieves a schema', () => {
    const schema = makeSchema()
    cache.set(FAKE_DB_ID, schema)
    const retrieved = cache.get(FAKE_DB_ID)
    expect(retrieved).not.toBeNull()
    expect(retrieved!.id).toBe(FAKE_DB_ID)
    expect(retrieved!.title).toBe('Test DB')
  })

  it('invalidates cached schema', () => {
    const schema = makeSchema()
    cache.set(FAKE_DB_ID, schema)
    cache.invalidate(FAKE_DB_ID)
    expect(cache.get(FAKE_DB_ID)).toBeNull()
  })

  it('handles invalidate on non-existent schema gracefully', () => {
    expect(() => cache.invalidate('nonexistent' + 'x'.repeat(20))).not.toThrow()
  })
})

describe('PropertyResolver', () => {
  let resolver: PropertyResolver

  beforeEach(() => {
    resolver = new PropertyResolver()
  })

  it('finds property case-insensitively', () => {
    const schema = makeSchema()
    expect(resolver.findProperty(schema, 'name')).not.toBeNull()
    expect(resolver.findProperty(schema, 'NAME')).not.toBeNull()
    expect(resolver.findProperty(schema, 'Status')).not.toBeNull()
  })

  it('returns null for unknown property', () => {
    const schema = makeSchema()
    expect(resolver.findProperty(schema, 'NonExistent')).toBeNull()
  })

  it('resolves title property', () => {
    const schema = makeSchema()
    const result = resolver.resolve('Name', 'Hello World', schema)
    expect(result).toEqual({ title: [{ type: 'text', text: { content: 'Hello World' } }] })
  })

  it('resolves select property', () => {
    const schema = makeSchema()
    const result = resolver.resolve('Status', 'Active', schema)
    expect(result).toEqual({ select: { name: 'Active' } })
  })

  it('resolves number property', () => {
    const schema = makeSchema()
    const result = resolver.resolve('Count', '42', schema)
    expect(result).toEqual({ number: 42 })
  })

  it('resolves all properties from raw object', () => {
    const schema = makeSchema()
    const result = resolver.resolveAll({ Name: 'Test', Count: '5', Status: 'Done' }, schema)
    expect(result).toHaveProperty('Name')
    expect(result).toHaveProperty('Count')
    expect(result).toHaveProperty('Status')
  })

  it('skips unknown properties in resolveAll', () => {
    const schema = makeSchema()
    const result = resolver.resolveAll({ UnknownProp: 'value', Name: 'Test' }, schema)
    expect(result).not.toHaveProperty('UnknownProp')
    expect(result).toHaveProperty('Name')
  })
})
