import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Wrench,
  Filter,
  ChevronLeft,
  ChevronRight,
  Clock,
  AlertTriangle,
  User,
  ExternalLink,
} from 'lucide-react'
import { isEmirleriniGetir } from '../api/isEmirleri'
import { makineleriGetir } from '../api/bakim'
import type { GenelOncelik, IsEmriDurum, IsEmriOncelik, IsEmriOzet } from '../types/isEmirleri'
import { isEmriDurumMetni } from '../types/isEmirleri'
import type { MakineOzet } from '../types/tahminler'
import { anaAksiyonMetni } from '../types/tahminler'
import { ApiHatasi } from '../types/apiHata'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { EmptyState } from '../components/feedback/EmptyState'
import { ErrorState } from '../components/feedback/ErrorState'
import { GeneralPriorityBadge } from '../components/feedback/GeneralPriorityBadge'

function parcaMetni(item: IsEmriOzet['erp_ozeti'][number]): string {
  const ad = item.parca_adi || item.parca_kodu
  return item.gerekli_miktar ? `${ad} ×${item.gerekli_miktar}` : ad
}

function parcaOzeti(parcalar: IsEmriOzet['erp_ozeti']): string {
  if (parcalar.length === 0) return 'Parça önerisi yok'
  const gorunenler = parcalar.slice(0, 2).map(parcaMetni).join(', ')
  return parcalar.length > 2 ? `${gorunenler} +${parcalar.length - 2} parça` : gorunenler
}

