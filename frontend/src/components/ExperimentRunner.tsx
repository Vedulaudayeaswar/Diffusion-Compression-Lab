import { useState } from 'react'
import { FlaskConical, LoaderCircle, Play } from 'lucide-react'
import { compressImage, getJob, type CompressionOptions } from '../api/compression'
import type { Job } from '../types/api'
import { RateDistortionChart, type ExperimentPoint } from './RateDistortionChart'

const LAMBDAS = [1, 5, 7, 10, 20]
const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

export function ExperimentRunner({ file, options, online }: { file: File | null; options: CompressionOptions; online: boolean }) {
  const [running, setRunning] = useState(false)
  const [current, setCurrent] = useState<number | null>(null)
  const [points, setPoints] = useState<ExperimentPoint[]>([])
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    if (!file || running) return
    setRunning(true)
    setError(null)
    setPoints([])
    try {
      const measured: ExperimentPoint[] = []
      for (const lambda of LAMBDAS) {
        setCurrent(lambda)
        const { job_id } = await compressImage(file, { ...options, lambda_value: String(lambda), bitrate: options.bitrate })
        let job: Job
        do {
          await wait(800)
          job = await getJob(job_id)
        } while (job.status === 'queued' || job.status === 'running')
        if (job.status !== 'completed' || !job.metrics) throw new Error(job.error ?? `Lambda ${lambda} failed`)
        measured.push({ lambda, metrics: job.metrics, id: job.id })
        setPoints([...measured])
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Experiment failed')
    } finally {
      setCurrent(null)
      setRunning(false)
    }
  }

  return <section className="card experiment-card">
    <div className="section-heading"><div><span className="eyebrow">EXPERIMENT MODE</span><h2>Rate-distortion sweep</h2><p className="section-subtitle">Run the same image through the real codec at Lambda = 1, 5, 7, 10, and 20.</p></div><FlaskConical size={18} className="muted" /></div>
    <div className="lambda-pills">{LAMBDAS.map((lambda) => <span className={current === lambda ? 'active' : ''} key={lambda}>Lambda {lambda}</span>)}</div>
    <button className="secondary-button experiment-button" disabled={!file || !online || running} onClick={run}>{running ? <><LoaderCircle className="spin" size={17} /> RUNNING Lambda {current}</> : <><Play size={17} /> RUN REAL EXPERIMENT</>}</button>
    {error && <p className="error-text">{error}</p>}
    <RateDistortionChart points={points} />
    {points.length > 0 && <div className="experiment-table-wrap"><table><thead><tr><th>Lambda</th><th>BPP</th><th>Ratio</th><th>PSNR</th><th>DFC2 size</th></tr></thead><tbody>{points.map((point) => <tr key={point.id ?? point.lambda}><td>Lambda {point.lambda}</td><td>{point.metrics.bpp.toFixed(3)}</td><td>{point.metrics.compression_ratio.toFixed(2)}x</td><td>{point.metrics.psnr == null ? '-' : `${point.metrics.psnr.toFixed(2)} dB`}</td><td>{(point.metrics.compressed_file_size / 1024).toFixed(2)} KB</td></tr>)}</tbody></table></div>}
  </section>
}
