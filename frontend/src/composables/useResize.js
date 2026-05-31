export function useResize(widthRef, { min = 0, max = Infinity } = {}) {
    return function startResize(e) {
        const startX = e.clientX
        // widthRef may be null when the element uses flex sizing by default —
        // fall back to the resized element's current rendered width so the
        // first drag continues from where it is instead of collapsing to min.
        const startW = widthRef.value ?? (e.currentTarget?.parentElement?.offsetWidth ?? 0)
        const onMove = e => {
            widthRef.value = Math.max(min, Math.min(max, startW + e.clientX - startX))
        }
        const onUp = () => {
            window.removeEventListener('mousemove', onMove)
            window.removeEventListener('mouseup', onUp)
        }
        window.addEventListener('mousemove', onMove)
        window.addEventListener('mouseup', onUp)
    }
}