export function IsEmirleri() {
  const navigate = useNavigate()
  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [veri, setVeri] = useState<{ count: number; results: IsEmriOzet[] }>({
    count: 0,
    results: [],
  })

  const [makineler, setMakineler] = useState<MakineOzet[]>([])
  const [sayfa, setSayfa] = useState(1)
  const [durum, setDurum] = useState<IsEmriDurum | ''>('')
  const [oncelik, setOncelik] = useState<IsEmriOncelik | ''>('')
  const [genelOncelik, setGenelOncelik] = useState<GenelOncelik | ''>('')
  const [makineId, setMakineId] = useState<string>('')
  const [gecikmis, setGecikmis] = useState<string>('')
  const [sirala, setSirala] = useState<string>('-etkin_genel_oncelik')
  const [isEmriNumarasi, setIsEmriNumarasi] = useState('')

  useEffect(() => {
    void makineleriGetir()
      .then((res) => setMakineler(res.results))
      .catch(() => {})
  }, [])

  useEffect(() => {
    let unmounted = false

    isEmirleriniGetir({
      durum: durum || undefined,
      etkin_oncelik_seviyesi: oncelik || undefined,
      genel_oncelik: genelOncelik || undefined,
      makine_id: makineId ? Number(makineId) : undefined,
      gecikmis: gecikmis === 'true' ? true : gecikmis === 'false' ? false : undefined,
      is_emri_numarasi: isEmriNumarasi || undefined,
      sirala,
      sayfa,
      sayfa_boyutu: 10,
    })
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
            setHata('İş emirleri yüklenirken bir hata oluştu.')
          }
          setYukleniyor(false)
        }
      })

    return () => {
      unmounted = true
    }
  }, [sayfa, durum, oncelik, genelOncelik, makineId, gecikmis, sirala, isEmriNumarasi])

  const yenile = () => {
    setSayfa(1)
  }

  return (
    <div className="sayfa-konteyner">
      <div className="sayfa-baslik-alani">
        <div>
          <h1 className="sayfa-basligi">İş Emirleri</h1>
          <p className="sayfa-alt-basligi">
            Sistem tarafından üretilmiş bakım kararlarının operasyonel iş emirlerini takip ve organize edin.
          </p>
        </div>
      </div>

      {/* Filtre Paneli */}
      <div className="dashboard-panel">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Filter size={18} color="var(--primary)" />
          <h3 style={{ margin: 0, fontSize: '1rem' }}>İş Emri Filtreleri</h3>
        </div>

        <div className="form-grid-3">
          <div>
            <label htmlFor="filtre-numara">İş Emri No Ara</label>
            <input
              id="filtre-numara"
              type="text"
              value={isEmriNumarasi}
              onChange={(e) => {
                setIsEmriNumarasi(e.target.value)
                yenile()
              }}
              placeholder="Örn: WO-2026..."
            />
          </div>

          <div>
            <label htmlFor="filtre-durum">İş Emri Durumu</label>
            <select
              id="filtre-durum"
              value={durum}
              onChange={(e) => {
                setDurum(e.target.value as IsEmriDurum | '')
                yenile()
              }}
            >
              <option value="">Tümü</option>
              <option value="ACIK">Açık</option>
              <option value="ATANDI">Atandı</option>
              <option value="DEVAM_EDIYOR">Devam Ediyor</option>
              <option value="BEKLEMEDE">Beklemede</option>
              <option value="TAMAMLANDI">Tamamlandı</option>
              <option value="IPTAL_EDILDI">İptal Edildi</option>
            </select>
          </div>

          <div>
            <label htmlFor="filtre-oncelik">Öncelik Seviyesi</label>
            <select
              id="filtre-oncelik"
              value={oncelik}
              onChange={(e) => {
                setOncelik(e.target.value as IsEmriOncelik | '')
                yenile()
              }}
            >
              <option value="">Tümü</option>
              <option value="KRITIK">Kritik</option>
              <option value="YUKSEK">Yüksek</option>
              <option value="ORTA">Orta</option>
              <option value="DUSUK">Düşük</option>
            </select>
          </div>

          <div>
            <label htmlFor="filtre-makine">Makine</label>
            <select
              id="filtre-makine"
              value={makineId}
              onChange={(e) => {
                setMakineId(e.target.value)
                yenile()
              }}
            >
              <option value="">Tüm Makineler</option>
              {makineler.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.kod} — {m.ad}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="filtre-genel-oncelik">Genel Öncelik</label>
            <select
              id="filtre-genel-oncelik"
              value={genelOncelik}
              onChange={(e) => {
                setGenelOncelik(e.target.value ? Number(e.target.value) as GenelOncelik : '')
                yenile()
              }}
            >
              <option value="">Tümü</option>
              {[5, 4, 3, 2, 1].map((value) => (
                <option key={value} value={value}>Öncelik {value}/5</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="filtre-gecikmis">SLA / Gecikme Durumu</label>
            <select
              id="filtre-gecikmis"
              value={gecikmis}
              onChange={(e) => {
                setGecikmis(e.target.value)
                yenile()
              }}
            >
              <option value="">Tümü</option>
              <option value="true">Gecikmiş (SLA Aşıldı)</option>
              <option value="false">Süresi İçinde</option>
            </select>
          </div>

          <div>
            <label htmlFor="filtre-sirala">Sıralama</label>
            <select
              id="filtre-sirala"
              value={sirala}
              onChange={(e) => {
                setSirala(e.target.value)
                yenile()
              }}
            >
              <option value="-olusturulma_zamani">Oluşturulma (Yeni-Eski)</option>
              <option value="olusturulma_zamani">Oluşturulma (Eski-Yeni)</option>
              <option value="hedef_mudahale_zamani">Müdahale Zamanı (Önce-Sonra)</option>
              <option value="-etkin_oncelik">Etkin Öncelik (Yüksek-Düşük)</option>
              <option value="-etkin_genel_oncelik">Genel Öncelik (5–1)</option>
              <option value="etkin_genel_oncelik">Genel Öncelik (1–5)</option>
              <option value="durum">Durum</option>
            </select>
          </div>
        </div>
      </div>

      {/* İçerik Alanı */}
      {yukleniyor ? (
        <LoadingSkeleton adet={5} />
      ) : hata ? (
        <ErrorState mesaj={hata} traceId={traceId} onRetry={yenile} />
      ) : veri.results.length === 0 ? (
        <EmptyState
          baslik="İş Emri Bulunamadı"
          aciklama="Seçilen filtrelere uygun kaydedilmiş bir bakım iş emri bulunmuyor."
          ikon={<Wrench size={32} />}
        />
      ) : (
        <div className="dashboard-panel" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="veri-tablosu">
              <thead>
                <tr>
                  <th>İş Emri No</th>
                  <th>Makine</th>
                  <th>Aksiyon</th>
                  <th>Parça</th>
                  <th>Öncelik</th>
                  <th>Durum</th>
                  <th>Atanan</th>
                  <th>Hedef Müdahale</th>
                  <th>SLA</th>
                  <th>Oluşturulma</th>
                  <th style={{ textAlign: 'right' }}>İşlem</th>
                </tr>
              </thead>
              <tbody>
                {veri.results.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => navigate(`/app/is-emirleri/${item.id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--brand-primary)' }}>
                        {item.is_emri_numarasi}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{item.makine.ad}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{item.makine.kod}</div>
                    </td>
                    <td style={{ minWidth: '180px', maxWidth: '260px' }}>
                      <span
                        title={item.ana_aksiyon ? anaAksiyonMetni(item.ana_aksiyon) : undefined}
                        style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
                      >
                        {item.ana_aksiyon ? anaAksiyonMetni(item.ana_aksiyon) : 'Aksiyon belirtilmemiş'}
                      </span>
                    </td>
                    <td style={{ minWidth: '180px', maxWidth: '280px' }}>
                      <span title={item.erp_ozeti.map(parcaMetni).join(', ') || undefined}>
                        {parcaOzeti(item.erp_ozeti)}
                      </span>
                    </td>
                    <td>
                      <GeneralPriorityBadge
                        genelOncelik={item.etkin_genel_oncelik}
                        legacyOncelik={item.etkin_oncelik_seviyesi}
                      />
                      {item.etkin_genel_oncelik !== null && item.kaynak_genel_oncelik !== item.etkin_genel_oncelik && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                          Kaynak öncelik: {item.kaynak_genel_oncelik}/5
                        </div>
                      )}
                    </td>
                    <td>
                      <span className="etiket">{isEmriDurumMetni(item.durum)}</span>
                    </td>
                    <td>
                      {item.atanan_kullanici ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.88rem' }}>
                          <User size={14} color="var(--text-secondary)" />
                          {item.atanan_kullanici.kullanici_adi}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Atanmadı</span>
                      )}
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>
                      {new Date(item.hedef_mudahale_zamani).toLocaleString('tr-TR')}
                    </td>
                    <td>
                      {item.gecikmis ? (
                        <span className="rozet" style={{ background: 'var(--status-critical-bg)', color: 'var(--status-critical-text)', border: '1px solid var(--status-critical-border)' }}>
                          <AlertTriangle size={12} />
                          Süresi Geçti
                        </span>
                      ) : (
                        <span className="rozet basarili" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <Clock size={12} />
                          Süre İçinde
                        </span>
                      )}
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
                          navigate(`/app/is-emirleri/${item.id}`)
                        }}
                      >
                        <span>Detay</span>
                        <ExternalLink size={14} />
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
    </div>
  )
}
