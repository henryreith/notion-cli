export enum ExitCode {
  SUCCESS = 0,
  AUTH = 1,
  NOT_FOUND = 2,
  VALIDATION = 3,
  API = 4,
  EXISTS = 5,
  AMBIGUOUS = 6,
  DRY_RUN = 7,
}

export function die(code: ExitCode, message: string, extra?: Record<string, unknown>): never {
  const payload: Record<string, unknown> = { error: message }
  if (extra) Object.assign(payload, extra)
  process.stderr.write(JSON.stringify(payload) + '\n')
  process.exit(code)
}

export function handleApiError(err: unknown): never {
  const e = err as any
  if (e?.status === 403 || e?.code === 'restricted_resource') {
    die(ExitCode.AUTH, "Permission denied — this page/database hasn't been shared with your integration.", {
      hint: "In Notion: open the page → '...' menu → Connections → [your integration name]",
    })
  }
  if (e?.status === 404 || e?.code === 'object_not_found') {
    die(ExitCode.NOT_FOUND, e?.message ?? 'Resource not found')
  }
  die(ExitCode.API, e?.message ?? 'Notion API error')
}
