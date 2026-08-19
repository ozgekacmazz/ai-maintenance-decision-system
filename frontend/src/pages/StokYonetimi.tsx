import { useEffect, useState } from 'react'
import { Package, Edit2, ChevronLeft, ChevronRight, CheckCircle2, AlertTriangle } from 'lucide-react'
import { stokGuncelle, stoklariGetir } from '../api/yonetim'
import type { StokItem } from '../types/yonetim'
import { useAuth } from '../app/AuthContext'
import { ApiHatasi } from '../types/apiHata'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { EmptyState } from '../components/feedback/EmptyState'
import { ErrorState } from '../components/feedback/ErrorState'

export function StokYonetimi() {
  const { kullanici } = useAuth()
  const isAdmin = kullanici?.rol === 'ADMIN'

  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [veri, setVeri] = useState<{ count: number; results: StokItem[] }>({ count: 0, results: [] })
  const [sayfa, setSayfa] = useState(1)

  // Edit Modal State
  const [modalAcik, setModalAcik] = useState(false)
  const [seciliStok, setSeciliStok] = useState<StokItem | null>(null)
  const [toplamStok, setToplamStok] = useState(0)
  const [minimumStok, setMinimumStok] = useState(0)
  const [tedarikGun, setTedarikGun] = useState(3)
  const [islemGonderiliyor, setIslemGonderiliyor] = useState(false)
  const [modalHatasi, setModalHatasi] = useState<string | null>(null)

  useEffect(() => {
    let unmounted = false

    stoklariGetir(sayfa, 10)
      .then((res) => {
        if (!unmounted) {
          setVeri({ count: res.count, results: res.results })
          setYukleniyor(false)
        }
      })
      .catch((err) => {
        if (!unmounted) {
          if (err instanceof ApiHatasi) {
            setHata(err.message)
            setTraceId(err.traceId ?? null)
          } else {
            setHata('Stok ve parça listesi yüklenirken bir hata oluştu.')
          }
          setYukleniyor(false)
        }
      })

    return () => {
      unmounted = true
    }
  }, [sayfa])

  const modalAcDuzenle = (stok: StokItem) => {
    setSeciliStok(stok)
    setToplamStok(stok.toplam_stok)
    setMinimumStok(stok.minimum_stok)
    setTedarikGun(stok.tedarik_gun)
    setModalHatasi(null)
    setModalAcik(true)
  }

  const stokGuncelleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!seciliStok) return

    setIslemGonderiliyor(true)
    setModalHatasi(null)

    try {
      await stokGuncelle(seciliStok.id, {
        toplam_stok: Number(toplamStok),
        minimum_stok: Number(minimumStok),
        tedarik_gun: Number(tedarikGun),
      })
      setModalAcik(false)
      setSayfa((s) => s)
    } catch (err) {
      if (err instanceof ApiHatasi) {
        setModalHatasi(err.message)
      } else {
        setModalHatasi('Stok güncellenirken bir hata oluştu.')
      }
    } finally {
      setIslemGonderiliyor(false)
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
          <h1 className="sayfa-basligi">Stok ve Parça Yönetimi (Admin)</h1>
          <p className="sayfa-alt-basligi">
            ERP yedek parça envanterini, kullanılabilir stok miktarlarını, minimum eşikleri ve tedarik sürelerini takip edin.
          </p>
        </div>
      </div>

      {yukleniyor ? (
        <LoadingSkeleton adet={5} />
      ) : hata ? (
        <ErrorState mesaj={hata} traceId={traceId} onRetry={() => window.location.reload()} />
      ) : veri.results.length === 0 ? (
        <EmptyState
          baslik="Henüz Parça Stok Kaydı Bulunmuyor"
          aciklama="ERP sisteminde henüz tanımlanmış yedek parça stok kaydı bulunmamaktadır."
          ikon={<Package size={32} />}
        />
      ) : (
        <div className="dashboard-panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="veri-tablosu">
              <thead>
                <tr>
                  <th>Parça Kodu</th>
                  <th>Parça Adı</th>
                  <th>Toplam Stok</th>
                  <th>Min. Stok</th>
                  <th>Tedarik Süresi</th>
                  <th>Stok Durumu</th>
                  <th>Güncellenme</th>
                  <th style={{ textAlign: 'right' }}>Aksiyon</th>
                </tr>
              </thead>
              <tbody>
                {veri.results.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{item.parca.parca_kodu}</span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{item.parca.ad}</td>
                    <td>{item.toplam_stok} adet</td>
                    <td>{item.minimum_stok} adet</td>
                    <td>{item.tedarik_gun} gün</td>
                    <td>
                      {item.stok_yeterli ? (
                        <span className="rozet basarili" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle2 size={12} />
                          Yeterli ({item.toplam_stok} adet)
                        </span>
                      ) : item.toplam_stok === 0 ? (
                        <span className="rozet" style={{ background: 'var(--status-critical-bg)', color: 'var(--status-critical-text)', border: '1px solid var(--status-critical-border)' }}>
                          <AlertTriangle size={12} />
                          Stok: 0 adet (Tükendi)
                        </span>
                      ) : (
                        <span className="rozet uyari" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <AlertTriangle size={12} />
                          Eşik Altı ({item.toplam_stok} adet)
                        </span>
                      )}
                    </td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      {new Date(item.guncellenme_zamani).toLocaleString('tr-TR')}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        className="buton-sekonder"
                        style={{ width: 'auto', padding: '4px 10px', fontSize: '0.82rem' }}
                        onClick={() => modalAcDuzenle(item)}
                      >
                        <Edit2 size={14} />
                        <span>Stok Güncelle</span>
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

      {/* Edit Stock Modal */}
      {modalAcik && seciliStok && (
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
            <h3>Stok Güncelle: {seciliStok.parca.ad}</h3>
            {modalHatasi && <ErrorState mesaj={modalHatasi} />}

            <form onSubmit={(e) => void stokGuncelleSubmit(e)}>
              <div>
                <label htmlFor="toplam-stok">Toplam Stok Miktarı (Adet)</label>
                <input
                  id="toplam-stok"
                  type="number"
                  min={0}
                  value={toplamStok}
                  onChange={(e) => setToplamStok(Number(e.target.value))}
                  required
                />
              </div>

              <div>
                <label htmlFor="minimum-stok">Minimum Eşik Miktarı (Adet)</label>
                <input
                  id="minimum-stok"
                  type="number"
                  min={0}
                  value={minimumStok}
                  onChange={(e) => setMinimumStok(Number(e.target.value))}
                  required
                />
              </div>

              <div>
                <label htmlFor="tedarik-gun">Tedarik Süresi (Gün)</label>
                <input
                  id="tedarik-gun"
                  type="number"
                  min={0}
                  value={tedarikGun}
                  onChange={(e) => setTedarikGun(Number(e.target.value))}
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
                  {islemGonderiliyor ? 'Kaydediliyor...' : 'Güncelle'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
