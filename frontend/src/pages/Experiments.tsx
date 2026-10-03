import { useEffect, useMemo, useState } from 'react'
import { getExperiments } from '../api/experiments'
import { Header } from '../components/Header'
import { RateDistortionChart, type ExperimentPoint } from '../components/RateDistortionChart'
import { StatusBadge } from '../components/StatusBadge'

export function Experiments({ online }: { online: boolean }) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  useEffect(() => { getExperiments().then(setRows).catch(() => setRows([])) }, [])
  const points = useMemo<ExperimentPoint[]>(() => rows.filter((row) => row.lambda != null).map((row) => ({ lambda: Number(row.lambda), id: String(row.id), metrics: row as never })), [rows])
  return <><Header online={online} /><main className="page-shell"><section className="page-intro"><StatusBadge label="EXPERIMENTS" tone="active" /><h1>Research runs</h1><p>Actual compression jobs persisted by the backend, with measured rate-distortion points only.</p></section><section className="card table-card">{rows.length ? <div className="table-wrap"><table><thead><tr><th>Experiment</th><th>Image</th><th>Lambda</th><th>BPP</th><th>PSNR</th><th>SSIM</th><th>Ratio</th><th>Runtime</th></tr></thead><tbody>{rows.map((row) => <tr key={String(row.id)}><td><strong>{String(row.id).slice(0, 10)}</strong><span>{new Date(Number(row.created_at) * 1000).toLocaleString()}</span></td><td>{String(row.image_name ?? '-')}</td><td>{row.lambda == null ? '-' : `Lambda ${row.lambda}`}</td><td>{Number(row.bpp).toFixed(3)}</td><td>{row.psnr == null ? '-' : `${Number(row.psnr).toFixed(2)} dB`}</td><td>{row.ssim == null ? '-' : Number(row.ssim).toFixed(3)}</td><td>{Number(row.compression_ratio).toFixed(2)}x</td><td>{Number(row.encode_time_seconds).toFixed(1)} s / {Number(row.decode_time_seconds).toFixed(1)} s</td></tr>)}</tbody></table></div> : <div className="empty-state"><div className="empty-icon">0</div><h2>No experiments yet</h2><p>Run the real Lambda sweep from the Compress page.</p></div>}</section>{points.length > 0 && <section className="card chart-card"><div className="section-heading"><div><span className="eyebrow">MEASURED DATA</span><h2>Rate-distortion curve</h2></div><span className="muted">{points.length} backend points</span></div><RateDistortionChart points={points} /></section>}</main></>
}
