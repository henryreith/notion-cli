import { describe, it, expect } from 'vitest'
import { parseKV, coerceValue, markdownToBlocks, looksLikeMarkdown, buildTypedFilter } from '../../src/coerce.js'

describe('parseKV', () => {
  it('parses key=value pairs', () => {
    expect(parseKV(['Name=Alice', 'Status=Active'])).toEqual({ Name: 'Alice', Status: 'Active' })
  })

  it('handles values with = signs', () => {
    expect(parseKV(['URL=https://example.com?a=1'])).toEqual({ URL: 'https://example.com?a=1' })
  })

  it('skips args without =', () => {
    expect(parseKV(['no-equals'])).toEqual({})
  })
})

describe('coerceValue', () => {
  it('coerces title', () => {
    expect(coerceValue('Hello', 'title')).toEqual({
      title: [{ type: 'text', text: { content: 'Hello' } }],
    })
  })

  it('coerces rich_text', () => {
    expect(coerceValue('Some text', 'rich_text')).toEqual({
      rich_text: [{ type: 'text', text: { content: 'Some text' } }],
    })
  })

  it('coerces select', () => {
    expect(coerceValue('Option A', 'select')).toEqual({ select: { name: 'Option A' } })
  })

  it('coerces multi_select from comma-separated string', () => {
    expect(coerceValue('a,b,c', 'multi_select')).toEqual({
      multi_select: [{ name: 'a' }, { name: 'b' }, { name: 'c' }],
    })
  })

  it('coerces multi_select from array', () => {
    expect(coerceValue(['x', 'y'], 'multi_select')).toEqual({
      multi_select: [{ name: 'x' }, { name: 'y' }],
    })
  })

  it('coerces number', () => {
    expect(coerceValue('42', 'number')).toEqual({ number: 42 })
  })

  it('coerces checkbox true', () => {
    expect(coerceValue('true', 'checkbox')).toEqual({ checkbox: true })
  })

  it('coerces checkbox false', () => {
    expect(coerceValue('false', 'checkbox')).toEqual({ checkbox: false })
  })

  it('coerces date', () => {
    expect(coerceValue('2024-01-15', 'date')).toEqual({ date: { start: '2024-01-15', end: null } })
  })

  it('coerces url', () => {
    expect(coerceValue('https://example.com', 'url')).toEqual({ url: 'https://example.com' })
  })

  it('coerces relation', () => {
    expect(coerceValue('abc123', 'relation')).toEqual({ relation: [{ id: 'abc123' }] })
  })

  it('coerces people', () => {
    expect(coerceValue('uid1', 'people')).toEqual({
      people: [{ object: 'user', id: 'uid1' }],
    })
  })
})

describe('markdownToBlocks', () => {
  it('converts heading 1', () => {
    const blocks = markdownToBlocks('# Title')
    expect(blocks[0]).toMatchObject({ type: 'heading_1', heading_1: { rich_text: [{ text: { content: 'Title' } }] } })
  })

  it('converts heading 2', () => {
    const blocks = markdownToBlocks('## Sub')
    expect(blocks[0]).toMatchObject({ type: 'heading_2' })
  })

  it('converts bulleted list', () => {
    const blocks = markdownToBlocks('- item one')
    expect(blocks[0]).toMatchObject({ type: 'bulleted_list_item' })
  })

  it('converts numbered list', () => {
    const blocks = markdownToBlocks('1. first item')
    expect(blocks[0]).toMatchObject({ type: 'numbered_list_item' })
  })

  it('converts blockquote', () => {
    const blocks = markdownToBlocks('> quote text')
    expect(blocks[0]).toMatchObject({ type: 'quote' })
  })

  it('converts code block', () => {
    const blocks = markdownToBlocks('```typescript\nconst x = 1\n```')
    expect(blocks[0]).toMatchObject({ type: 'code', code: { language: 'typescript' } })
  })

  it('converts divider', () => {
    const blocks = markdownToBlocks('---')
    expect(blocks[0]).toMatchObject({ type: 'divider' })
  })

  it('converts plain text to paragraph', () => {
    const blocks = markdownToBlocks('Just some text')
    expect(blocks[0]).toMatchObject({ type: 'paragraph' })
  })

  it('skips empty lines', () => {
    const blocks = markdownToBlocks('line1\n\nline2')
    expect(blocks).toHaveLength(2)
  })
})

describe('looksLikeMarkdown', () => {
  it('detects headings', () => expect(looksLikeMarkdown('# heading')).toBe(true))
  it('detects lists', () => expect(looksLikeMarkdown('- item')).toBe(true))
  it('detects code fences', () => expect(looksLikeMarkdown('```\ncode\n```')).toBe(true))
  it('rejects plain text', () => expect(looksLikeMarkdown('just text')).toBe(false))
})

describe('buildTypedFilter', () => {
  it('builds text equals filter', () => {
    const f = buildTypedFilter('Status', '=', 'Active', 'select')
    expect(f).toEqual({ property: 'Status', select: { equals: 'Active' } })
  })

  it('builds number greater_than filter', () => {
    const f = buildTypedFilter('Count', '>', '5', 'number')
    expect(f).toEqual({ property: 'Count', number: { greater_than: 5 } })
  })

  it('builds checkbox filter', () => {
    const f = buildTypedFilter('Done', '=', 'true', 'checkbox')
    expect(f).toEqual({ property: 'Done', checkbox: { equals: true } })
  })
})
