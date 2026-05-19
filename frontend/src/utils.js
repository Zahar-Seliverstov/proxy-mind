export const fmtPath = (path) => path?.replace(/^\/home\/[^/]+/, '~') ?? ''
