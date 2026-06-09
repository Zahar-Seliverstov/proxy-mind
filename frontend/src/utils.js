export const fmtPath = (path) => path?.replace(/^\/home\/[^/]+/, '~') ?? ''

export const dirName = (path) => path?.replace(/\/+$/, '').split('/').pop() || '~'
