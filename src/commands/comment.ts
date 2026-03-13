import { Command } from 'commander'
import { createNotionClient, normaliseId, collectPaginatedAPI } from '../client.js'
import { printJSON, printIds } from '../output.js'

export function registerComment(program: Command): void {
  const comment = program.command('comment').description('Comment commands')

  // comment add
  comment.command('add <page-id> <text>')
    .description('Add a comment to a page')
    .action(async (pageId: string, text: string) => {
      const client = createNotionClient()
      const result = await client.comments.create({
        parent: { page_id: normaliseId(pageId) },
        rich_text: [{ type: 'text', text: { content: text } }],
      }) as any
      printJSON(result)
    })

  // comment list
  comment.command('list <page-id>')
    .description('List comments on a page')
    .option('--output <format>', 'Output format: json|ids', 'json')
    .action(async (pageId: string, opts: { output: string }) => {
      const client = createNotionClient()
      const results = await collectPaginatedAPI(client.comments.list, {
        block_id: normaliseId(pageId),
      })

      if (opts.output === 'ids') {
        printIds(results as Array<{ id: string }>)
      } else {
        printJSON(results)
      }
    })
}
