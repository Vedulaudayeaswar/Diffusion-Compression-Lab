import { useEffect, useState } from 'react'
import { websocketUrl } from '../api/client'
import type { Job } from '../types/api'

export function usePipelineSocket(jobId: string | null) {
  const [job, setJob] = useState<Partial<Job> | null>(null)
  const [socketError, setSocketError] = useState<string | null>(null)
  useEffect(() => {
    if (!jobId) return
    const socket = new WebSocket(websocketUrl(`/ws/pipeline/${jobId}`))
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as Partial<Job> & { type?: string }
      if (message.type === 'error') setSocketError(message.error ?? 'Pipeline connection failed')
      else setJob(message)
    }
    socket.onerror = () => setSocketError('Unable to connect to the live pipeline.')
    return () => socket.close()
  }, [jobId])
  return { job, socketError }
}
