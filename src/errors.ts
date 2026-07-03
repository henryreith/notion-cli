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

// Thrown by library code (coerce, client) for bad user input; the CLI
// entry point maps it to ExitCode.VALIDATION without exiting mid-library.
export class ValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ValidationError'
  }
}

export function die(code: ExitCode, message: string, extra?: Record<string, unknown>): never {
  const payload: Record<string, unknown> = { error: message }
  if (extra) Object.assign(payload, extra)
  process.stderr.write(JSON.stringify(payload) + '\n')
  process.exit(code)
}

export function handleApiError(err: unknown): never {
  if (err instanceof ValidationError) {
    die(ExitCode.VALIDATION, err.message)
  }
  const e = err as any
  if (e?.status === 401 || e?.code === 'unauthorized') {
    die(ExitCode.AUTH, 'Authentication failed — token is missing, invalid, or revoked.', {
      hint: 'Run: notion auth test',
    })
  }
  if (e?.status === 403 || e?.code === 'restricted_resource') {
    die(ExitCode.AUTH, "Permission denied — this page/database hasn't been shared with your integration.", {
      hint: "In Notion: open the page → '...' menu → Connections → [your integration name]",
    })
  }
  if (e?.status === 404 || e?.code === 'object_not_found') {
    die(ExitCode.NOT_FOUND, e?.message ?? 'Resource not found')
  }
  if (e?.status === 429 || e?.code === 'rate_limited') {
    die(ExitCode.API, 'Rate limited by the Notion API (3 req/sec).', {
      hint: 'Wait a moment and retry, or space out batch operations.',
    })
  }
  die(ExitCode.API, e?.message ?? 'Notion API error')
}
