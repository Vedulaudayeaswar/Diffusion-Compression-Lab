import type { Metrics } from '../types/api'

export interface ExperimentPoint { lambda: number; metrics: Metrics; id?: string }

export function RateDistortionChart({ points }: { points: ExperimentPoint[] }) {
  if (!points.length) return <div className="chart-empty">Run the Lambda sweep to generate measured rate-distortion points.</div>
  const width = 680, height = 270, left = 58, right = 22, top = 20, bottom = 42
  const xs = points.map((point) => point.metrics.bpp), ys = points.map((point) => point.metrics.psnr ?? 0)
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys)
  const x = (value: number) => left + ((value - minX) / Math.max(maxX - minX, 0.001)) * (width - left - right)
  const y = (value: number) => height - bottom - ((value - minY) / Math.max(maxY - minY, 0.1)) * (height - top - bottom)
  const ordered = [...points].sort((a, b) => a.metrics.bpp - b.metrics.bpp)
  return <div className="chart-wrap"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Measured rate-distortion chart">
    <line x1={left} x2={left} y1={top} y2={height - bottom} className="chart-axis" /><line x1={left} x2={width - right} y1={height - bottom} y2={height - bottom} className="chart-axis" />
    <polyline points={ordered.map((point) => `${x(point.metrics.bpp)},${y(point.metrics.psnr ?? 0)}`).join(' ')} className="chart-line" />
    {points.map((point) => <g key={point.id ?? point.lambda}><circle cx={x(point.metrics.bpp)} cy={y(point.metrics.psnr ?? 0)} r="6" className="chart-point"><title>{`Lambda ${point.lambda} - ${point.metrics.bpp.toFixed(3)} BPP - ${(point.metrics.psnr ?? 0).toFixed(2)} dB - ${point.metrics.compression_ratio.toFixed(2)}x`}</title></circle></g>)}
    <text x={width / 2} y={height - 10} className="chart-label">BPP</text><text x="15" y={height / 2} transform={`rotate(-90 15 ${height / 2})`} className="chart-label">PSNR (dB)</text>
  </svg><div className="chart-footnote">Measured points from completed backend experiments - hover a point for Lambda, BPP, PSNR, and ratio.</div></div>
}
