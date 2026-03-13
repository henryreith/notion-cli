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
