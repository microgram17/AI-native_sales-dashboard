
export function safeFilename(title: string): string {
  const cleaned = title
    .trim()
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^[.-]+|[.-]+$/g, '')

  return cleaned || 'export'
}

export function displayExportValue(value: unknown): string | number | boolean | null {
  if (value === undefined || value === null) return null

  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return value
  }

  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (
          typeof item === 'string' ||
          typeof item === 'number' ||
          typeof item === 'boolean'
        ) {
          return String(item)
        }

        return JSON.stringify(item)
      })
      .join(', ')
  }

  return JSON.stringify(value)
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.style.display = 'none'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}

export function downloadDataUrl(dataUrl: string, filename: string): void {
  const anchor = document.createElement('a')
  anchor.href = dataUrl
  anchor.download = filename
  anchor.style.display = 'none'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}
