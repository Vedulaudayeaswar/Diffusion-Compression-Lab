import type { CSSProperties } from 'react'

const nodes = ['01 IMAGE', '02 SD2.1 VAE', '03 4-CHANNEL LATENT', '04 ADAPTIVE QUANTIZATION', '05 ENTROPY MODEL', '06 ARITHMETIC CODING', '07 DFC2', '08 DIFFUSION', '09 SD2.1 VAE', '10 RECONSTRUCTION']
const stages: Record<string, number> = { preprocessing: 0, vae_encoding: 1, parameter_estimation: 2, quantization: 3, entropy_coding: 4, entropy_decoding: 6, dfc2_generation: 6, diffusion: 7, vae_decoding: 8, completed: 9 }
export function PipelineVisualizer({ stage, progress }: { stage: string; progress: number }) {
  const active = stages[stage] ?? -1
  void progress
  return <div className="pipeline"><div className="pipeline-track" style={{ '--progress': `${Math.max(0, Math.min(active, 9)) / 9 * 100}%` } as CSSProperties} />{nodes.map((node, i) => <div className={`pipeline-node ${i < active ? 'completed' : i === active ? 'active' : ''}`} key={`${node}-${i}`}><div className="node-dot">{i < active ? '✓' : String(i + 1).padStart(2, '0')}</div><span>{node}</span></div>)}</div>
}
