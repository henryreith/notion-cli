import { Command } from 'commander'
import { createNotionClient, collectPaginatedAPI } from '../client.js'
import { printJSON, printIds } from '../output.js'

export function registerSearch(program: Command): void {
  program.command('search [query]')
    .description('Search pages and databases')
    .option('--type <type>', 'Filter by type: page|database')
    .option('--sort <sort>', 'Sort: last_edited|relevance', 'relevance')
    .option('--limit <N>', 'Maximum results', parseInt)
    .option('--page-all', 'Fetch all pages')
    .option('--output <format>', 'Output format: json|ids', 'json')
    .action(async (query: string | undefined, opts: {
      type?: string
      sort: string
      limit?: number
      pageAll?: boolean
      output: string
    }) => {
      const client = createNotionClient()

      const params: Record<string, unknown> = {}
      if (query) params['query'] = query
      if (opts.type) params['filter'] = { value: opts.type, property: 'object' }
      if (opts.sort === 'last_edited') {
        params['sort'] = { direction: 'descending', timestamp: 'last_edited_time' }
      }

      const results: unknown[] = []
      let cursor: string | undefined

      do {
        const body: Record<string, unknown> = { ...params }
        if (cursor) body['start_cursor'] = cursor
        if (opts.limit && !opts.pageAll) body['page_size'] = Math.min(opts.limit, 100)

        const res = await client.search(body as any) as any
        results.push(...res.results)
        cursor = res.has_more ? res.next_cursor : undefined

        if (!opts.pageAll && opts.limit && results.length >= opts.limit) break
        if (!opts.pageAll && !opts.limit) break
      } while (cursor)

      const limited = opts.limit ? results.slice(0, opts.limit) : results

      if (opts.output === 'ids') {
        printIds(limited as Array<{ id: string }>)
      } else {
        printJSON(limited)
      }
    })
}
