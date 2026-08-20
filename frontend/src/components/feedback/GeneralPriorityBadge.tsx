import { StatusBadge } from './StatusBadge'
import type { GenelOncelik, IsEmriOncelik } from '../../types/isEmirleri'

interface GeneralPriorityBadgeProps {
  genelOncelik: GenelOncelik | null
  legacyOncelik?: IsEmriOncelik | string | null
}

const styles: Record<GenelOncelik, { background: string; color: string; border: string }> = {
  1: { background: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: 'var(--border-color)' },
  2: { background: 'var(--status-success-bg)', color: 'var(--status-success-text)', border: 'var(--status-success-border)' },
  3: { background: 'var(--status-warning-bg)', color: 'var(--status-warning-text)', border: 'var(--status-warning-border)' },
  4: { background: 'var(--status-critical-bg)', color: 'var(--status-critical-text)', border: 'var(--status-critical-border)' },
  5: { background: 'var(--status-critical-bg)', color: 'var(--status-critical-text)', border: 'var(--status-critical-border)' },
}

export function GeneralPriorityBadge({ genelOncelik, legacyOncelik }: GeneralPriorityBadgeProps) {
  if (genelOncelik === null) {
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
        <StatusBadge oncelik={legacyOncelik} />
        <small style={{ color: 'var(--text-muted)' }}>Legacy öncelik</small>
      </span>
    )
  }

  const style = styles[genelOncelik]
  return (
    <span
      className="rozet"
      title="Risk × makine kritikliÄŸi × stok katsayÄ±sÄ±"
      style={{ background: style.background, color: style.color, border: `1px solid ${style.border}` }}
    >
      Öncelik {genelOncelik}/5
    </span>
  )
}
