interface Props { label: string; tone?: 'ready' | 'muted' | 'error' | 'active' }
export function StatusBadge({ label, tone = 'muted' }: Props) {
  return <span className={`status-badge ${tone}`}><span className="status-dot" />{label}</span>
}
