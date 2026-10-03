const explanations: Record<string, string> = {
  'Bits per pixel': 'Average number of compressed bits used per image pixel.',
  'Compression ratio': 'Original file size divided by DFC2 file size.',
  PSNR: 'Pixel-level reconstruction quality compared with the original.',
}
export function MetricCard({ label, value, detail }: { label: string; value: string; detail?: string }) { return <div className="metric-card" title={explanations[label]}><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div> }
