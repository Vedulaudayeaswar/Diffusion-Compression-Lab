import { apiFetch, apiUrl } from './client'
import type { Dfc2Metadata } from '../types/api'

export async function inspectDfc2(file: File) {
  const form = new FormData()
  form.append('file', file)
  return apiFetch<Dfc2Metadata>('/api/decompress/inspect', { method: 'POST', body: form })
}

export async function decompressDfc2(file: File) {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(apiUrl('/api/decompress'), { method: 'POST', body: form })
  if (!response.ok) throw new Error((await response.json()).detail ?? 'Decode failed')
  return { blob: await response.blob(), metadata: JSON.parse(response.headers.get('X-DFC2-Metadata') ?? '{}') }
}
