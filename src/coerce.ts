import { readFileSync } from 'fs'

export function parseKV(args: string[]): Record<string, string> {
  const result: Record<string, string> = {}
  for (const arg of args) {
    const idx = arg.indexOf('=')
    if (idx === -1) continue
    result[arg.slice(0, idx)] = arg.slice(idx + 1)
  }
  return result
}

export function readDataInput(data: string): unknown {
  if (data.startsWith('@')) {
    return JSON.parse(readFileSync(data.slice(1), 'utf-8'))
  }
  if (data === '-') {
    const buf = readFileSync('/dev/stdin', 'utf-8')
    return JSON.parse(buf)
  }
  return JSON.parse(data)
}

export function buildFilter(filterArgs: string[]): Record<string, unknown> | undefined {
  if (!filterArgs.length) return undefined

  const conditions = filterArgs.map(f => {
    const parts = f.split(':')
    if (parts.length < 3) throw new Error(`Invalid filter format: ${f}. Expected PROP:OP:VALUE`)
    const [prop, op, ...valueParts] = parts
    const value = valueParts.join(':')

    const condition: Record<string, unknown> = { property: prop }

    switch (op) {
      case '=': case 'equals':
        condition['rich_text'] = { equals: value }
        // Will be resolved properly with schema info
        return { property: prop as string, rich_text: { equals: value } }
      case '!=': case 'does_not_equal':
        return { property: prop as string, rich_text: { does_not_equal: value } }
      case 'contains':
        return { property: prop as string, rich_text: { contains: value } }
      case 'starts_with':
        return { property: prop as string, rich_text: { starts_with: value } }
      case 'is_empty':
        return { property: prop as string, rich_text: { is_empty: true } }
      case 'is_not_empty':
        return { property: prop as string, rich_text: { is_not_empty: true } }
      default:
        return { property: prop as string, rich_text: { equals: value } }
    }
  })

  if (conditions.length === 1) {
    return { filter: conditions[0] }
  }
  return { filter: { and: conditions } }
}

export function buildTypedFilter(
  prop: string,
  op: string,
  value: string,
  propType: string
): Record<string, unknown> {
  const typeKey = getFilterTypeKey(propType)
  const condition = buildCondition(op, value, propType)
  return { property: prop, [typeKey]: condition }
}

function getFilterTypeKey(propType: string): string {
  switch (propType) {
    case 'title': return 'title'
    case 'rich_text': return 'rich_text'
    case 'select': return 'select'
    case 'multi_select': return 'multi_select'
    case 'number': return 'number'
    case 'checkbox': return 'checkbox'
    case 'date': return 'date'
    case 'url': return 'url'
    case 'email': return 'email'
    case 'phone_number': return 'phone_number'
    case 'people': return 'people'
    case 'relation': return 'relation'
    case 'formula': return 'formula'
    case 'status': return 'status'
    default: return 'rich_text'
  }
}

function buildCondition(op: string, value: string, propType: string): Record<string, unknown> {
  if (propType === 'checkbox') {
    return { equals: value === 'true' }
  }
  if (propType === 'number') {
    switch (op) {
      case '=': case 'equals': return { equals: Number(value) }
      case '!=': case 'does_not_equal': return { does_not_equal: Number(value) }
      case '>': case 'greater_than': return { greater_than: Number(value) }
      case '<': case 'less_than': return { less_than: Number(value) }
      case '>=': case 'greater_than_or_equal_to': return { greater_than_or_equal_to: Number(value) }
      case '<=': case 'less_than_or_equal_to': return { less_than_or_equal_to: Number(value) }
    }
  }
  switch (op) {
    case '=': case 'equals': return { equals: value }
    case '!=': case 'does_not_equal': return { does_not_equal: value }
    case 'contains': return { contains: value }
    case 'does_not_contain': return { does_not_contain: value }
    case 'starts_with': return { starts_with: value }
    case 'ends_with': return { ends_with: value }
    case 'is_empty': return { is_empty: true }
    case 'is_not_empty': return { is_not_empty: true }
    default: return { equals: value }
  }
}

export function coerceValue(value: string | string[], propType: string): unknown {
  switch (propType) {
    case 'title':
      return { title: [{ type: 'text', text: { content: String(value) } }] }
    case 'rich_text':
      return { rich_text: [{ type: 'text', text: { content: String(value) } }] }
    case 'select':
      return { select: { name: String(value) } }
    case 'status':
      return { status: { name: String(value) } }
    case 'multi_select': {
      const items = Array.isArray(value) ? value : String(value).split(',').map(s => s.trim())
      return { multi_select: items.map(name => ({ name })) }
    }
    case 'number':
      return { number: Number(value) }
    case 'checkbox':
      return { checkbox: value === 'true' }
    case 'date':
      return { date: { start: String(value), end: null } }
    case 'url':
      return { url: String(value) }
    case 'email':
      return { email: String(value) }
    case 'phone_number':
      return { phone_number: String(value) }
    case 'relation': {
      const ids = Array.isArray(value) ? value : [String(value)]
      return { relation: ids.map(id => ({ id })) }
    }
    case 'people': {
      const ids = Array.isArray(value) ? value : [String(value)]
      return { people: ids.map(id => ({ object: 'user', id })) }
    }
    default:
      return { rich_text: [{ type: 'text', text: { content: String(value) } }] }
  }
}

export function markdownToBlocks(md: string): unknown[] {
  const blocks: unknown[] = []
  const lines = md.split('\n')
  let i = 0

  while (i < lines.length) {
    const line = lines[i]!
    if (line === '') {
      i++
      continue
    }

    if (line.startsWith('# ')) {
      blocks.push({ object: 'block', type: 'heading_1', heading_1: { rich_text: [{ type: 'text', text: { content: line.slice(2) } }] } })
    } else if (line.startsWith('## ')) {
      blocks.push({ object: 'block', type: 'heading_2', heading_2: { rich_text: [{ type: 'text', text: { content: line.slice(3) } }] } })
    } else if (line.startsWith('### ')) {
      blocks.push({ object: 'block', type: 'heading_3', heading_3: { rich_text: [{ type: 'text', text: { content: line.slice(4) } }] } })
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      blocks.push({ object: 'block', type: 'bulleted_list_item', bulleted_list_item: { rich_text: [{ type: 'text', text: { content: line.slice(2) } }] } })
    } else if (/^\d+\. /.test(line)) {
      blocks.push({ object: 'block', type: 'numbered_list_item', numbered_list_item: { rich_text: [{ type: 'text', text: { content: line.replace(/^\d+\. /, '') } }] } })
    } else if (line.startsWith('> ')) {
      blocks.push({ object: 'block', type: 'quote', quote: { rich_text: [{ type: 'text', text: { content: line.slice(2) } }] } })
    } else if (line.startsWith('```')) {
      const lang = line.slice(3).trim()
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i]!.startsWith('```')) {
        codeLines.push(lines[i]!)
        i++
      }
      blocks.push({ object: 'block', type: 'code', code: { rich_text: [{ type: 'text', text: { content: codeLines.join('\n') } }], language: lang || 'plain text' } })
    } else if (line === '---' || line === '***') {
      blocks.push({ object: 'block', type: 'divider', divider: {} })
    } else {
      blocks.push({ object: 'block', type: 'paragraph', paragraph: { rich_text: [{ type: 'text', text: { content: line } }] } })
    }

    i++
  }

  return blocks
}

export function looksLikeMarkdown(input: string): boolean {
  return /^#{1,3} |^[-*] |^\d+\. |^> |^```/.test(input.trim())
}
