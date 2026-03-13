import { Command } from 'commander'
import { createNotionClient, normaliseId } from '../client.js'
import { die, ExitCode } from '../errors.js'
import { printJSON, printIds, printTable, printId } from '../output.js'
import { parseKV, readDataInput, buildTypedFilter } from '../coerce.js'
import { PropertyResolver, schemaCache, rawToSchema } from '../schema.js'
import { confirm, getMode } from '../modes.js'

const resolver = new PropertyResolver()

export function registerDb(program: Command): void {
  const db = program.command('db').description('Database commands')

  // db schema
  db.command('schema <db-id>')
    .description('Fetch data source schema')
    .option('--refresh', 'Force re-fetch from API')
    .option('--no-cache', 'Skip reading/writing cache')
    .option('--output <format>', 'Output format: json|properties|options', 'json')
    .action(async (dbId: string, opts: { refresh?: boolean; cache: boolean; output: string }) => {
      const client = createNotionClient()
      const id = normaliseId(dbId)
      const schema = await resolver.getSchema(id, client, {
        noCache: !opts.cache,
        refresh: opts.refresh,
      })

      if (opts.output === 'properties') {
        for (const prop of Object.values(schema.properties)) {
          console.log(`${prop.name} (${prop.type})`)
        }
      } else if (opts.output === 'options') {
        for (const prop of Object.values(schema.properties)) {
          const p = prop as any
          if (p.options?.length) {
            console.log(`${prop.name}:`)
            for (const opt of p.options) {
              console.log(`  - ${opt.name}`)
            }
          }
        }
      } else {
        printJSON(schema)
      }
    })

  // db query
  db.command('query <db-id>')
    .description('Query a data source')
    .option('--filter <PROP:OP:VALUE>', 'Filter condition (repeatable)', collect, [])
    .option('--sort <PROP>', 'Sort by property (prefix - for descending)')
    .option('--limit <N>', 'Maximum results', parseInt)
    .option('--page-all', 'Fetch all pages')
    .option('--output <format>', 'Output format: json|table|ids', 'json')
    .action(async (dbId: string, opts: {
      filter: string[]
      sort?: string
      limit?: number
      pageAll?: boolean
      output: string
    }) => {
      const client = createNotionClient()
      const id = normaliseId(dbId)

      // Build filter from args with schema-aware types
      let filterObj: Record<string, unknown> | undefined
      if (opts.filter.length) {
        const schema = await resolver.getSchema(id, client)
        const conditions = opts.filter.map(f => {
          const parts = f.split(':')
          if (parts.length < 3) die(ExitCode.VALIDATION, `Invalid filter: ${f}`)
          const prop = parts[0]!
          const op = parts[1]!
          const value = parts.slice(2).join(':')
          const propSchema = resolver.findProperty(schema, prop)
          const propType = propSchema?.type ?? 'rich_text'
          return buildTypedFilter(prop, op, value, propType)
        })
        filterObj = conditions.length === 1 ? conditions[0] : { and: conditions }
      }

      // Build sorts
      const sorts = opts.sort ? [buildSort(opts.sort)] : undefined

      const results: unknown[] = []
      let cursor: string | undefined

      do {
        const body: Record<string, unknown> = {}
        if (filterObj) body['filter'] = filterObj
        if (sorts) body['sorts'] = sorts
        if (cursor) body['start_cursor'] = cursor
        if (opts.limit && !opts.pageAll) body['page_size'] = Math.min(opts.limit, 100)

        const res = await client.dataSources.query({
          data_source_id: id,
          ...(body as any),
        })

        results.push(...res.results)
        cursor = res.has_more ? res.next_cursor ?? undefined : undefined

        if (!opts.pageAll && opts.limit && results.length >= opts.limit) break
        if (!opts.pageAll && !opts.limit) break
      } while (cursor)

      const limited = opts.limit ? results.slice(0, opts.limit) : results

      if (opts.output === 'ids') {
        printIds(limited as Array<{ id: string }>)
      } else if (opts.output === 'table') {
        const rows = (limited as any[]).map(pageToTableRow)
        const cols = rows.length > 0 ? Object.keys(rows[0]!) : ['id']
        printTable(rows, cols.slice(0, 5))
      } else {
        printJSON(limited)
      }
    })

  // db info
  db.command('info <db-id>')
    .description('Show raw database container metadata')
    .action(async (dbId: string) => {
      const client = createNotionClient()
      const db = await client.databases.retrieve({ database_id: normaliseId(dbId) })
      printJSON(db)
    })

  // db list-templates
  db.command('list-templates <db-id>')
    .description('List data source templates')
    .action(async (dbId: string) => {
      const client = createNotionClient()
      const result = await client.dataSources.listTemplates({ data_source_id: normaliseId(dbId) })
      printJSON(result)
    })

  // db add
  db.command('add <db-id> [kv...]')
    .description('Add a row to a data source')
    .option('--data <input>', 'JSON input: inline, @file, or -')
    .option('--add-options', 'Auto-create missing select/multi_select options')
    .option('--output <format>', 'Output format: json|id', 'json')
    .option('--no-cache', 'Skip schema cache')
    .action(async (dbId: string, kv: string[], opts: {
      data?: string
      addOptions?: boolean
      output: string
      cache: boolean
    }) => {
      const client = createNotionClient()
      const id = normaliseId(dbId)
      const schema = await resolver.getSchema(id, client, { noCache: !opts.cache })

      let raw: Record<string, string | string[]> = parseKV(kv)
      if (opts.data) {
        const parsed = readDataInput(opts.data) as Record<string, string | string[]>
        raw = { ...raw, ...parsed }
      }

      if (opts.addOptions) {
        await ensureOptions(client, id, schema, raw)
        // Refresh schema after adding options
        await resolver.getSchema(id, client, { refresh: true })
      }

      const freshSchema = await resolver.getSchema(id, client, { noCache: !opts.cache })
      const properties = resolver.resolveAll(raw, freshSchema)

      const page = await client.pages.create({
        parent: { database_id: id } as any,
        properties: properties as any,
      })

      if (opts.output === 'id') {
        printId(page.id)
      } else {
        printJSON(page)
      }
    })

  // db upsert
  db.command('upsert <db-id> [kv...]')
    .description('Insert or update a row matching --match criteria')
    .requiredOption('--match <PROP:VALUE>', 'Match property:value')
    .option('--data <input>', 'JSON input: inline, @file, or -')
    .option('--add-options', 'Auto-create missing select/multi_select options')
    .option('--no-cache', 'Skip schema cache')
    .action(async (dbId: string, kv: string[], opts: {
      match: string
      data?: string
      addOptions?: boolean
      cache: boolean
    }) => {
      const client = createNotionClient()
      const id = normaliseId(dbId)
      const schema = await resolver.getSchema(id, client, { noCache: !opts.cache })

      const matchParts = opts.match.split(':')
      if (matchParts.length < 2) die(ExitCode.VALIDATION, 'Invalid --match format. Expected PROP:VALUE')
      const matchProp = matchParts[0]!
      const matchValue = matchParts.slice(1).join(':')

      const propSchema = resolver.findProperty(schema, matchProp)
      const propType = propSchema?.type ?? 'rich_text'
      const filterCond = buildTypedFilter(matchProp, '=', matchValue, propType)

      const res = await client.dataSources.query({
        data_source_id: id,
        filter: filterCond as any,
      })

      if (res.results.length > 1) {
        die(ExitCode.AMBIGUOUS, `Upsert matched ${res.results.length} rows`, { property: matchProp, value: matchValue })
      }

      let raw: Record<string, string | string[]> = parseKV(kv)
      if (opts.data) {
        const parsed = readDataInput(opts.data) as Record<string, string | string[]>
        raw = { ...raw, ...parsed }
      }

      if (opts.addOptions) {
        await ensureOptions(client, id, schema, raw)
      }

      const freshSchema = await resolver.getSchema(id, client, { noCache: !opts.cache })
      const properties = resolver.resolveAll(raw, freshSchema)

      if (res.results.length === 0) {
        const page = await client.pages.create({
          parent: { database_id: id } as any,
          properties: properties as any,
        })
        printJSON({ action: 'created', id: page.id })
      } else {
        const pageId = (res.results[0] as any).id as string
        const page = await client.pages.update({
          page_id: pageId,
          properties: properties as any,
        })
        printJSON({ action: 'updated', id: page.id })
      }
    })

  // db update-row
  db.command('update-row <page-id> [kv...]')
    .description('Update properties of an existing row')
    .option('--data <input>', 'JSON input: inline, @file, or -')
    .option('--no-cache', 'Skip schema cache')
    .action(async (pageId: string, kv: string[], opts: { data?: string; cache: boolean }) => {
      const client = createNotionClient()
      const id = normaliseId(pageId)

      // Fetch page to find parent database
      const page = await client.pages.retrieve({ page_id: id }) as any
      const dbId = page.parent?.database_id
      if (!dbId) die(ExitCode.VALIDATION, 'Page is not part of a database')

      const schema = await resolver.getSchema(dbId as string, client, { noCache: !opts.cache })

      let raw: Record<string, string | string[]> = parseKV(kv)
      if (opts.data) {
        const parsed = readDataInput(opts.data) as Record<string, string | string[]>
        raw = { ...raw, ...parsed }
      }

      const properties = resolver.resolveAll(raw, schema)
      const updated = await client.pages.update({
        page_id: id,
        properties: properties as any,
      })
      printJSON(updated)
    })

  // db add-option
  db.command('add-option <db-id> <property>')
    .description('Add select/multi_select options to a property')
    .requiredOption('--option <name>', 'Option name (repeatable)', collect, [])
    .option('--color <color>', 'Option color')
    .action(async (dbId: string, property: string, opts: { option: string[]; color?: string }) => {
      const client = createNotionClient()
      const id = normaliseId(dbId)
      const schema = await resolver.getSchema(id, client, { refresh: true })

      const prop = resolver.findProperty(schema, property)
      if (!prop) die(ExitCode.VALIDATION, `Property not found: ${property}`)
      if (prop.type !== 'select' && prop.type !== 'multi_select') {
        die(ExitCode.VALIDATION, `Property ${property} is ${prop.type}, not select or multi_select`)
      }

      const existingOptions: string[] = ((prop as any).options ?? []).map((o: any) => o.name as string)
      const newOptions = opts.option.filter(o => !existingOptions.includes(o))

      if (newOptions.length === 0) {
        printJSON({ message: 'All options already exist', options: opts.option })
        return
      }

      const allOptions = [
        ...existingOptions.map(name => ({ name })),
        ...newOptions.map(name => ({ name, ...(opts.color ? { color: opts.color } : {}) })),
      ]

      await client.dataSources.update({
        data_source_id: id,
        properties: {
          [prop.name]: { [prop.type]: { options: allOptions } } as any,
        },
      })

      schemaCache.invalidate(id)
      printJSON({ added: newOptions, skipped: opts.option.filter(o => existingOptions.includes(o)) })
    })

  // db batch-add
  db.command('batch-add <db-id>')
    .description('Batch insert rows from a JSON array')
    .requiredOption('--data <input>', 'JSON array: @file or -')
    .option('--dry-run', 'Validate only, no writes')
    .option('--continue-on-error', 'Skip failed rows instead of stopping')
    .option('--no-cache', 'Skip schema cache')
    .action(async (dbId: string, opts: {
      data: string
      dryRun?: boolean
      continueOnError?: boolean
      cache: boolean
    }) => {
      const client = createNotionClient()
      const id = normaliseId(dbId)
      const schema = await resolver.getSchema(id, client, { noCache: !opts.cache })

      const rows = readDataInput(opts.data) as Record<string, string | string[]>[]
      if (!Array.isArray(rows)) die(ExitCode.VALIDATION, '--data must be a JSON array')

      // Validate all rows first
      const validated: Array<Record<string, unknown>> = []
      for (let i = 0; i < rows.length; i++) {
        const properties = resolver.resolveAll(rows[i]!, schema)
        if (Object.keys(properties).length === 0) {
          if (!opts.continueOnError) die(ExitCode.VALIDATION, `Row ${i}: no valid properties`)
          process.stderr.write(JSON.stringify({ error: `Row ${i}: no valid properties` }) + '\n')
          validated.push({})
        } else {
          validated.push(properties)
        }
      }

      if (opts.dryRun) {
        printJSON({ dry_run: true, rows: rows.length, validated: validated.length })
        process.exit(ExitCode.DRY_RUN)
      }

      const results: unknown[] = []
      for (let i = 0; i < validated.length; i++) {
        const props = validated[i]!
        if (Object.keys(props).length === 0) continue
        try {
          const page = await client.pages.create({
            parent: { database_id: id } as any,
            properties: props as any,
          })
          results.push({ index: i, id: page.id, status: 'created' })
        } catch (err: any) {
          if (!opts.continueOnError) die(ExitCode.API, `Row ${i} failed: ${err.message}`)
          process.stderr.write(JSON.stringify({ error: `Row ${i}: ${err.message}` }) + '\n')
          results.push({ index: i, status: 'failed', error: err.message })
        }
        // Rate limiting: 350ms between requests
        if (i < validated.length - 1) {
          await sleep(350)
        }
      }

      printJSON({ inserted: results.filter((r: any) => r.status === 'created').length, results })
    })

  // db create
  db.command('create <parent-id> <title>')
    .description('Create a new data source')
    .option('--data <schema-json>', 'Extra properties schema as JSON')
    .option('--output <format>', 'Output format: json|id', 'json')
    .action(async (parentId: string, title: string, opts: { data?: string; output: string }) => {
      const client = createNotionClient()
      const id = normaliseId(parentId)

      let extraProps: Record<string, unknown> = {}
      if (opts.data) {
        extraProps = readDataInput(opts.data) as Record<string, unknown>
      }

      const ds = await client.dataSources.create({
        parent: { page_id: id } as any,
        title: [{ type: 'text', text: { content: title } }] as any,
        properties: {
          Name: { title: {} },
          ...extraProps,
        } as any,
      })

      if (opts.output === 'id') {
        printId(ds.id)
      } else {
        printJSON(ds)
      }
    })

  // db delete
  db.command('delete <db-id>')
    .description('Archive a data source')
    .option('--confirm', 'Skip confirmation prompt')
    .action(async (dbId: string, opts: { confirm?: boolean }) => {
      const mode = opts.confirm ? 'auto' : getMode()
      const ok = await confirm(`Archive database ${dbId}?`, mode)
      if (!ok) {
        console.log('Cancelled.')
        return
      }
      const client = createNotionClient()
      const id = normaliseId(dbId)
      await client.dataSources.update({ data_source_id: id, in_trash: true })
      schemaCache.invalidate(id)
      printJSON({ status: 'archived', id })
    })

  // db update-schema
  db.command('update-schema <db-id>')
    .description('Update data source schema properties')
    .requiredOption('--data <input>', 'JSON properties object: inline, @file, or -')
    .action(async (dbId: string, opts: { data: string }) => {
      const client = createNotionClient()
      const id = normaliseId(dbId)
      const properties = readDataInput(opts.data) as Record<string, unknown>
      const updated = await client.dataSources.update({
        data_source_id: id,
        properties: properties as any,
      })
      schemaCache.invalidate(id)
      printJSON(updated)
    })
}

