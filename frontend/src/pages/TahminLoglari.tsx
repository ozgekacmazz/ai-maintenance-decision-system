import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, FileText, Filter } from 'lucide-react'
import { tahminLoglariniGetir } from '../api/tahminler'
import type { GenelOncelik } from '../types/isEmirleri'
import type { TahminKararDurumu, TahminLoglariParametreleri, TahminLogu } from '../types/tahminler'
import { ApiHatasi } from '../types/apiHata'
import { GeneralPriorityBadge } from '../components/feedback/GeneralPriorityBadge'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { EmptyState } from '../components/feedback/EmptyState'
import { ErrorState } from '../components/feedback/ErrorState'

const kararMetni: Record<TahminKararDurumu, string> = {
  BEKLIYOR: 'Bekliyor', ONAYLANDI: 'Onaylandı', REDDEDILDI: 'Reddedildi', TUTARSIZ: 'Tutarsız',
}

function kararOzeti(log: TahminLogu) {
  if (log.karar_durumu === 'TUTARSIZ') return 'Tutarsız karar verisi: hem iş emri hem red kaydı var.'
  if (log.karar_durumu === 'REDDEDILDI') return log.karar_nedeni || 'Red nedeni belirtilmedi'
  return null
}

export function TahminLoglari() {
  const [veri, setVeri] = useState<{ count: number; results: TahminLogu[] }>({ count: 0, results: [] })
  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [sayfa, setSayfa] = useState(1)
  const [kararDurumu, setKararDurumu] = useState<TahminKararDurumu | ''>('')
  const [kaynak, setKaynak] = useState<TahminLogu['kaynak'] | ''>('')
  const [oncelik, setOncelik] = useState<GenelOncelik | ''>('')
  const [baslangic, setBaslangic] = useState('')
  const [bitis, setBitis] = useState('')
  const [sirala, setSirala] = useState<TahminLoglariParametreleri['sirala']>('-olcum_zamani')
  const [yenileme, setYenileme] = useState(0)

  useEffect(() => {
    let iptal = false
    tahminLoglariniGetir({
      karar_durumu: kararDurumu || undefined,
      kaynak: kaynak || undefined,
      genel_oncelik: oncelik || undefined,
      baslangic: baslangic || undefined,
      bitis: bitis || undefined,
      sirala,
      sayfa,
      sayfa_boyutu: 10,
    }).then((yanit) => {
      if (!iptal) setVeri({ count: yanit.count, results: yanit.results })
    }).catch((error: unknown) => {
      if (iptal) return
      if (error instanceof ApiHatasi) {
        setHata(error.status === 403 ? 'Bu bölüme erişim yetkiniz yok.' : error.message)
        setTraceId(error.traceId ?? null)
      } else setHata('Tahmin logları yüklenirken bir hata oluştu.')
    }).finally(() => { if (!iptal) setYukleniyor(false) })
    return () => { iptal = true }
  }, [kararDurumu, kaynak, oncelik, baslangic, bitis, sirala, sayfa, yenileme])

  const filtreDegistir = (islem: () => void) => { setSayfa(1); islem() }
  const temizle = () => {
    setSayfa(1); setKararDurumu(''); setKaynak(''); setOncelik(''); setBaslangic(''); setBitis(''); setSirala('-olcum_zamani')
  }

  return <div className="sayfa-konteyner">
    <div className="sayfa-baslik-alani"><div><h1 className="sayfa-basligi">Tahmin Logları</h1><p className="sayfa-alt-basligi">Tahminlerin risk, öncelik ve kullanıcı kararlarını denetleyin.</p></div></div>
    <div className="dashboard-panel">
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 16 }}><Filter size={18}/><h3 style={{ margin: 0 }}>Log Filtreleri</h3></div>
      <div className="form-grid-3">
        <div><label htmlFor="log-karar">Karar durumu</label><select id="log-karar" value={kararDurumu} onChange={(e) => filtreDegistir(() => setKararDurumu(e.target.value as TahminKararDurumu | ''))}><option value="">Tümü</option>{Object.entries(kararMetni).map(([k,v]) => <option key={k} value={k}>{v}</option>)}</select></div>
        <div><label htmlFor="log-kaynak">Kaynak</label><select id="log-kaynak" value={kaynak} onChange={(e) => filtreDegistir(() => setKaynak(e.target.value as TahminLogu['kaynak'] | ''))}><option value="">Tümü</option><option value="MANUEL">Manuel</option><option value="ENTEGRASYON">Entegrasyon</option><option value="REPLAY">Replay</option></select></div>
        <div><label htmlFor="log-oncelik">Genel öncelik</label><select id="log-oncelik" value={oncelik} onChange={(e) => filtreDegistir(() => setOncelik(e.target.value ? Number(e.target.value) as GenelOncelik : ''))}><option value="">Tümü</option>{[5,4,3,2,1].map(v => <option key={v} value={v}>Öncelik {v}/5</option>)}</select></div>
        <div><label htmlFor="log-baslangic">Başlangıç</label><input id="log-baslangic" type="date" value={baslangic} onChange={(e) => filtreDegistir(() => setBaslangic(e.target.value))}/></div>
        <div><label htmlFor="log-bitis">Bitiş</label><input id="log-bitis" type="date" value={bitis} onChange={(e) => filtreDegistir(() => setBitis(e.target.value))}/></div>
        <div><label htmlFor="log-sirala">Sıralama</label><select id="log-sirala" value={sirala} onChange={(e) => filtreDegistir(() => setSirala(e.target.value as TahminLoglariParametreleri['sirala']))}><option value="-olcum_zamani">En yeni tahmin</option><option value="-risk_orani">En yüksek risk</option><option value="-genel_oncelik">En yüksek öncelik</option><option value="-karar_zamani">En yeni karar</option></select></div>
      </div>
      <button type="button" className="buton-sekonder" style={{ marginTop: 16 }} onClick={temizle}>Filtreleri temizle</button>
    </div>
    {yukleniyor ? <LoadingSkeleton adet={5}/> : hata ? <ErrorState mesaj={hata} traceId={traceId} onRetry={() => setYenileme(v => v + 1)}/> : veri.results.length === 0 ? <EmptyState baslik="Tahmin Logu Bulunamadı" aciklama="Filtrelere uygun tahmin logu bulunamadı." ikon={<FileText size={32}/>}/> :
      <div className="dashboard-panel" style={{ padding: 0, overflow: 'hidden' }}><div style={{ overflowX: 'auto' }}><table className="veri-tablosu"><thead><tr><th>Tarih</th><th>Makine</th><th>Kaynak</th><th>Risk</th><th>Öncelik</th><th>Karar</th><th>Karar Veren</th><th>Karar Zamanı</th><th>İş Emri / Red Nedeni</th><th>Detay</th></tr></thead><tbody>{veri.results.map(log => {
        const ozet = kararOzeti(log)
        return <tr key={log.id}><td>{new Date(log.olcum_zamani).toLocaleString('tr-TR')}</td><td><strong>{log.makine.ad}</strong><div className="alt-bilgi">{log.makine.kod}</div></td><td>{log.kaynak}</td><td>%{(log.risk_orani * 100).toLocaleString('tr-TR', { maximumFractionDigits: 1 })}</td><td><GeneralPriorityBadge genelOncelik={log.genel_oncelik} legacyOncelik={log.legacy_oncelik_seviyesi}/></td><td><span className="etiket">{log.karar_durumu === 'TUTARSIZ' ? 'Tutarsız karar verisi' : kararMetni[log.karar_durumu]}</span></td><td>{log.karar_veren ?? '—'}</td><td>{log.karar_zamani ? new Date(log.karar_zamani).toLocaleString('tr-TR') : '—'}</td><td style={{ maxWidth: 260 }}>{log.is_emri_bilgisi ? <Link to={`/app/is-emirleri/${log.is_emri_bilgisi.id}`}>{log.is_emri_bilgisi.is_emri_numarasi}</Link> : ozet ? <span title={ozet} style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{ozet}</span> : '—'}</td><td><Link to={`/app/tahminler/${log.id}`}>Detay</Link></td></tr>
      })}</tbody></table></div>
      <div style={{ padding: '14px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><button type="button" className="buton-sekonder" disabled={sayfa === 1} onClick={() => setSayfa(v => v - 1)}><ChevronLeft size={16}/>Önceki</button><span>Sayfa {sayfa} / {Math.ceil(veri.count / 10) || 1}</span><button type="button" className="buton-sekonder" disabled={sayfa * 10 >= veri.count} onClick={() => setSayfa(v => v + 1)}>Sonraki<ChevronRight size={16}/></button></div></div>}
  </div>
}
