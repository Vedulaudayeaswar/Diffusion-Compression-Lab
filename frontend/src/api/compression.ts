import { apiFetch } from './client'
import type { Job } from '../types/api'

export interface CompressionOptions {
  mode: string
  bitrate: string
  lambda_value: string
  steps: string
  resolution: string
  reconstruction_mode: string
  refinement_alpha: string
}

export async function compressImage(file: File, options: CompressionOptions) {
  const form = new FormData()
  form.append('image', file)
  Object.entries(options).forEach(([key, value]) => {
    if (key === 'bitrate' && !value.trim()) return
    form.append(key, value)
  })
  return apiFetch<{ job_id: string }>('/api/compress', { method: 'POST', body: form })
}

export function getJob(jobId: string) {
  return apiFetch<Job>(`/api/jobs/${jobId}`)
}
