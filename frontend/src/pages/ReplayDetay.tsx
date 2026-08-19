import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  Square,
  Activity,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
} from 'lucide-react'
import {
  replayAdim,
  replayBaslat,
  replayDevamEt,
  replayDuraklat,
  replayIptalEt,
  replayOgeleriniGetir,
  replayOturumuDetayiGetir,
  replayRetry,
} from '../api/replay'
import type { ReplayOge, ReplayOturumDetay } from '../types/replay'
import { replayDurumMetni, replayOgeDurumMetni } from '../types/replay'
import { useAuth } from '../app/AuthContext'
import { ApiHatasi } from '../types/apiHata'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { EmptyState } from '../components/feedback/EmptyState'
import { ErrorState } from '../components/feedback/ErrorState'
import { MetricCard } from '../components/data-display/MetricCard'

function yuzdeFormatla(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return 'Hesaplanamadı'
  return `%${(value * 100).toLocaleString('tr-TR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })}`
}

export function ReplayDetay() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const { kullanici } = useAuth()
  const isAdmin = kullanici?.rol === 'ADMIN'

  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [session, setSession] = useState<ReplayOturumDetay | null>(null)

  const [ogeler, setOgeler] = useState<ReplayOge[]>([])
  const [ogelerYukleniyor, setOgelerYukleniyor] = useState(false)
  const [ogelerHatasi, setOgelerHatasi] = useState<string | null>(null)

  const [seciliBatch, setSeciliBatch] = useState<number>(5)
  const [islemGonderiliyor, setIslemGonderiliyor] = useState(false)
  const [islemHatasi, setIslemHatasi] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) return
    let unmounted = false

    replayOturumuDetayiGetir(sessionId)
      .then((res) => {
        if (!unmounted) {
          setSession(res)
          setSeciliBatch(res.varsayilan_batch_boyutu || 5)
          setYukleniyor(false)
        }
      })
      .catch((err) => {
        if (!unmounted) {
          if (err instanceof ApiHatasi) {
            setHata(err.message)
            setTraceId(err.traceId ?? null)
          } else {
            setHata('Replay detayı yüklenirken bir hata oluştu.')
          }
          setYukleniyor(false)
        }
      })

    replayOgeleriniGetir(sessionId, 1, 20)
      .then((res) => {
        if (!unmounted) {
          setOgeler(res.results)
          setOgelerHatasi(null)
          setOgelerYukleniyor(false)
        }
      })
      .catch((err) => {
        if (!unmounted) {
          if (err instanceof ApiHatasi) {
            setOgelerHatasi(err.message)
          } else {
            setOgelerHatasi('Replay öğeleri yüklenirken bir hata oluştu.')
          }
          setOgelerYukleniyor(false)
        }
      })

    return () => {
      unmounted = true
    }
  }, [sessionId])

  const ogeleriYukle = async () => {
    if (!sessionId) return
    setOgelerYukleniyor(true)
    setOgelerHatasi(null)
    try {
      const res = await replayOgeleriniGetir(sessionId, 1, 20)
      setOgeler(res.results)
    } catch (err) {
      if (err instanceof ApiHatasi) {
        setOgelerHatasi(err.message)
      } else {
        setOgelerHatasi('Replay öğeleri yüklenirken bir hata oluştu.')
      }
    } finally {
      setOgelerYukleniyor(false)
    }
  }

  const islemYap = async (actionFn: () => Promise<ReplayOturumDetay>) => {
    if (!session || islemGonderiliyor) return
    setIslemGonderiliyor(true)
    setIslemHatasi(null)

    try {
      const guncel = await actionFn()
      setSession(guncel)
      void ogeleriYukle()
    } catch (err) {
      if (err instanceof ApiHatasi) {
        if (err.status === 409) {
          setIslemHatasi(
            'Replay oturumu başka bir işlem tarafından güncellendi veya oturum kilitli (Claim). Güncel bilgileri yükleyin.'
          )
        } else {
          setIslemHatasi(err.message)
        }
      } else {
        setIslemHatasi('İşlem gerçekleştirilemedi.')
      }
    } finally {
      setIslemGonderiliyor(false)
    }
  }

  if (yukleniyor) {
    return (
      <div className="sayfa-konteyner">
        <LoadingSkeleton adet={6} />
      </div>
    )
  }

  if (hata || !session) {
    return (
      <div className="sayfa-konteyner">
        <ErrorState mesaj={hata || 'Oturum bulunamadı.'} traceId={traceId} onRetry={() => window.location.reload()} />
      </div>
    )
  }

  const binaryMetrics = session.metrikler?.binary

  return (
    <div className="sayfa-konteyner">
      {/* Üst Başlık */}
      <div className="sayfa-baslik-alani">
        <div>
          <button
            type="button"
            className="buton-sekonder"
            onClick={() => navigate('/app/replay')}
            style={{ marginBottom: '12px', padding: '6px 12px', fontSize: '0.85rem' }}
          >
            <ArrowLeft size={16} />
            <span>Replay Oturumlarına Dön</span>
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <h1 className="sayfa-basligi">{session.makine.ad} Replay Oturumu</h1>
            <span className="etiket">{session.makine.kod}</span>
            <span className="etiket" style={{ textTransform: 'uppercase' }}>{session.split}</span>
            <span className="rozet bilgi">{replayDurumMetni(session.durum)}</span>
          </div>
          <p className="sayfa-alt-basligi">
            İlerleme: {session.ilerleme.basarili + session.ilerleme.basarisiz} / {session.toplam_oge} (%{session.ilerleme.tamamlanma_yuzdesi}) — Oluşturulma: {new Date(session.olusturulma_zamani).toLocaleString('tr-TR')}
          </p>
        </div>
      </div>

      {islemHatasi && <ErrorState mesaj={islemHatasi} onRetry={() => window.location.reload()} />}

      {/* ADMIN Kontrol Paneli */}
      {isAdmin ? (
        <div className="dashboard-panel" style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <h3 style={{ margin: '0 0 4px 0', fontSize: '1.05rem' }}>Oynatma Kontrolleri (Admin)</h3>
              <p className="aciklama" style={{ margin: 0, fontSize: '0.85rem' }}>
                Simülasyon adımlarını tekli veya toplu (batch) olarak tetikleyin.
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <label htmlFor="batch-select" style={{ margin: 0, fontSize: '0.85rem' }}>Batch Boyutu:</label>
                <select
                  id="batch-select"
                  value={seciliBatch}
                  onChange={(e) => setSeciliBatch(Number(e.target.value))}
                  disabled={islemGonderiliyor}
                  style={{ width: 'auto', padding: '6px 12px', fontSize: '0.85rem' }}
                >
                  <option value={1}>1 Ölçüm</option>
                  <option value={5}>5 Ölçüm</option>
                  <option value={10}>10 Ölçüm</option>
                  <option value={25}>25 Ölçüm (Max)</option>
                </select>
              </div>

              {session.durum === 'HAZIR' && (
                <button
                  type="button"
                  className="buton-primer"
                  onClick={() => void islemYap(() => replayBaslat(session.id, session.version))}
                  disabled={islemGonderiliyor}
                >
                  <Play size={16} />
                  <span>Başlat</span>
                </button>
              )}

              {(session.durum === 'CALISIYOR' || session.durum === 'DURAKLATILDI' || session.durum === 'HAZIR') && (
                <button
                  type="button"
                  className="buton-primer"
                  onClick={() => void islemYap(() => replayAdim(session.id, session.version, seciliBatch))}
                  disabled={islemGonderiliyor}
                >
                  <SkipForward size={16} />
                  <span>{seciliBatch} Adım İşle</span>
                </button>
              )}

              {session.durum === 'CALISIYOR' && (
                <button
                  type="button"
                  className="buton-sekonder"
                  onClick={() => void islemYap(() => replayDuraklat(session.id, session.version))}
                  disabled={islemGonderiliyor}
                >
                  <Pause size={16} />
                  <span>Duraklat</span>
                </button>
              )}

              {session.durum === 'DURAKLATILDI' && (
                <button
                  type="button"
                  className="buton-primer"
                  onClick={() => void islemYap(() => replayDevamEt(session.id, session.version))}
                  disabled={islemGonderiliyor}
                >
                  <Play size={16} />
                  <span>Devam Et</span>
                </button>
              )}

              {session.durum === 'HATALI' && (
                <button
                  type="button"
                  className="buton-primer"
                  onClick={() => void islemYap(() => replayRetry(session.id, session.version))}
                  disabled={islemGonderiliyor}
                >
                  <RotateCcw size={16} />
                  <span>Başarısızları Yeniden Dene</span>
                </button>
              )}

              {session.durum !== 'TAMAMLANDI' && session.durum !== 'IPTAL_EDILDI' && (
                <button
                  type="button"
                  className="buton-sekonder"
                  style={{ color: 'var(--status-critical-text)', borderColor: 'var(--status-critical-border)' }}
                  onClick={() => void islemYap(() => replayIptalEt(session.id, session.version))}
                  disabled={islemGonderiliyor}
                >
                  <Square size={16} />
                  <span>İptal Et</span>
                </button>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div style={{ padding: '12px 16px', background: 'var(--status-info-bg)', borderRadius: '8px', marginBottom: '24px', fontSize: '0.9rem', color: 'var(--status-info-text)' }}>
          Replay simülasyonunu duraklatma, devam ettirme veya adımlama kontrolleri yetkili ADMIN kullanıcılarına açıktır.
        </div>
      )}

      {/* Metrikler & Performans Kartları */}
      <div className="dashboard-grid" style={{ marginBottom: '24px' }}>
        <MetricCard
          baslik="İşlenen Kayıt"
          deger={`${session.ilerleme.basarili + session.ilerleme.basarisiz} / ${session.toplam_oge}`}
          aciklama={`Başarılı: ${session.ilerleme.basarili} — Hatalı: ${session.ilerleme.basarisiz}`}
          varyant="varsayilan"
        />

        <MetricCard
          baslik="Precision"
          deger={binaryMetrics ? yuzdeFormatla(binaryMetrics.precision) : 'Hesaplanamadı'}
          aciklama="Arıza uyarılarının ne kadarının gerçek arıza olduğunu gösterir."
          varyant="varsayilan"
        />

        <MetricCard
          baslik="Recall"
          deger={binaryMetrics ? yuzdeFormatla(binaryMetrics.recall) : 'Hesaplanamadı'}
          aciklama="Gerçek arızaların ne kadarının yakalandığını gösterir."
          varyant="varsayilan"
        />

        <MetricCard
          baslik="PR-AUC"
          deger={binaryMetrics ? yuzdeFormatla(binaryMetrics.pr_auc) : 'Hesaplanamadı'}
          aciklama="Threshold'dan bağımsız precision-recall performansı."
          varyant="varsayilan"
        />

        <MetricCard
          baslik="F1-Skoru (Yardımcı)"
          deger={binaryMetrics ? yuzdeFormatla(binaryMetrics.f1) : 'Hesaplanamadı'}
          aciklama={binaryMetrics ? `Değerlendirilen öğe: ${session.metrikler.degerlendirilen_oge_sayisi}` : 'Nihai metrikler tamamlanan replay için gösterilir.'}
          varyant="varsayilan"
        />
      </div>

      {session.metrikler.metrik_uyarilari.length > 0 && (
        <div className="dashboard-panel" role="status" style={{ marginBottom: '24px' }}>
          <h3 style={{ marginTop: 0 }}>Metrik uyarıları</h3>
          <ul style={{ marginBottom: 0 }}>
            {session.metrikler.metrik_uyarilari.map((uyari) => <li key={uyari}>{uyari}</li>)}
          </ul>
        </div>
      )}

      <div className="dashboard-panel" style={{ marginBottom: '24px', overflowX: 'auto' }}>
        <h3 style={{ marginTop: 0 }}>Confusion Matrix</h3>
        {binaryMetrics ? (
          <table className="veri-tablosu">
            <caption className="sr-only">Gerçek ve tahmin edilen arıza sınıflarının sayım matrisi</caption>
            <thead>
              <tr>
                <th scope="col">Gerçek / Tahmin</th>
                <th scope="col">Tahmin: Sağlam</th>
                <th scope="col">Tahmin: Arıza</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Gerçek: Sağlam</th>
                <td><strong>TN — Doğru sağlam</strong><br />{binaryMetrics.confusion_matrix.true_negative}</td>
                <td><strong>FP — Yanlış alarm</strong><br />{binaryMetrics.confusion_matrix.false_positive}</td>
              </tr>
              <tr>
                <th scope="row">Gerçek: Arıza</th>
                <td><strong>FN — Kaçırılan arıza</strong><br />{binaryMetrics.confusion_matrix.false_negative}</td>
                <td><strong>TP — Doğru arıza</strong><br />{binaryMetrics.confusion_matrix.true_positive}</td>
              </tr>
            </tbody>
          </table>
        ) : (
          <p style={{ marginBottom: 0 }}>Confusion matrix hesaplanamadı.</p>
        )}
      </div>

      {/* İşlenen Son Ölçümler Listesi */}
      <div className="dashboard-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={20} color="var(--primary)" />
            <h3 style={{ margin: 0, fontSize: '1.05rem' }}>İşlenen Son Sensör Ölçümleri</h3>
          </div>

          <button
            type="button"
            className="buton-sekonder"
            style={{ width: 'auto', padding: '4px 10px', fontSize: '0.82rem' }}
            onClick={ogeleriYukle}
            disabled={ogelerYukleniyor}
          >
            <RotateCcw size={14} />
            <span>Yenile</span>
          </button>
        </div>

        {ogelerYukleniyor ? (
          <LoadingSkeleton adet={3} />
        ) : ogelerHatasi ? (
          <ErrorState mesaj={ogelerHatasi} onRetry={ogeleriYukle} />
        ) : ogeler.length === 0 ? (
          <EmptyState
            baslik="Henüz Ölçüm İşlenmedi"
            aciklama="Replay simülasyonu adımlandıkça işlenen sensör verileri burada listelenecektir."
            ikon={<Activity size={28} />}
          />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="veri-tablosu">
              <thead>
                <tr>
                  <th>Sıra No</th>
                  <th>Durum</th>
                  <th>Risk Uyarısı</th>
                  <th>Öncelik</th>
                  <th>İşlenme Zamanı</th>
                  <th style={{ textAlign: 'right' }}>Kaynak Tahmin Kaydı</th>
                </tr>
              </thead>
              <tbody>
                {ogeler.map((oge) => (
                  <tr key={oge.id}>
                    <td>
                      <strong>#{oge.sira}</strong>
                    </td>
                    <td>
                      <span className="etiket">{replayOgeDurumMetni(oge.durum)}</span>
                    </td>
                    <td>
                      {oge.risk_uyarisi === true ? (
                        <span className="rozet" style={{ background: 'var(--status-critical-bg)', color: 'var(--status-critical-text)' }}>
                          <AlertTriangle size={12} />
                          Risk Uyarısı Var
                        </span>
                      ) : oge.risk_uyarisi === false ? (
                        <span className="rozet basarili">
                          <CheckCircle2 size={12} />
                          Normal
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>-</span>
                      )}
                    </td>
                    <td>
                      {oge.oncelik_seviyesi ? (
                        <span className="etiket">{oge.oncelik_seviyesi}</span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>-</span>
                      )}
                    </td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      {oge.islenme_zamani ? new Date(oge.islenme_zamani).toLocaleString('tr-TR') : '-'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {oge.tahmin_kaydi_id ? (
                        <button
                          type="button"
                          className="buton-sekonder"
                          style={{ width: 'auto', padding: '4px 10px', fontSize: '0.82rem' }}
                          onClick={() => navigate(`/app/tahminler/${oge.tahmin_kaydi_id}`)}
                        >
                          <span>Değerlendirmeyi Gör</span>
                          <ExternalLink size={14} />
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Kayıt Yok</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ marginTop: '16px', padding: '12px 16px', background: 'var(--bg-subtle)', borderRadius: '8px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          <strong>Güvenlik Notu:</strong> Deterministik sensör replay akışından otomatik olarak bakım iş emri oluşturulmaz. İş emirleri yalnızca doğrulanmış gerçek üretim değerlendirmelerinden açılabilir.
        </div>
      </div>
    </div>
  )
}
