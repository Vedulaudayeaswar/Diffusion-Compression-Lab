import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Download, LoaderCircle, LockKeyhole, Sparkles } from 'lucide-react'
import { compressImage, getJob, type CompressionOptions } from '../api/compression'
import { apiUrl } from '../api/client'
import { Header } from '../components/Header'
import { ImageComparison } from '../components/ImageComparison'
import { MetricCard } from '../components/MetricCard'
import { PipelineVisualizer } from '../components/PipelineVisualizer'
import { CompressionSettings } from '../components/CompressionSettings'
import { ExperimentRunner } from '../components/ExperimentRunner'
import { UploadZone } from '../components/UploadZone'
import { StatusBadge } from '../components/StatusBadge'
import { usePipelineSocket } from '../hooks/usePipelineSocket'
import type { Job } from '../types/api'

const defaults: CompressionOptions = { mode: 'research', bitrate: '', lambda_value: '5', steps: '1', resolution: '256', reconstruction_mode: 'one_step', refinement_alpha: '0' }
const format = (v: number | null | undefined, suffix = '') => v == null || Number.isNaN(v) ? '-' : `${typeof v === 'number' && v % 1 !== 0 ? v.toFixed(2) : v}${suffix}`

export function Compress({ online }: { online: boolean }) {
  const [file, setFile] = useState<File | null>(null)
  const [options, setOptions] = useState(defaults)
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState<string | null>(null)
  const socket = usePipelineSocket(jobId)
  const preview = useMemo(() => file ? URL.createObjectURL(file) : null, [file])
  const live = (socket.job ?? job) as Partial<Job> | null

  const submit = async () => {
    if (!file) return
    setError(null); setJob(null); setJobId(null)
    try { const result = await compressImage(file, options); setJobId(result.job_id) } catch (e) { setError(e instanceof Error ? e.message : 'Compression failed') }
  }
  useEffect(() => {
    if (jobId && live?.status === 'completed' && !job) void getJob(jobId).then(setJob).catch((e) => setError(e instanceof Error ? e.message : 'Unable to load results'))
  }, [jobId, live?.status, job])
  const done = job?.status === 'completed' || live?.status === 'completed'
  return <><Header online={online} /><main className="page-shell">
    <section className="hero"><div><StatusBadge label="RESEARCH PROTOTYPE" tone="active" /><h1>Diffusion<br /><span>Compression</span> Lab</h1><p>Learned lossy image compression with foundation diffusion models.</p><div className="hero-note"><Sparkles size={15} />Compact DFC2 bitstreams - SD 2.1 latent reconstruction</div><p className="research-disclaimer">Research prototype inspired by "Lossy Image Compression with Foundation Diffusion Models". The current implementation uses one-step SD2.1 latent diffusion reconstruction and a factorized Gaussian entropy model.</p></div><div className="hero-orbit"><div className="orbit-ring ring-a" /><div className="orbit-ring ring-b" /><span>DFC2</span></div></section>
    <div className="workspace-grid"><section className="card upload-card"><div className="section-heading"><div><span className="eyebrow">01 / INPUT</span><h2>Source image</h2></div><span className="muted">256 x 256 default</span></div><UploadZone file={file} onChange={setFile} />{preview && <div className="source-preview"><img src={preview} /><div><strong>{file?.name}</strong><span>Ready for preprocessing</span></div></div>}</section>
      <section className="card settings-card"><div className="section-heading"><div><span className="eyebrow">02 / CONTROL</span><h2>Compression settings</h2></div><LockKeyhole size={16} className="muted" /></div><CompressionSettings value={options} onChange={setOptions} /><button className="primary-button" disabled={!file || !online || live?.status === 'running' || live?.status === 'queued'} onClick={submit}>{live?.status === 'running' || live?.status === 'queued' ? <><LoaderCircle className="spin" size={18} /> PROCESSING</> : <>COMPRESS IMAGE <ArrowRight size={18} /></>}</button>{error && <p className="error-text">{error}</p>}</section></div>
    <ExperimentRunner file={file} options={options} online={online} />
    {jobId && <section className="card pipeline-card"><div className="section-heading"><div><span className="eyebrow">LIVE PIPELINE</span><h2>{live?.stage?.replace(/_/g, ' ') || 'Connecting...'}</h2></div><strong className="progress-number">{Math.round(live?.progress ?? 0)}%</strong></div><PipelineVisualizer stage={live?.stage ?? ''} progress={live?.progress ?? 0} /><p className="pipeline-caption">Progress is streamed from the backend job - no client-side simulation</p>{socket.socketError && <p className="error-text">{socket.socketError}</p>}</section>}
    {done && job?.metrics && <section className="results-section"><div className="section-heading"><div><span className="eyebrow">RESULTS / {job.id.slice(0, 8)}</span><h2>Reconstruction report</h2></div><StatusBadge label="COMPLETE" tone="ready" /></div><ImageComparison original={preview} reconstruction={job.output ? apiUrl(job.output.reconstruction_url) : null} /><div className="metrics-grid"><MetricCard label="Bits per pixel" value={format(job.metrics.bpp)} /><MetricCard label="Compression ratio" value={`${format(job.metrics.compression_ratio)}x`} /><MetricCard label="PSNR" value={format(job.metrics.psnr, ' dB')} /><MetricCard label="SSIM" value={format(job.metrics.ssim)} /><MetricCard label="Original size" value={`${format(job.metrics.original_file_size / 1024)} KB`} /><MetricCard label="DFC2 size" value={`${format(job.metrics.compressed_file_size / 1024)} KB`} /><MetricCard label="Encode time" value={`${format(job.metrics.encode_time_seconds)} s`} /><MetricCard label="Decode time" value={format(job.metrics.decode_time_seconds, ' s')} /></div><div className="download-row"><a className="secondary-button" href={job.output ? apiUrl(job.output.dfc2_url) : '#'} download><Download size={17} /> DOWNLOAD .DFC2</a><a className="secondary-button" href={job.output ? apiUrl(job.output.reconstruction_url) : '#'} download><Download size={17} /> DOWNLOAD RECONSTRUCTION</a></div></section>}
  </main></>
}
