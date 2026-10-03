import type { CompressionOptions } from '../api/compression'

export function CompressionSettings({ value, onChange }: { value: CompressionOptions; onChange: (value: CompressionOptions) => void }) {
  const set = (key: keyof CompressionOptions, next: string) => onChange({ ...value, [key]: next })
  return <div className="settings-grid">
    <label>Mode<select value={value.mode} onChange={(e) => set('mode', e.target.value)}><option value="research">Research codec</option></select></label>
    <label>Lambda<span className="hint">Controls the rate-distortion tradeoff.</span><input type="number" min="0.1" step="0.1" value={value.lambda_value} onChange={(e) => set('lambda_value', e.target.value)} /></label>
    <label>Bitrate target <span className="hint">Optional target bitrate. The current codec uses learned quantization and entropy coding.</span><input type="number" min="0" step="0.01" placeholder="auto" value={value.bitrate} onChange={(e) => set('bitrate', e.target.value)} /></label>
    <label>Resolution<select value={value.resolution} onChange={(e) => set('resolution', e.target.value)}><option value="256">256 × 256</option><option value="128">128 × 128</option><option value="512">512 × 512</option></select></label>
    <label>Reconstruction method<div className="setting-static"><strong>One-step diffusion</strong><span>Validated one-step SD2.1 latent diffusion reconstruction.</span></div></label>
  </div>
}
