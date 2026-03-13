import { Command } from 'commander'
import { createNotionClient, normaliseId, collectPaginatedAPI } from '../client.js'
import { printJSON, printIds } from '../output.js'
import { readDataInput } from '../coerce.js'

export function registerBlock(program: Command): void {
  const block = program.command('block').description('Block commands')

  // block list
  block.command('list <block-id>')
    .description('List children of a block/page')
    .option('--output <format>', 'Output format: json|ids', 'json')
    .action(async (blockId: string, opts: { output: string }) => {
      const client = createNotionClient()
      const id = normaliseId(blockId)
      const results = await collectPaginatedAPI(client.blocks.children.list, { block_id: id })

      if (opts.output === 'ids') {
        printIds(results as Array<{ id: string }>)
      } else {
        printJSON(results)
      }
    })

  // block get
  block.command('get <block-id>')
    .description('Retrieve a block')
    .action(async (blockId: string) => {
      const client = createNotionClient()
      const result = await client.blocks.retrieve({ block_id: normaliseId(blockId) })
      printJSON(result)
    })

  // block append
  block.command('append <block-id>')
    .description('Append a new block')
    .requiredOption('--type <type>', 'Block type (e.g. paragraph, heading_1, bulleted_list_item)')
    .requiredOption('--text <text>', 'Text content')
    .action(async (blockId: string, opts: { type: string; text: string }) => {
      const client = createNotionClient()
      const id = normaliseId(blockId)

      const richText = [{ type: 'text', text: { content: opts.text } }]
      const blockBody: Record<string, unknown> = {
        object: 'block',
        type: opts.type,
        [opts.type]: { rich_text: richText },
      }

      const result = await client.blocks.children.append({
        block_id: id,
        children: [blockBody as any],
      })
      printJSON(result)
    })

  // block update
  block.command('update <block-id>')
    .description('Update a block')
    .requiredOption('--data <input>', 'JSON block body: inline, @file, or -')
    .action(async (blockId: string, opts: { data: string }) => {
      const client = createNotionClient()
      const id = normaliseId(blockId)
      const body = readDataInput(opts.data) as Record<string, unknown>
      const result = await client.blocks.update({ block_id: id, ...body } as any)
      printJSON(result)
    })

  // block delete
  block.command('delete <block-id>')
    .description('Delete a block')
    .action(async (blockId: string) => {
      const client = createNotionClient()
      const result = await client.blocks.delete({ block_id: normaliseId(blockId) })
      printJSON({ status: 'deleted', id: (result as any).id })
    })
}
