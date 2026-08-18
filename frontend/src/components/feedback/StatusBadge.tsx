import { oncelikSeviyesiMetni, arizaTipiMetni } from '../../types/tahminler'

interface StatusBadgeProps {
  oncelik?: 'KRITIK' | 'YUKSEK' | 'ORTA' | 'DUSUK' | string | null
  arizaTipi?: string | null
  metin?: string
  varyant?: 'basarili' | 'uyari' | 'kritik' | 'bilgi' | 'notr'
}

export function StatusBadge({ oncelik, arizaTipi, metin, varyant }: StatusBadgeProps) {
  if (oncelik) {
    const baslik = oncelikSeviyesiMetni(oncelik)
    let cls = 'rozet'
    if (oncelik === 'KRITIK' || oncelik === 'YUKSEK') cls = 'rozet'
    else if (oncelik === 'ORTA') cls = 'rozet uyari'
    else if (oncelik === 'DUSUK') cls = 'rozet basarili'
    return <span className={cls}>{baslik}</span>
  }

  if (arizaTipi) {
    const baslik = arizaTipiMetni(arizaTipi)
    const isTWF = arizaTipi === 'TWF'
    return (
      <span className={isTWF ? 'rozet uyari' : 'rozet bilgi'}>
        {baslik}
      </span>
    )
  }

  const cls = varyant ? (varyant === 'kritik' ? 'rozet' : `rozet ${varyant}`) : 'rozet notr'
  return <span className={cls}>{metin ?? 'Belirtilmedi'}</span>
}
