const WS_URL      = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
const RECONNECT_MS = 2000

const _handlers = new Map()
let   _ws        = null
let   _reconnTimer = null

function _emit(type, data) {
    _handlers.get(type)?.forEach(fn => fn(data))
}

function _connect() {
    if (_ws && (_ws.readyState === WebSocket.CONNECTING || _ws.readyState === WebSocket.OPEN)) return

    clearTimeout(_reconnTimer)
    _reconnTimer = null

    _ws = new WebSocket(WS_URL)

    _ws.onopen    = () => { clearTimeout(_reconnTimer); _emit('connect', {}) }
    _ws.onmessage = (e) => {
        let msg
        try { msg = JSON.parse(e.data) } catch { return }
        _emit(msg.type, msg)
    }
    _ws.onclose   = () => { _emit('disconnect', {}); _reconnTimer = setTimeout(_connect, RECONNECT_MS) }
    _ws.onerror   = () => { _ws.close() }
}

function on(type, fn) {
    if (!_handlers.has(type)) _handlers.set(type, new Set())
    _handlers.get(type).add(fn)
    return () => _handlers.get(type)?.delete(fn)
}

export function useWebSocket() {
    return { on, start: _connect }
}
