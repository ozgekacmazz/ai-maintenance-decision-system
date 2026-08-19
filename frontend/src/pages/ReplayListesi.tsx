import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Plus, ChevronLeft, ChevronRight, Activity, ShieldAlert } from 'lucide-react'
import { replayOturumlariniGetir, replayOturumuOlustur } from '../api/replay'
import { makineleriGetir } from '../api/bakim'
import type { ReplayOturumOzet } from '../types/replay'
import { replayDurumMetni } from '../types/replay'
import type { MakineOzet } from '../types/tahminler'
import { useAuth } from '../app/AuthContext'
import { ApiHatasi } from '../types/apiHata'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { EmptyState } from '../components/feedback/EmptyState'
import { ErrorState } from '../components/feedback/ErrorState'

export function ReplayListesi() {
  const navigate = useNavigate()
  const { kullanici } = useAuth()
  const isAdmin = kullanici?.rol === 'ADMIN'

  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [veri, setVeri] = useState<{ count: number; results: ReplayOturumOzet[] }>({
    count: 0,
    results: [],
  })

  const [sayfa, setSayfa] = useState(1)
  const [makineler, setMakineler] = useState<MakineOzet[]>([])

  // Modal State
  const [modalAcik, setModalAcik] = useState(false)
  const [seciliMakineId, setSeciliMakineId] = useState<string>('')
  const [split, setSplit] = useState<'test' | 'validation' | 'all'>('test')
  const [kayitSayisi, setKayitSayisi] = useState(250)
  const [batchBoyutu, setBatchBoyutu] = useState(5)
  const [olusturuluyor, setOlusturuluyor] = useState(false)
  const [modalHatasi, setModalHatasi] = useState<string | null>(null)

  useEffect(() => {
    void makineleriGetir()
      .then((res) => {
        setMakineler(res.results)
        if (res.results.length > 0) {
          setSeciliMakineId(String(res.results[0].id))
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    let unmounted = false

    replayOturumlariniGetir({ sayfa, sayfa_boyutu: 10 })
      .then((res) => {
        if (!unmounted) {
          setVeri({ count: res.count, results: res.results || [] })
          setYukleniyor(false)
        }
      })
      .catch((err) => {
        if (!unmounted) {
          if (err instanceof ApiHatasi) {
            setHata(err.message)
            setTraceId(err.traceId ?? null)
          } else {
            setHata('Replay oturumları yüklenirken bir hata oluştu.')
          }
          setYukleniyor(false)
        }
      })

    return () => {
      unmounted = true
    }
  }, [sayfa])

  const yeniOturumOlustur = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!seciliMakineId) return

    setOlusturuluyor(true)
    setModalHatasi(null)

    try {
      const yeni = await replayOturumuOlustur({
        makine_id: Number(seciliMakineId),
        split,
        kayit_sayisi: Number(kayitSayisi),
        varsayilan_batch_boyutu: Number(batchBoyutu),
      })
      setModalAcik(false)
      navigate(`/app/replay/${yeni.id}`)
    } catch (err) {
      if (err instanceof ApiHatasi) {
        setModalHatasi(err.message)
      } else {
        setModalHatasi('Replay oturumu oluşturulurken bir hata oluştu.')
      }
    } finally {
      setIslemYukleniyor(false)
    }
  }

  const setIslemYukleniyor = (val: boolean) => setOlusturuluyor(val)

  return (
    <div className="sayfa-konteyner">
      <div className="sayfa-baslik-alani">
        <div>
          <h1 className="sayfa-basligi">Sensör Replay (AI4I Simülasyonu)</h1>
          <p className="sayfa-alt-basligi">
            Kayıtlı AI4I sensör veri kümesini sırayla oynatarak sistemin risk değerlendirmelerini ve model performansını gözlemleyin.
          </p>
        </div>

        {isAdmin && (
          <button
            type="button"
            className="buton-primer"
            onClick={() => setModalAcik(true)}
          >
            <Plus size={18} />
            <span>Yeni Replay Oturumu</span>
          </button>
        )}
      </div>

      {!isAdmin && (
        <div style={{ padding: '12px 16px', background: 'var(--status-info-bg)', border: '1px solid var(--status-info-border)', borderRadius: '8px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-info-text)', fontWeight: 600 }}>
            <ShieldAlert size={18} />
            <span>Bilgi: Replay Oturumu Başlatma / Adımlama Yetkisi</span>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.88rem', color: 'var(--status-info-text)' }}>
            Mevcut oturumları görüntüleyebilirsiniz. Yeni oturum oluşturma ve oynatma kontrolleri yalnız ADMIN yetkisine sahiptir.
          </p>
        </div>
      )}

      {/* İçerik */}
      {yukleniyor ? (
        <LoadingSkeleton adet={5} />
      ) : hata ? (
        <ErrorState mesaj={hata} traceId={traceId} onRetry={() => window.location.reload()} />
      ) : veri.results.length === 0 ? (
        <EmptyState
          baslik="Henüz Replay Oturumu Oluşturulmadı"
          aciklama="Sensör veri replay simülasyonunu başlatmak için yeni bir oturum oluşturun."
          ikon={<Activity size={32} />}
          action={
            isAdmin ? (
              <button
                type="button"
                className="buton-primer"
                onClick={() => setModalAcik(true)}
              >
                <Plus size={18} />
                <span>Yeni Replay Oturumu Oluştur</span>
              </button>
            ) : null
          }
        />
      ) : (
        <div className="dashboard-panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="veri-tablosu">
              <thead>
                <tr>
                  <th>Makine</th>
                  <th>Split</th>
                  <th>Durum</th>
                  <th>İlerleme</th>
                  <th>Başarılı / Hatalı</th>
                  <th>Oluşturulma</th>
                  <th style={{ textAlign: 'right' }}>İşlem</th>
                </tr>
              </thead>
              <tbody>
                {veri.results.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => navigate(`/app/replay/${item.id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <div style={{ fontWeight: 600 }}>{item.makine.ad}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{item.makine.kod}</div>
                    </td>
                    <td>
                      <span className="etiket" style={{ textTransform: 'uppercase' }}>{item.split}</span>
                    </td>
                    <td>
                      <span className="etiket">{replayDurumMetni(item.durum)}</span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ flex: 1, height: '6px', background: 'var(--bg-subtle)', borderRadius: '3px', overflow: 'hidden', minWidth: '80px' }}>
                          <div
                            style={{
                              height: '100%',
                              width: `${item.ilerleme.tamamlanma_yuzdesi}%`,
                              background: 'var(--brand-primary)',
                            }}
                          />
                        </div>
                        <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>
                          %{item.ilerleme.tamamlanma_yuzdesi}
                        </span>
                      </div>
                    </td>
                    <td style={{ fontSize: '0.88rem' }}>
                      <span style={{ color: 'var(--status-success-text)', fontWeight: 600 }}>{item.ilerleme.basarili}</span> /{' '}
                      <span style={{ color: item.ilerleme.basarisiz > 0 ? 'var(--status-critical-text)' : 'var(--text-muted)' }}>{item.ilerleme.basarisiz}</span>
                    </td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      {new Date(item.olusturulma_zamani).toLocaleString('tr-TR')}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        className="buton-sekonder"
                        style={{ width: 'auto', padding: '4px 10px', fontSize: '0.82rem' }}
                        onClick={(e) => {
                          e.stopPropagation()
                          navigate(`/app/replay/${item.id}`)
                        }}
                      >
                        <span>Detay</span>
                        <Play size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Sayfalama */}
          <div
            style={{
              padding: '14px 24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderTop: '1px solid var(--border-color)',
              gap: '16px',
            }}
          >
            <button
              type="button"
              className="buton-sekonder"
              style={{ width: 'auto' }}
              disabled={sayfa === 1 || yukleniyor}
              onClick={() => setSayfa((s) => Math.max(1, s - 1))}
            >
              <ChevronLeft size={16} />
              <span>Önceki</span>
            </button>

            <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
              Sayfa <strong>{sayfa}</strong> / {Math.ceil(veri.count / 10) || 1}
            </span>

            <button
              type="button"
              className="buton-sekonder"
              style={{ width: 'auto' }}
              disabled={sayfa * 10 >= veri.count || yukleniyor}
              onClick={() => setSayfa((s) => s + 1)}
            >
              <span>Sonraki</span>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Yeni Replay Oturumu Modal */}
      {modalAcik && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '16px',
          }}
        >
          <div className="kart" style={{ maxWidth: '500px', width: '100%' }}>
            <h3>Yeni Sensör Replay Oturumu</h3>
            {modalHatasi && <ErrorState mesaj={modalHatasi} />}

            <form onSubmit={(e) => void yeniOturumOlustur(e)}>
              <div>
                <label htmlFor="replay-makine">Makine Seçimi</label>
                <select
                  id="replay-makine"
                  value={seciliMakineId}
                  onChange={(e) => setSeciliMakineId(e.target.value)}
                  required
                >
                  {makineler.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.kod} — {m.ad}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="replay-split">Veri Kümesi Bölümü (Split)</label>
                <select
                  id="replay-split"
                  value={split}
                  onChange={(e) => setSplit(e.target.value as 'test' | 'validation' | 'all')}
                >
                  <option value="test">Test Verisi (Varsayılan)</option>
                  <option value="validation">Doğrulama Verisi (Validation)</option>
                  <option value="all">Tüm Veri Kümesi (All)</option>
                </select>
              </div>

              <div className="form-grid-2">
                <div>
                  <label htmlFor="replay-limit">Kayıt Sayısı (Max 1000)</label>
                  <input
                    id="replay-limit"
                    type="number"
                    min={1}
                    max={1000}
                    value={kayitSayisi}
                    onChange={(e) => setKayitSayisi(Number(e.target.value))}
                    required
                  />
                </div>

                <div>
                  <label htmlFor="replay-batch">Varsayılan Batch Boyutu (Max 25)</label>
                  <input
                    id="replay-batch"
                    type="number"
                    min={1}
                    max={25}
                    value={batchBoyutu}
                    onChange={(e) => setBatchBoyutu(Number(e.target.value))}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                <button
                  type="button"
                  className="buton-sekonder"
                  onClick={() => {
                    setModalAcik(false)
                    setModalHatasi(null)
                  }}
                  disabled={olusturuluyor}
                >
                  İptal
                </button>
                <button type="submit" className="buton-primer" disabled={olusturuluyor}>
                  {olusturuluyor ? 'Oluşturuluyor...' : 'Oturumu Başlat'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
