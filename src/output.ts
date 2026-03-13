import Table from 'cli-table3'

export function printJSON(data: unknown): void {
  process.stdout.write(JSON.stringify(data, null, 2) + '\n')
}

export function printIds(items: Array<{ id: string }>): void {
  for (const item of items) {
    process.stdout.write(normaliseOutputId(item.id) + '\n')
  }
}

export function printId(id: string): void {
  process.stdout.write(normaliseOutputId(id) + '\n')
}

function normaliseOutputId(id: string): string {
  return id.replace(/-/g, '')
}

export function printTable(
  rows: Array<Record<string, string>>,
  columns: string[]
): void {
  const table = new Table({ head: columns })
  for (const row of rows) {
    table.push(columns.map(col => row[col] ?? ''))
  }
  process.stdout.write(table.toString() + '\n')
}
