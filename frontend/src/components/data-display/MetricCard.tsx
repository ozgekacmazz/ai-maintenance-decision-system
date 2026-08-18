import type { ReactNode } from 'react'

interface MetricCardProps {
  baslik: string
  deger: string | number
  aciklama?: string
  ikon?: ReactNode
  varyant?: 'varsayilan' | 'kritik' | 'uyari' | 'basarili'
}

export function MetricCard({ baslik, deger, aciklama, ikon, varyant = 'varsayilan' }: MetricCardProps) {
  let ikonCls = 'metrik-ikon-kutu'
  if (varyant === 'kritik') ikonCls = 'metrik-ikon-kutu kritik'
  else if (varyant === 'uyari') ikonCls = 'metrik-ikon-kutu uyari'
  else if (varyant === 'basarili') ikonCls = 'metrik-ikon-kutu basarili'

  return (
    <div className="metrik-kart">
      <div className="metrik-icerik">
        <span className="metrik-etiket">{baslik}</span>
        <span className="metrik-deger">{deger}</span>
        {aciklama && <span className="metrik-aciklama">{aciklama}</span>}
      </div>
      {ikon && <div className={ikonCls}>{ikon}</div>}
    </div>
  )
}
