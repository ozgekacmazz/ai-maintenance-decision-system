import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, Activity, Database, ShieldAlert, PlusCircle } from 'lucide-react'

import { tahminKayitlariniGetir } from '../api/tahminler'
import type { TahminKaydiOzet } from '../types/tahminler'
import { anaAksiyonMetni } from '../types/tahminler'
import { MetricCard } from '../components/data-display/MetricCard'
import { StatusBadge } from '../components/feedback/StatusBadge'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { EmptyState } from '../components/feedback/EmptyState'
import { ErrorState } from '../components/feedback/ErrorState'

export function Dashboard() {
  const navigate = useNavigate()
  const [toplamKayit, setToplamKayit] = useState<number | null>(null)
  const [riskliKayitSayisi, setRiskliKayitSayisi] = useState<number | null>(null)
  const [kritikSayisi, setKritikSayisi] = useState<number | null>(null)
  const [oncelikliRiskler, setOncelikliRiskler] = useState<TahminKaydiOzet[]>([])

  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)

  const veriGetir = useCallback(async () => {
    setYukleniyor(true)
    setHata(null)
    setTraceId(null)
    try {
      const [toplamRes, riskliRes, kritikRes, listeRes] = await Promise.all([
        tahminKayitlariniGetir({ sayfa_boyutu: 1 }),
        tahminKayitlariniGetir({ risk_uyarisi: true, sayfa_boyutu: 1 }),
        tahminKayitlariniGetir({ oncelik_seviyesi: 'KRITIK', sayfa_boyutu: 1 }),
        tahminKayitlariniGetir({ risk_uyarisi: true, sirala: '-nihai_oncelik', sayfa_boyutu: 10 }),
      ])

      setToplamKayit(toplamRes.count)
      setRiskliKayitSayisi(riskliRes.count)
      setKritikSayisi(kritikRes.count)
      setOncelikliRiskler(listeRes.results)
    } catch (err: unknown) {
      const errorObj = err as { mesaj?: string; trace_id?: string; message?: string }
      setHata(errorObj.mesaj ?? errorObj.message ?? 'Veriler yüklenirken bir hata oluştu.')
      setTraceId(errorObj.trace_id ?? null)
    } finally {
      setYukleniyor(false)
    }
  }, [])

  useEffect(() => {
    let aktif = true
    const fetchData = async () => {
      try {
        const [toplamRes, riskliRes, kritikRes, listeRes] = await Promise.all([
          tahminKayitlariniGetir({ sayfa_boyutu: 1 }),
          tahminKayitlariniGetir({ risk_uyarisi: true, sayfa_boyutu: 1 }),
          tahminKayitlariniGetir({ oncelik_seviyesi: 'KRITIK', sayfa_boyutu: 1 }),
          tahminKayitlariniGetir({ risk_uyarisi: true, sirala: '-nihai_oncelik', sayfa_boyutu: 10 }),
        ])

        if (aktif) {
          setToplamKayit(toplamRes.count)
          setRiskliKayitSayisi(riskliRes.count)
          setKritikSayisi(kritikRes.count)
          setOncelikliRiskler(listeRes.results)
          setHata(null)
          setTraceId(null)
        }
      } catch (err: unknown) {
        if (aktif) {
          const errorObj = err as { mesaj?: string; trace_id?: string; message?: string }
          setHata(errorObj.mesaj ?? errorObj.message ?? 'Veriler yüklenirken bir hata oluştu.')
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
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div>
        <h2>Makine Sağlığı ve Bakım Görünümü</h2>
        <p className="aciklama" style={{ margin: 0 }}>
          Sistem genelindeki gerçek sensör değerlendirmelerini ve öncelikli bakım kararlarını takip edin.
        </p>
      </div>

      {/* KPI Kartları Grid */}
      <div className="metrik-grid">
        <MetricCard
          baslik="Toplam Tahmin Kaydı"
          deger={yukleniyor ? '…' : (toplamKayit ?? 0)}
          aciklama="Değerlendirilmiş toplam sensör ölçümü"
          ikon={<Database size={24} />}
          varyant="varsayilan"
        />

        <MetricCard
          baslik="Risk Uyarısı Bulunanlar"
          deger={yukleniyor ? '…' : (riskliKayitSayisi ?? 0)}
          aciklama="Model eşiğini aşan arıza riski"
          ikon={<AlertTriangle size={24} />}
          varyant={riskliKayitSayisi && riskliKayitSayisi > 0 ? 'uyari' : 'basarili'}
        />

        <MetricCard
          baslik="Kritik Öncelikli Değerlendirmeler"
          deger={yukleniyor ? '…' : (kritikSayisi ?? 0)}
          aciklama="Acil teknik müdahale bekleyen kayıtlar"
          ikon={<ShieldAlert size={24} />}
          varyant={kritikSayisi && kritikSayisi > 0 ? 'kritik' : 'basarili'}
        />
      </div>

      {/* Öncelikli Riskler Paneli */}
      <div className="dashboard-panel">
        <div className="dashboard-panel-ust">
          <div>
            <h3 className="dashboard-panel-baslik">Öncelikli Riskler</h3>
            <p className="dashboard-panel-alt">
              Nihai bakım öncelik skoruna göre sıralanmış son sensör analizleri
            </p>
          </div>
          <button
            type="button"
            style={{ width: 'auto' }}
            onClick={() => navigate('/app/analiz')}
          >
            <PlusCircle size={16} />
            <span>Yeni Sensör Analizi</span>
          </button>
        </div>

        {yukleniyor ? (
          <LoadingSkeleton adet={4} />
        ) : hata ? (
          <ErrorState mesaj={hata} traceId={traceId} onRetry={() => void veriGetir()} />
        ) : oncelikliRiskler.length === 0 ? (
          <EmptyState
            baslik="Henüz değerlendirilmiş bir kayıt yok"
            aciklama="Sistemde henüz kaydedilmiş bir sensör analizi bulunmuyor. Yeni bir analiz başlatarak ilk değerlendirmeyi oluşturabilirsiniz."
            ikon={<Activity size={32} />}
            action={
              <button type="button" onClick={() => navigate('/app/analiz')}>
                Hızlı Sensör Analizi Başlat
              </button>
            }
          />
        ) : (
          <div className="risk-liste">
            {oncelikliRiskler.map((kayit) => {
              const yuzdeRisk = Math.round(kayit.risk_orani * 100)
              const tarih = new Date(kayit.olcum_zamani).toLocaleString('tr-TR', {
                dateStyle: 'medium',
                timeStyle: 'short',
              })

              return (
                <div key={kayit.id} className="risk-kart">
                  <div className="risk-kart-makine">
                    <span className="risk-kart-makine-adi">
                      {kayit.makine.ad || 'Makine'}
                    </span>
                    <span className="risk-kart-makine-kodu">
                      KOD: {kayit.makine.kod}
                    </span>
                  </div>

                  <div className="risk-kart-orani">
                    <span className="risk-orani-etiket">Arıza Riski</span>
                    <span className={`risk-orani-yuzde ${kayit.risk_uyarisi ? '' : 'dusuk'}`}>
                      %{yuzdeRisk}
                    </span>
                  </div>

                  <div className="risk-kart-detay">
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <StatusBadge oncelik={kayit.oncelik_seviyesi} />
                      <StatusBadge arizaTipi={kayit.en_yuksek_guvenilir_ariza_tipi} />
                    </div>
                    <span style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      {anaAksiyonMetni(kayit.ana_aksiyon)}
                    </span>
                  </div>

                  <div className="risk-kart-zaman">
                    <span>Ölçüm Zamanı</span>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                      {tarih}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