function buildSort(sortArg: string): Record<string, unknown> {
  if (sortArg.startsWith('-')) {
    return { property: sortArg.slice(1), direction: 'descending' }
  }
  return { property: sortArg, direction: 'ascending' }
}

function pageToTableRow(page: any): Record<string, string> {
  const row: Record<string, string> = { id: page.id }
  for (const [name, prop] of Object.entries(page.properties ?? {})) {
    row[name] = extractPropText(prop as any)
  }
  return row
}

function extractPropText(prop: any): string {
  if (!prop) return ''
  switch (prop.type) {
    case 'title': return prop.title?.map((t: any) => t.plain_text).join('') ?? ''
    case 'rich_text': return prop.rich_text?.map((t: any) => t.plain_text).join('') ?? ''
    case 'select': return prop.select?.name ?? ''
    case 'status': return prop.status?.name ?? ''
    case 'multi_select': return prop.multi_select?.map((o: any) => o.name).join(', ') ?? ''
    case 'number': return String(prop.number ?? '')
    case 'checkbox': return String(prop.checkbox ?? '')
    case 'date': return prop.date?.start ?? ''
    case 'url': return prop.url ?? ''
    default: return ''
  }
}

async function ensureOptions(
  client: any,
  dbId: string,
  schema: any,
  raw: Record<string, string | string[]>
): Promise<void> {
  for (const [key, value] of Object.entries(raw)) {
    const prop = schema.properties[key] ?? Object.values(schema.properties).find(
      (p: any) => (p as any).name.toLowerCase() === key.toLowerCase()
    ) as any
    if (!prop) continue
    if (prop.type !== 'select' && prop.type !== 'multi_select') continue

    const newNames = Array.isArray(value) ? value : [String(value)]
    const existing: string[] = (prop.options ?? []).map((o: any) => o.name as string)
    const toAdd = newNames.filter(n => !existing.includes(n))
    if (!toAdd.length) continue

    const allOptions = [
      ...existing.map((name: string) => ({ name })),
      ...toAdd.map(name => ({ name })),
    ]
    await client.dataSources.update({
      data_source_id: dbId,
      properties: { [prop.name]: { [prop.type]: { options: allOptions } } },
    })
    schemaCache.invalidate(dbId)
  }
}

function collect(val: string, prev: string[]): string[] {
  return [...prev, val]
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}
