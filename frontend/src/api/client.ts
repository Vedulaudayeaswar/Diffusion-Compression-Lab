const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    let message = response.statusText
    try {
      const body = await response.json()
      const detail = body.detail
      message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((item) => item?.msg ?? JSON.stringify(item)).join('; ') : message
    } catch { /* plain response */ }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}

export function websocketUrl(path: string): string {
  const base = API_BASE.replace(/^http/, 'ws')
  return `${base}${path}`
}
