import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getMode, confirmDestructive } from '../../src/modes.js'

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

describe('confirmDestructive', () => {
  const originalMode = process.env['NOTION_MODE']
  const originalAutoConfirm = process.env['NOTION_AUTO_CONFIRM']

  afterEach(() => {
    if (originalMode === undefined) delete process.env['NOTION_MODE']
    else process.env['NOTION_MODE'] = originalMode
    if (originalAutoConfirm === undefined) delete process.env['NOTION_AUTO_CONFIRM']
    else process.env['NOTION_AUTO_CONFIRM'] = originalAutoConfirm
    vi.restoreAllMocks()
  })

  it('proceeds when --confirm was passed, regardless of mode', async () => {
    process.env['NOTION_MODE'] = 'ci'
    await expect(confirmDestructive('Delete?', true)).resolves.toBe(true)
  })

  it('proceeds when NOTION_AUTO_CONFIRM=1 in non-interactive mode', async () => {
    process.env['NOTION_MODE'] = 'ci'
    process.env['NOTION_AUTO_CONFIRM'] = '1'
    await expect(confirmDestructive('Delete?', false)).resolves.toBe(true)
  })

  it('refuses with exit 3 in non-interactive mode without --confirm', async () => {
    process.env['NOTION_MODE'] = 'ci'
    delete process.env['NOTION_AUTO_CONFIRM']
    const stderrSpy = vi.spyOn(process.stderr, 'write').mockReturnValue(true)
    const exitSpy = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('process.exit called')
    }) as never)

    await expect(confirmDestructive('Delete?', false)).rejects.toThrow('process.exit called')
    expect(exitSpy).toHaveBeenCalledWith(3)
    const errorOutput = String(stderrSpy.mock.calls[0]?.[0])
    expect(errorOutput).toContain('--confirm')
    expect(errorOutput).toContain('NOTION_AUTO_CONFIRM')
  })
})
