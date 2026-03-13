import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('output module', () => {
  let writeOutput: string
  let originalWrite: typeof process.stdout.write

  beforeEach(() => {
    writeOutput = ''
    originalWrite = process.stdout.write.bind(process.stdout)
    process.stdout.write = ((s: string) => { writeOutput += s; return true }) as any
  })

  afterEach(() => {
    process.stdout.write = originalWrite
  })

  it('printJSON outputs pretty JSON', async () => {
    const { printJSON } = await import('../../src/output.js')
    printJSON({ key: 'value' })
    expect(writeOutput).toContain('"key": "value"')
    expect(writeOutput).toContain('\n')
  })

  it('printId outputs normalised ID', async () => {
    const { printId } = await import('../../src/output.js')
    printId('abc-def-123')
    expect(writeOutput).toBe('abcdef123\n')
  })

  it('printIds outputs one ID per line', async () => {
    const { printIds } = await import('../../src/output.js')
    printIds([{ id: 'aaa-111' }, { id: 'bbb-222' }])
    expect(writeOutput).toBe('aaa111\nbbb222\n')
  })
})
