import { Command } from 'commander'
import { createNotionClient, normaliseId, iteratePaginatedAPI } from '../client.js'
import { die, ExitCode } from '../errors.js'
import { printJSON, printId, printIds } from '../output.js'
import { parseKV, readDataInput, markdownToBlocks, looksLikeMarkdown } from '../coerce.js'
import { PropertyResolver } from '../schema.js'
import { confirm, getMode } from '../modes.js'

const resolver = new PropertyResolver()

export function registerPage(program: Command): void {
  const page = program.command('page').description('Page commands')

  // page list
  page.command('list <parent-id>')
    .description('List child pages under a page or block')
    .option('--output <format>', 'Output format: json|ids', 'json')
    .action(async (parentId: string, opts: { output: string }) => {
      const client = createNotionClient()
      const id = normaliseId(parentId)
      const results: unknown[] = []

      for await (const block of iteratePaginatedAPI(client.blocks.children.list, { block_id: id })) {
        if ((block as any).type === 'child_page') {
          results.push(block)
        }
      }

      if (opts.output === 'ids') {
        printIds(results as Array<{ id: string }>)
      } else {
        printJSON(results)
      }
    })

  // page create
  page.command('create <parent-id>')
    .description('Create a new page')
    .requiredOption('--title <title>', 'Page title')
    .option('--data <input>', 'Additional properties as JSON: inline, @file, or -')
    .option('--output <format>', 'Output format: json|id', 'json')
    .action(async (parentId: string, opts: { title: string; data?: string; output: string }) => {
      const client = createNotionClient()
      const id = normaliseId(parentId)

      let extraProps: Record<string, unknown> = {}
      if (opts.data) {
        extraProps = readDataInput(opts.data) as Record<string, unknown>
      }

      const page = await client.pages.create({
        parent: { page_id: id } as any,
        properties: {
          title: { title: [{ type: 'text', text: { content: opts.title } }] },
          ...extraProps,
        } as any,
      }) as any

      if (opts.output === 'id') {
        printId(page.id)
      } else {
        printJSON(page)
      }
    })

  // page get
  page.command('get <page-id>')
    .description('Retrieve a page')
    .option('--output <format>', 'Output format: json|properties', 'json')
    .action(async (pageId: string, opts: { output: string }) => {
      const client = createNotionClient()
      const p = await client.pages.retrieve({ page_id: normaliseId(pageId) }) as any

      if (opts.output === 'properties') {
        printJSON(p.properties ?? {})
      } else {
        printJSON(p)
      }
    })

  // page get-property
  page.command('get-property <page-id> <property-name>')
    .description('Retrieve a single property value')
    .action(async (pageId: string, propertyName: string) => {
      const client = createNotionClient()
      const id = normaliseId(pageId)
      const p = await client.pages.retrieve({ page_id: id }) as any
      const props = p.properties ?? {}

      // Case-insensitive property lookup
      const lower = propertyName.toLowerCase()
      const key = Object.keys(props).find(k => k.toLowerCase() === lower)
      if (!key) die(ExitCode.NOT_FOUND, `Property not found: ${propertyName}`)

      printJSON(props[key])
    })

  // page set
  page.command('set <page-id> [kv...]')
    .description('Update page properties')
    .option('--data <input>', 'JSON input: inline, @file, or -')
    .option('--no-cache', 'Skip schema cache')
    .action(async (pageId: string, kv: string[], opts: { data?: string; cache: boolean }) => {
      const client = createNotionClient()
      const id = normaliseId(pageId)

      let raw: Record<string, string | string[]> = parseKV(kv)
      if (opts.data) {
        const parsed = readDataInput(opts.data) as Record<string, string | string[]>
        raw = { ...raw, ...parsed }
      }

      // Try to get parent DB schema for type-aware coercion
      let properties: Record<string, unknown> = {}
      try {
        const p = await client.pages.retrieve({ page_id: id }) as any
        const dbId = p.parent?.database_id
        if (dbId) {
          const schema = await resolver.getSchema(dbId, client, { noCache: !opts.cache })
          properties = resolver.resolveAll(raw, schema)
        } else {
          // Page without DB parent — just set title/properties directly
          properties = raw as Record<string, unknown>
        }
      } catch {
        properties = raw as Record<string, unknown>
      }

      const updated = await client.pages.update({
        page_id: id,
        properties: properties as any,
      }) as any
      printJSON(updated)
    })

  // page append
  page.command('append <page-id>')
    .description('Append blocks to a page')
    .requiredOption('--data <input>', 'Markdown or JSON blocks: inline, @file, or -')
    .action(async (pageId: string, opts: { data: string }) => {
      const client = createNotionClient()
      const id = normaliseId(pageId)

      let blocks: unknown[]
      let rawInput: string

      if (opts.data.startsWith('@')) {
        const { readFileSync } = await import('fs')
        rawInput = readFileSync(opts.data.slice(1), 'utf-8')
      } else if (opts.data === '-') {
        const { readFileSync } = await import('fs')
        rawInput = readFileSync('/dev/stdin', 'utf-8')
      } else {
        rawInput = opts.data
      }

      if (looksLikeMarkdown(rawInput)) {
        blocks = markdownToBlocks(rawInput)
      } else {
        try {
          const parsed = JSON.parse(rawInput)
          blocks = Array.isArray(parsed) ? parsed : [parsed]
        } catch {
          blocks = markdownToBlocks(rawInput)
        }
      }

      const result = await client.blocks.children.append({
        block_id: id,
        children: blocks as any,
      }) as any
      printJSON(result)
    })

  // page delete
  page.command('delete <page-id>')
    .description('Archive (delete) a page')
    .option('--confirm', 'Skip confirmation prompt')
    .action(async (pageId: string, opts: { confirm?: boolean }) => {
      const mode = opts.confirm ? 'auto' : getMode()
      const ok = await confirm(`Archive page ${pageId}?`, mode)
      if (!ok) { console.log('Cancelled.'); return }
      const client = createNotionClient()
      const updated = await client.pages.update({
        page_id: normaliseId(pageId),
        archived: true,
      }) as any
      printJSON({ status: 'archived', id: updated.id })
    })

  // page restore
  page.command('restore <page-id>')
    .description('Restore an archived page')
    .action(async (pageId: string) => {
      const client = createNotionClient()
      const updated = await client.pages.update({
        page_id: normaliseId(pageId),
        archived: false,
      }) as any
      printJSON({ status: 'restored', id: updated.id })
    })

  // page get-markdown (v5 SDK exclusive — reads full page content as markdown)
  page.command('get-markdown <page-id>')
    .description('Retrieve a page\'s full content as markdown (v5 SDK)')
    .action(async (pageId: string) => {
      const client = createNotionClient()
      const result = await client.pages.retrieveMarkdown({ page_id: normaliseId(pageId) }) as any
      // Output raw markdown to stdout (not JSON-wrapped — useful for piping)
      process.stdout.write((result.markdown ?? result) + '\n')
    })

  // page set-markdown (v5 SDK exclusive — replaces full page content with markdown)
  page.command('set-markdown <page-id>')
    .description('Replace page content with markdown (v5 SDK)')
    .requiredOption('--data <input>', 'Markdown: inline string, @file, or -')
    .action(async (pageId: string, opts: { data: string }) => {
      const client = createNotionClient()
      const id = normaliseId(pageId)

      let markdown: string
      if (opts.data.startsWith('@')) {
        const { readFileSync } = await import('fs')
        markdown = readFileSync(opts.data.slice(1), 'utf-8')
      } else if (opts.data === '-') {
        const { readFileSync } = await import('fs')
        markdown = readFileSync('/dev/stdin', 'utf-8')
      } else {
        markdown = opts.data
      }

      const result = await client.pages.updateMarkdown({
        page_id: id,
        type: 'insert_content',
        insert_content: { content: markdown },
      }) as any
      printJSON(result)
    })

  // page move
  page.command('move <page-id> <new-parent-id>')
    .description('Move a page to a new parent')
    .action(async (pageId: string, newParentId: string) => {
      const client = createNotionClient()
      const id = normaliseId(pageId)
      const newParent = normaliseId(newParentId)

      const updated = await client.pages.move({
        page_id: id,
        parent: { page_id: newParent },
      }) as any
      printJSON({ status: 'moved', id: updated.id, new_parent: newParent })
    })
}
