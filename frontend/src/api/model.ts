import { apiFetch } from './client'
import type { ModelStatus } from '../types/api'

export function getModelStatus() { return apiFetch<ModelStatus>('/api/model/status') }
export function getSystemStatus() { return apiFetch<{ status: string; device: string; gpu: unknown }>('/api/system/status') }
