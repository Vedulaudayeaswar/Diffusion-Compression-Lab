import { apiFetch } from './client'

export function getExperiments() { return apiFetch<Record<string, unknown>[]>('/api/experiments') }
