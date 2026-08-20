import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Filter, ChevronLeft, ChevronRight, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { tahminKayitlariniGetir } from '../api/tahminler'
import type { SayfalanmisYanit, TahminKaydiOzet } from '../types/tahminler'
import {
  anaAksiyonMetni,
  arizaTipiMetni,
  kararGuveniMetni,
  kaynakMetni,
} from '../types/tahminler'
import { GeneralPriorityBadge } from '../components/feedback/GeneralPriorityBadge'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { EmptyState } from '../components/feedback/EmptyState'
import { ErrorState } from '../components/feedback/ErrorState'

export function TahminGecmisi() {
  const navigate = useNavigate()

  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [veri, setVeri] = useState<SayfalanmisYanit<TahminKaydiOzet> | null>(null)

  // Filtre durumları
  const [sayfa, setSayfa] = useState(1)
  const [riskUyarisi, setRiskUyarisi] = useState<string>('')
  const [oncelikSeviyesi, setOncelikSeviyesi] = useState<string>('')
  const [genelOncelik, setGenelOncelik] = useState<string>('')
  const [kararGuveni, setKararGuveni] = useState<string>('')
  const [kaynak, setKaynak] = useState<string>('')
  const [sirala, setSirala] = useState<string>('-genel_oncelik')
  const [yenilemeSayaci, setYenilemeSayaci] = useState(0)

  useEffect(() => {
    let aktif = true
    const fetchData = async () => {
      setYukleniyor(true)
      try {
        const res = await tahminKayitlariniGetir({
          sayfa,
          sayfa_boyutu: 10,
          risk_uyarisi: riskUyarisi === 'true' ? true : riskUyarisi === 'false' ? false : undefined,
          oncelik_seviyesi: oncelikSeviyesi || undefined,
          genel_oncelik: genelOncelik ? Number(genelOncelik) as 1 | 2 | 3 | 4 | 5 : undefined,
          karar_guveni: kararGuveni || undefined,
          kaynak: kaynak || undefined,
          sirala: sirala || undefined,
        })
        if (aktif) {
          setVeri(res)
          setHata(null)
          setTraceId(null)
        }
      } catch (err: unknown) {
        if (aktif) {
          const errorObj = err as { mesaj?: string; trace_id?: string; message?: string }
          setHata(errorObj.mesaj ?? errorObj.message ?? 'Değerlendirme geçmişi yüklenemedi.')
          setTraceId(errorObj.trace_id ?? null)
        }
      } finally {
        if (aktif) {
          setYukleniyor(false)
        }
      }
    }

    void fetchData()
    return () => {
      aktif = false
    }
  }, [sayfa, riskUyarisi, oncelikSeviyesi, genelOncelik, kararGuveni, kaynak, sirala, yenilemeSayaci])

  return (
    <div className="sayfa-konteyner">
      <div className="sayfa-baslik-alani">
        <div>
          <h1 className="sayfa-basligi">Tahmin Geçmişi</h1>
          <p className="sayfa-alt-basligi">
            Kaydedilmiş sensör değerlendirmelerini, bakım önceliklerini ve karar geçmişini inceleyin.
          </p>
        </div>
        <button
          type="button"
          className="buton-primer"
          onClick={() => navigate('/app/tahminler/yeni')}
        >
          <Plus size={18} />
          <span>Yeni Kalıcı Değerlendirme</span>
        </button>
      </div>

      {/* Filtre Paneli */}
      <div className="dashboard-panel" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Filter size={18} color="var(--primary)" />
          <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Filtrele ve Sırala</h3>
        </div>

        <div className="form-grid-3">
          <div>
            <label htmlFor="filtre-risk">Risk Durumu</label>
            <select
              id="filtre-risk"
              value={riskUyarisi}
              onChange={(e) => {
                setRiskUyarisi(e.target.value)
                setSayfa(1)
              }}
            >
              <option value="">Tüm Kayıtlar</option>
              <option value="true">Risk Uyarısı Var</option>
              <option value="false">Normal (Risk Yok)</option>
            </select>
          </div>

          <div>
            <label htmlFor="filtre-oncelik">Bakım Önceliği</label>
            <select
              id="filtre-oncelik"
              value={oncelikSeviyesi}
              onChange={(e) => {
                setOncelikSeviyesi(e.target.value)
                setSayfa(1)
              }}
            >
              <option value="">Tüm Öncelikler</option>
              <option value="KRITIK">Kritik</option>
              <option value="YUKSEK">Yüksek</option>
              <option value="ORTA">Orta</option>
              <option value="DUSUK">Düşük</option>
            </select>
          </div>

          <div>
            <label htmlFor="filtre-guven">Karar Güveni</label>
            <select
              id="filtre-guven"
              value={kararGuveni}
              onChange={(e) => {
                setKararGuveni(e.target.value)
                setSayfa(1)
              }}
            >
              <option value="">Tüm Güven Seviyeleri</option>
              <option value="YUKSEK">Yüksek Güven</option>
              <option value="ORTA">Orta Güven</option>
              <option value="DUSUK">Düşük Güven</option>
            </select>
          </div>

          <div>
            <label htmlFor="filtre-genel-oncelik">Genel Öncelik</label>
            <select id="filtre-genel-oncelik" value={genelOncelik} onChange={(e) => { setGenelOncelik(e.target.value); setSayfa(1) }}>
              <option value="">Tümü</option>
              {[5, 4, 3, 2, 1].map((value) => <option key={value} value={value}>Öncelik {value}/5</option>)}
            </select>
          </div>

          <div>
            <label htmlFor="filtre-kaynak">Değerlendirme Kaynağı</label>
            <select
              id="filtre-kaynak"
              value={kaynak}
              onChange={(e) => {
                setKaynak(e.target.value)
                setSayfa(1)
              }}
            >
              <option value="">Tüm Kaynaklar</option>
              <option value="MANUEL">Manuel Değerlendirme</option>
              <option value="REPLAY">Replay</option>
              <option value="ENTEGRASYON">Entegrasyon</option>
            </select>
          </div>

          <div>
            <label htmlFor="filtre-sirala">Sıralama</label>
            <select
              id="filtre-sirala"
              value={sirala}
              onChange={(e) => {
                setSirala(e.target.value)
                setSayfa(1)
              }}
            >
              <option value="-olcum_zamani">Ölçüm Zamanı (Yeniden Eskiye)</option>
              <option value="olcum_zamani">Ölçüm Zamanı (Eskiden Yeniye)</option>
              <option value="-nihai_oncelik">Bakım Önceliği (Yüksekten Düşüğe)</option>
              <option value="-genel_oncelik">Genel Öncelik (5–1)</option>
              <option value="genel_oncelik">Genel Öncelik (1–5)</option>
              <option value="-risk_orani">Risk Oranı (Yüksekten Düşüğe)</option>
            </select>
          </div>
        </div>
      </div>

      {/* İçerik Alanı */}
      {hata ? (
        <ErrorState mesaj={hata} traceId={traceId} onRetry={() => setYenilemeSayaci((v) => v + 1)} />
      ) : yukleniyor ? (
        <LoadingSkeleton adet={5} />
      ) : !veri || veri.results.length === 0 ? (
        <EmptyState
          baslik="Kayıtlı Değerlendirme Bulunamadı"
          aciklama="Seçilen filtrelere uygun kaydedilmiş herhangi bir sensör değerlendirmesi bulunmuyor."
          action={
            <button
              type="button"
              className="buton-primer"
              onClick={() => navigate('/app/tahminler/yeni')}
            >
              Yeni Kalıcı Değerlendirme Başlat
            </button>
          }
        />
      ) : (
        <div className="dashboard-panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Toplam <strong>{veri.count}</strong> değerlendirme
            </span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table className="veri-tablosu">
              <caption className="sr-only">Tahmin geçmişi kayıtları</caption>
              <thead>
                <tr>
                  <th scope="col">Makine</th>
                  <th scope="col">Ölçüm Zamanı</th>
                  <th scope="col">Risk Oranı</th>
                  <th scope="col">Fiziksel Arıza Tipi</th>
                  <th scope="col">Bakım Önceliği</th>
                  <th scope="col">Ana Aksiyon</th>
                  <th scope="col">Karar Güveni</th>
                  <th scope="col">Kaynak</th>
                </tr>
              </thead>
              <tbody>
                {veri.results.map((kayit) => (
                  <tr
                    key={kayit.id}
                    onClick={() => navigate(`/app/tahminler/${kayit.id}`)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        navigate(`/app/tahminler/${kayit.id}`)
                      }
                    }}
                    role="link"
                    tabIndex={0}
                    aria-label={`${kayit.makine.kod} tahmin detayını aç`}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <div style={{ fontWeight: 600 }}>{kayit.makine.ad}</div>
                      <div className="alt-bilgi">{kayit.makine.kod}</div>
                    </td>
                    <td>{new Date(kayit.olcum_zamani).toLocaleString('tr-TR')}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {kayit.risk_uyarisi ? (
                          <AlertTriangle size={16} color="var(--status-critical-text)" />
                        ) : (
                          <CheckCircle2 size={16} color="var(--status-success-text)" />
                        )}
                        <span style={{ fontWeight: 700 }}>%{Math.round(kayit.risk_orani * 100)}</span>
                      </div>
                    </td>
                    <td>
                      {kayit.belirsiz_fiziksel_tip
                        ? 'Belirsiz arıza tipi'
                        : arizaTipiMetni(kayit.en_yuksek_guvenilir_ariza_tipi)}
                    </td>
                    <td>
                      <GeneralPriorityBadge
                        genelOncelik={kayit.genel_oncelik}
                        legacyOncelik={kayit.oncelik_seviyesi}
                      />
                    </td>
                    <td>{anaAksiyonMetni(kayit.ana_aksiyon)}</td>
                    <td>{kararGuveniMetni(kayit.karar_guveni)}</td>
                    <td>
                      <span className="etiket">{kaynakMetni(kayit.kaynak)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Sayfalama */}
          <div style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)' }}>
            <button
              type="button"
              className="buton-sekonder"
              disabled={!veri.previous || yukleniyor}
              onClick={() => setSayfa((s) => Math.max(1, s - 1))}
            >
              <ChevronLeft size={16} />
              <span>Önceki</span>
            </button>

            <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Sayfa <strong>{sayfa}</strong> / {Math.ceil(veri.count / 10) || 1}
            </span>

            <button
              type="button"
              className="buton-sekonder"
              disabled={!veri.next || yukleniyor}
              onClick={() => setSayfa((s) => s + 1)}
            >
              <span>Sonraki</span>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
