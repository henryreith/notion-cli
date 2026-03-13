import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getMode } from '../../src/modes.js'

describe('getMode', () => {
  const originalEnv = process.env['NOTION_MODE']
  const originalIsTTY = process.stdout.isTTY

  afterEach(() => {
    if (originalEnv === undefined) delete process.env['NOTION_MODE']
    else process.env['NOTION_MODE'] = originalEnv
    Object.defineProperty(process.stdout, 'isTTY', { value: originalIsTTY, writable: true })
  })

  it('returns flag value when provided', () => {
    expect(getMode('auto')).toBe('auto')
    expect(getMode('interactive')).toBe('interactive')
    expect(getMode('ci')).toBe('ci')
  })

  it('returns env value when no flag', () => {
    process.env['NOTION_MODE'] = 'auto'
    expect(getMode()).toBe('auto')
  })

  it('falls through on invalid env value to TTY detection', () => {
    process.env['NOTION_MODE'] = 'invalid'
    Object.defineProperty(process.stdout, 'isTTY', { value: false, writable: true })
    expect(getMode()).toBe('auto')
  })

  it('returns auto when no TTY', () => {
    delete process.env['NOTION_MODE']
    Object.defineProperty(process.stdout, 'isTTY', { value: false, writable: true })
    expect(getMode()).toBe('auto')
  })

  it('returns interactive when TTY', () => {
    delete process.env['NOTION_MODE']
    Object.defineProperty(process.stdout, 'isTTY', { value: true, writable: true })
    expect(getMode()).toBe('interactive')
  })
})
