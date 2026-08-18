import type { ReactNode } from 'react'

interface EmptyStateProps {
  baslik: string
  aciklama: string
  ikon?: ReactNode
  action?: ReactNode
}

export function EmptyState({ baslik, aciklama, ikon, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      {ikon && <div className="empty-state-ikon">{ikon}</div>}
      <h3 className="empty-state-baslik">{baslik}</h3>
      <p className="empty-state-metin">{aciklama}</p>
      {action && <div className="empty-state-butonu">{action}</div>}
    </div>
  )
}
