import { useCallback, useEffect, useState } from 'react'
import { Building2, Plus, Edit2, CheckCircle2, XCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import { makineAktiflikDegistir, makineGuncelle, makineleriGetirFull, makineOlustur } from '../api/yonetim'
import type { Makine } from '../types/yonetim'
import { useAuth } from '../app/AuthContext'
import { ApiHatasi } from '../types/apiHata'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { EmptyState } from '../components/feedback/EmptyState'
import { ErrorState } from '../components/feedback/ErrorState'

export function MakineYonetimi() {
  const { kullanici } = useAuth()
  const isAdmin = kullanici?.rol === 'ADMIN'

  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [veri, setVeri] = useState<{ count: number; results: Makine[] }>({ count: 0, results: [] })
  const [sayfa, setSayfa] = useState(1)

  // Form Modal State
  const [modalAcik, setModalAcik] = useState(false)
  const [duzenlenecekMakine, setDuzenlenecekMakine] = useState<Makine | null>(null)
  const [makineKodu, setMakineKodu] = useState('')
  const [ad, setAd] = useState('')
  const [kritiklik, setKritiklik] = useState(3)
  const [islemGonderiliyor, setIslemGonderiliyor] = useState(false)
  const [modalHatasi, setModalHatasi] = useState<string | null>(null)

  const yenidenYukle = useCallback(async () => {
    setYukleniyor(true)
    setHata(null)
    setTraceId(null)
    try {
      const res = await makineleriGetirFull(sayfa, 10)
      setVeri({ count: res.count, results: res.results })
    } catch (err) {
      if (err instanceof ApiHatasi) {
        setHata(err.message)
        setTraceId(err.traceId ?? null)
      } else setHata('Makine listesi yüklenirken bir hata oluştu.')
    } finally {
      setYukleniyor(false)
    }
  }, [sayfa])

  useEffect(() => {
    let unmounted = false
    void (async () => {
      if (!unmounted) await yenidenYukle()
    })()
    return () => { unmounted = true }
  }, [yenidenYukle])

  const modalAcYeni = () => {
    setDuzenlenecekMakine(null)
    setMakineKodu('')
    setAd('')
    setKritiklik(3)
    setModalHatasi(null)
    setModalAcik(true)
  }

  const modalAcDuzenle = (m: Makine) => {
    setDuzenlenecekMakine(m)
    setMakineKodu(m.makine_kodu)
    setAd(m.ad)
    setKritiklik(m.kritiklik_seviyesi)
    setModalHatasi(null)
    setModalAcik(true)
  }

  const formGonder = async (e: React.FormEvent) => {
    e.preventDefault()
    setIslemGonderiliyor(true)
    setModalHatasi(null)

    try {
      if (duzenlenecekMakine) {
        await makineGuncelle(duzenlenecekMakine.id, {
          makine_kodu: makineKodu,
          ad,
          kritiklik_seviyesi: Number(kritiklik),
        })
      } else {
        await makineOlustur({
          makine_kodu: makineKodu,
          ad,
          kritiklik_seviyesi: Number(kritiklik),
        })
      }
      setModalAcik(false)
      await yenidenYukle()
    } catch (err) {
      if (err instanceof ApiHatasi) {
        setModalHatasi(err.message)
      } else {
        setModalHatasi('Makine kaydedilirken hata oluştu.')
      }
    } finally {
      setIslemGonderiliyor(false)
    }
  }

  const aktiflikDegistir = async (m: Makine) => {
    try {
      await makineAktiflikDegistir(m.id, !m.aktif)
      await yenidenYukle()
    } catch (err) {
      if (err instanceof ApiHatasi) {
        setHata(err.message)
      } else {
        setHata('Aktiflik durumu değiştirilirken hata oluştu.')
      }
    }
  }

  if (!isAdmin) {
    return (
      <div className="sayfa-konteyner">
        <ErrorState mesaj="Bu alanı görüntülemek için YÖNETİCİ (ADMIN) yetkisi gereklidir." />
      </div>
    )
  }

  return (
    <div className="sayfa-konteyner">
      <div className="sayfa-baslik-alani">
        <div>
          <h1 className="sayfa-basligi">Makine Yönetimi (Admin)</h1>
          <p className="sayfa-alt-basligi">
            Sistemdeki üretim ekipmanlarını, kodlarını, kritiklik seviyelerini ve aktiflik durumlarını yönetin.
          </p>
        </div>

        <button type="button" className="buton-primer" onClick={modalAcYeni}>
          <Plus size={18} />
          <span>Yeni Makine Ekle</span>
        </button>
      </div>

      {yukleniyor ? (
        <LoadingSkeleton adet={5} />
      ) : hata ? (
        <ErrorState mesaj={hata} traceId={traceId} onRetry={() => window.location.reload()} />
      ) : veri.results.length === 0 ? (
        <EmptyState
          baslik="Henüz Makine Tanımlanmadı"
          aciklama="Sisteme yeni bir üretim makinesi eklemek için 'Yeni Makine Ekle' butonunu kullanın."
          ikon={<Building2 size={32} />}
        />
      ) : (
        <div className="dashboard-panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="veri-tablosu">
              <thead>
                <tr>
                  <th>Makine Kodu</th>
                  <th>Makine Adı</th>
                  <th>Kritiklik Seviyesi</th>
                  <th>Durum</th>
                  <th>Güncellenme</th>
                  <th style={{ textAlign: 'right' }}>Aksiyonlar</th>
                </tr>
              </thead>
              <tbody>
                {veri.results.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{m.makine_kodu}</span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{m.ad}</td>
                    <td>
                      <span className="etiket">{m.kritiklik_seviyesi} / 5</span>
                    </td>
                    <td>
                      {m.aktif ? (
                        <span className="rozet basarili" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle2 size={12} />
                          Aktif
                        </span>
                      ) : (
                        <span className="rozet" style={{ background: 'var(--bg-subtle)', color: 'var(--text-muted)', border: '1px solid var(--border-color)' }}>
                          <XCircle size={12} />
                          Pasif
                        </span>
                      )}
                    </td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      {new Date(m.guncellenme_zamani).toLocaleString('tr-TR')}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '8px' }}>
                        <button
                          type="button"
                          className="buton-sekonder"
                          style={{ width: 'auto', padding: '4px 10px', fontSize: '0.82rem' }}
                          onClick={() => modalAcDuzenle(m)}
                        >
                          <Edit2 size={14} />
                          <span>Düzenle</span>
                        </button>
                        <button
                          type="button"
                          className="buton-sekonder"
                          style={{
                            width: 'auto',
                            padding: '4px 10px',
                            fontSize: '0.82rem',
                            color: m.aktif ? 'var(--status-critical-text)' : 'var(--status-success-text)',
                          }}
                          onClick={() => void aktiflikDegistir(m)}
                        >
                          {m.aktif ? 'Pasife Al' : 'Aktifleştir'}
                        </button>
                      </div>
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

      {/* Makine Ekle/Düzenle Modal */}
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
          <div className="kart" style={{ maxWidth: '480px', width: '100%' }}>
            <h3>{duzenlenecekMakine ? 'Makine Düzenle' : 'Yeni Makine Ekle'}</h3>
            {modalHatasi && <ErrorState mesaj={modalHatasi} />}

            <form onSubmit={(e) => void formGonder(e)}>
              <div>
                <label htmlFor="makine-kodu">Makine Kodu</label>
                <input
                  id="makine-kodu"
                  type="text"
                  value={makineKodu}
                  onChange={(e) => setMakineKodu(e.target.value)}
                  placeholder="Örn: M-101"
                  required
                />
              </div>

              <div>
                <label htmlFor="makine-adi">Makine Adı</label>
                <input
                  id="makine-adi"
                  type="text"
                  value={ad}
                  onChange={(e) => setAd(e.target.value)}
                  placeholder="Örn: CNC Pres Motoru 1"
                  required
                />
              </div>

              <div>
                <label htmlFor="makine-kritiklik">Kritiklik Seviyesi (1 - 5)</label>
                <input
                  id="makine-kritiklik"
                  type="number"
                  min={1}
                  max={5}
                  value={kritiklik}
                  onChange={(e) => setKritiklik(Number(e.target.value))}
                  required
                />
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                <button
                  type="button"
                  className="buton-sekonder"
                  onClick={() => setModalAcik(false)}
                  disabled={islemGonderiliyor}
                >
                  İptal
                </button>
                <button type="submit" className="buton-primer" disabled={islemGonderiliyor}>
                  {islemGonderiliyor ? 'Kaydediliyor...' : 'Kaydet'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
