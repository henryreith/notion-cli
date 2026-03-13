import { describe, it, beforeAll, afterAll, expect } from 'vitest'
import { Client } from '@notionhq/client'

const SKIP = !process.env['NOTION_API_KEY'] || !process.env['NOTION_TEST_PARENT_ID']

describe.skipIf(SKIP)('KB Pipeline Integration', () => {
  let client: Client
  let dbId: string
  let pageId: string

  beforeAll(() => {
    client = new Client({ auth: process.env['NOTION_API_KEY']! })
  })

  afterAll(async () => {
    if (dbId) {
      try {
        await client.databases.update({ database_id: dbId, archived: true } as any)
      } catch {}
    }
  })

  it('1. auth: connects to Notion API', async () => {
    const me = await client.users.me({})
    expect(me.id).toBeDefined()
  })

  it('2. create database', async () => {
    const parentId = process.env['NOTION_TEST_PARENT_ID']!
    const db = await client.databases.create({
      parent: { page_id: parentId } as any,
      title: [{ type: 'text', text: { content: 'Test KB' } }] as any,
      properties: {
        Name: { title: {} },
        Status: { select: { options: [] } },
        Tags: { multi_select: { options: [] } },
      } as any,
    }) as any
    dbId = db.id
    expect(dbId).toBeDefined()
  })

  it('3. add select options', async () => {
    const db = await client.databases.update({
      database_id: dbId,
      properties: {
        Status: {
          select: { options: [{ name: 'Active' }, { name: 'Done' }] },
        } as any,
      },
    })
    expect(db).toBeDefined()
  })

  it('4. add first entry', async () => {
    const page = await client.pages.create({
      parent: { database_id: dbId },
      properties: {
        Name: { title: [{ type: 'text', text: { content: 'Entry 1' } }] },
        Status: { select: { name: 'Active' } },
      } as any,
    }) as any
    pageId = page.id
    expect(pageId).toBeDefined()
  })

  it('5. query all entries', async () => {
    const res = await client.databases.query({ database_id: dbId }) as any
    expect(res.results.length).toBeGreaterThan(0)
  })

  it('6. query with filter', async () => {
    const res = await client.databases.query({
      database_id: dbId,
      filter: { property: 'Status', select: { equals: 'Active' } } as any,
    }) as any
    expect(res.results.length).toBeGreaterThan(0)
  })

  it('7. page get', async () => {
    const page = await client.pages.retrieve({ page_id: pageId }) as any
    expect(page.id).toBe(pageId)
  })

  it('8. page append block', async () => {
    const res = await client.blocks.children.append({
      block_id: pageId,
      children: [{ type: 'paragraph', paragraph: { rich_text: [{ type: 'text', text: { content: 'Hello!' } }] } }] as any,
    })
    expect(res).toBeDefined()
  })

  it('9. comment on page', async () => {
    const comment = await client.comments.create({
      parent: { page_id: pageId },
      rich_text: [{ type: 'text', text: { content: 'Test comment' } }],
    }) as any
    expect(comment.id).toBeDefined()
  })

  it('10. search', async () => {
    const res = await client.search({ query: 'Entry 1' }) as any
    expect(res.results).toBeDefined()
  })

  it('11. user me', async () => {
    const me = await client.users.me({})
    expect(me.id).toBeDefined()
  })

  it('12. archive page', async () => {
    const updated = await client.pages.update({ page_id: pageId, archived: true }) as any
    expect(updated.archived).toBe(true)
  })
})
