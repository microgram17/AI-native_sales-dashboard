
import { downloadDataUrl, safeFilename } from './exportUtils'

function isTransparent(color: string): boolean {
  return (
    !color ||
    color === 'transparent' ||
    color === 'rgba(0, 0, 0, 0)' ||
    color === 'rgba(0,0,0,0)'
  )
}

function resolveBackgroundColor(node: HTMLElement): string {
  let current: HTMLElement | null = node

  while (current) {
    const color = window.getComputedStyle(current).backgroundColor
    if (!isTransparent(color)) return color
    current = current.parentElement
  }

  const rootBackground = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue('--bg')
    .trim()

  return rootBackground || '#ffffff'
}

function includeInExport(node: HTMLElement): boolean {
  return node.dataset?.exportControl !== 'true'
}

export async function exportNodeToPng(
  node: HTMLElement,
  title: string,
): Promise<void> {
  const { toPng } = await import('html-to-image')

  const width = Math.max(node.scrollWidth, node.clientWidth, 1)
  const height = Math.max(node.scrollHeight, node.clientHeight, 1)

  // Keep output crisp while avoiding oversized browser canvases for large tables.
  const largestDimension = Math.max(width, height)
  const pixelRatio = largestDimension > 5000 ? 1 : 2

  const dataUrl = await toPng(node, {
    backgroundColor: resolveBackgroundColor(node),
    cacheBust: true,
    pixelRatio,
    width,
    height,
    filter: includeInExport,
  })

  downloadDataUrl(dataUrl, `${safeFilename(title)}.png`)
}
