import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Wrench,
  ExternalLink,
  History,
  ShieldAlert,
  Package,
} from 'lucide-react'
import {
  isEmriDetayiGetir,
  isEmriAta,
  isEmriDurumGecisi,
  isEmriOncelikOverride,
} from '../api/isEmirleri'
import { kullanicilariGetir } from '../api/yonetim'
import type { KullaniciYonetimItem } from '../types/yonetim'
import type { GenelOncelik, IsEmriDetay, IsEmriDurum, IsEmriOncelik } from '../types/isEmirleri'
import {
  GECERLI_DURUM_GECISLERI,
  isEmriDurumMetni,
} from '../types/isEmirleri'
import { useAuth } from '../app/AuthContext'
import { ApiHatasi } from '../types/apiHata'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { ErrorState } from '../components/feedback/ErrorState'
import { GeneralPriorityBadge } from '../components/feedback/GeneralPriorityBadge'
import { MetricCard } from '../components/data-display/MetricCard'
import { sayiFormatla } from '../types/tahminler'
import { useAccessibleDialog } from '../components/accessibility/useAccessibleDialog'

export function IsEmriDetay() {
  const { isEmriId } = useParams<{ isEmriId: string }>()
  const navigate = useNavigate()
  const { kullanici } = useAuth()

  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [isEmri, setIsEmri] = useState<IsEmriDetay | null>(null)

  // Durum geçişi modal state
  const [gecisModalAcik, setGecisModalAcik] = useState(false)
  const [hedefDurum, setHedefDurum] = useState<IsEmriDurum | ''>('')
  const [beklemeNedeni, setBeklemeNedeni] = useState('')
  const [tamamlamaNotu, setTamamlamaNotu] = useState('')
  const [iptalNedeni, setIptalNedeni] = useState('')
  const [islemGonderiliyor, setIslemGonderiliyor] = useState(false)
  const [islemHatasi, setIslemHatasi] = useState<string | null>(null)
  const [atamaModalAcik, setAtamaModalAcik] = useState(false)
  const [aktifKullanicilar, setAktifKullanicilar] = useState<KullaniciYonetimItem[]>([])
  const [atanacakKullaniciId, setAtanacakKullaniciId] = useState<number | ''>('')
  const [atamaNotu, setAtamaNotu] = useState('')
  const [atamaHatasi, setAtamaHatasi] = useState<string | null>(null)
  const [atamaCakismasi, setAtamaCakismasi] = useState(false)
  const [atamaYukleniyor, setAtamaYukleniyor] = useState(false)

  // Admin override state
  const [overrideModalAcik, setOverrideModalAcik] = useState(false)
  const [etkinOncelik, setEtkinOncelik] = useState<IsEmriOncelik>('KRITIK')
  const [genelOncelik, setGenelOncelik] = useState<GenelOncelik>(3)
  const [overrideNedeni, setOverrideNedeni] = useState('')
  const gecisDialog = useAccessibleDialog(gecisModalAcik, () => setGecisModalAcik(false))
  const overrideDialog = useAccessibleDialog(overrideModalAcik, () => setOverrideModalAcik(false))
  const atamaDialog = useAccessibleDialog(atamaModalAcik, () => setAtamaModalAcik(false))

  const isAdmin = kullanici?.rol === 'ADMIN'

  const guncelVeriyiYukle = async () => {
    if (!isEmriId) return
    const guncel = await isEmriDetayiGetir(isEmriId)
    setIsEmri(guncel)
    setAtamaCakismasi(false)
    setAtamaHatasi(null)
  }

  const atamaModaliniAc = async () => {
    if (!isEmri) return
    setAtamaModalAcik(true)
    setAtamaYukleniyor(true)
    setAtamaHatasi(null)
    setAtamaCakismasi(false)
    setAtanacakKullaniciId(isEmri.atanan_kullanici?.id ?? '')
    try {
      const kullanicilar = await kullanicilariGetir()
      setAktifKullanicilar(kullanicilar.filter((aday) => aday.is_active))
    } catch (err) {
      setAtamaHatasi(err instanceof ApiHatasi ? err.message : 'Kullanıcı listesi yüklenemedi.')
    } finally {
      setAtamaYukleniyor(false)
    }
  }

  const atamayiKaydet = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isEmri || atanacakKullaniciId === '') return
    setAtamaYukleniyor(true)
    setAtamaHatasi(null)
    setAtamaCakismasi(false)
    try {
      const guncel = await isEmriAta(isEmri.id, {
        atanan_kullanici_id: atanacakKullaniciId,
        beklenen_version: isEmri.version,
        not: atamaNotu.trim() || undefined,
      })
      setIsEmri(guncel)
      setAtamaModalAcik(false)
      setAtamaNotu('')
    } catch (err) {
      if (err instanceof ApiHatasi && err.status === 409) {
        setAtamaCakismasi(true)
        setAtamaHatasi('Bu iş emri siz formu açtıktan sonra değiştirildi. Güncel veriyi yükleyip yeniden deneyin.')
      } else if (err instanceof ApiHatasi && err.status === 403) {
        setAtamaHatasi('Bu iş emrini atama yetkiniz yok.')
      } else setAtamaHatasi(err instanceof ApiHatasi ? err.message : 'Atama kaydedilemedi.')
    } finally {
      setAtamaYukleniyor(false)
    }
  }

  useEffect(() => {
    if (!isEmriId) return
    let unmounted = false

    isEmriDetayiGetir(isEmriId)
      .then((res) => {
        if (!unmounted) {
          setIsEmri(res)
          setYukleniyor(false)
        }
      })
      .catch((err) => {
        if (!unmounted) {
          if (err instanceof ApiHatasi) {
            setHata(err.message)
            setTraceId(err.traceId ?? null)
          } else {
            setHata('İş emri detayı yüklenirken bir hata oluştu.')
          }
          setYukleniyor(false)
        }
      })

    return () => {
      unmounted = true
    }
  }, [isEmriId])

  const durumGecisiYap = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isEmri || !hedefDurum) return

    setIslemGonderiliyor(true)
    setIslemHatasi(null)

    try {
      const guncel = await isEmriDurumGecisi(isEmri.id, {
        beklenen_version: isEmri.version,
        hedef_durum: hedefDurum as IsEmriDurum,
        bekleme_nedeni: hedefDurum === 'BEKLEMEDE' ? beklemeNedeni : undefined,
        tamamlama_notu: hedefDurum === 'TAMAMLANDI' ? tamamlamaNotu : undefined,
        iptal_nedeni: hedefDurum === 'IPTAL_EDILDI' ? iptalNedeni : undefined,
      })
      setIsEmri(guncel)
      setGecisModalAcik(false)
      setBeklemeNedeni('')
      setTamamlamaNotu('')
      setIptalNedeni('')
    } catch (err) {
      if (err instanceof ApiHatasi) {
        if (err.status === 409) {
          setIslemHatasi(
            'Bu iş emri başka bir işlem tarafından güncellendi. Lütfen güncel bilgileri yeniden yükleyin.'
          )
        } else {
          setIslemHatasi(err.message)
        }
      } else {
        setIslemHatasi('Durum geçişi yapılırken bir hata oluştu.')
      }
    } finally {
      setIslemGonderiliyor(false)
    }
  }

  const oncelikOverrideYap = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isEmri || !overrideNedeni.trim()) return

    setIslemGonderiliyor(true)
    setIslemHatasi(null)

    try {
      const ortak = { beklenen_version: isEmri.version, override_nedeni: overrideNedeni }
      const guncel = await isEmriOncelikOverride(
        isEmri.id,
        isEmri.etkin_genel_oncelik !== null
          ? { ...ortak, genel_oncelik: genelOncelik }
          : { ...ortak, etkin_oncelik_seviyesi: etkinOncelik }
      )
      setIsEmri(guncel)
      setOverrideModalAcik(false)
      setOverrideNedeni('')
    } catch (err) {
      if (err instanceof ApiHatasi) {
        if (err.status === 409) {
          setIslemHatasi('İş emri versiyon çakışması. Lütfen sayfayı yenileyin.')
        } else {
          setIslemHatasi(err.message)
        }
      } else {
        setIslemHatasi('Öncelik değiştirilirken bir hata oluştu.')
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

  if (hata || !isEmri) {
    return (
      <div className="sayfa-konteyner">
        <ErrorState
          mesaj={hata || 'İş emri bulunamadı.'}
          traceId={traceId}
          onRetry={() => window.location.reload()}
        />
      </div>
    )
  }

  const tumGecisler = GECERLI_DURUM_GECISLERI[isEmri.durum] || []
  const kullaniciAtananKisi = isEmri.atanan_kullanici?.id === kullanici?.id
  const gecerliGecisler = isAdmin
    ? tumGecisler
    : kullaniciAtananKisi
      ? tumGecisler.filter((durum) => durum !== 'IPTAL_EDILDI')
      : []
  const gecisEngeli = !isAdmin && !kullaniciAtananKisi
    ? isEmri.atanan_kullanici
      ? 'Bu iş emri başka bir kullanıcıya atanmış. Yalnız atanan kullanıcı durumunu değiştirebilir.'
      : 'Bu iş emri henüz atanmadı. Atama yapıldıktan sonra operasyonel durum değiştirilebilir.'
    : null

  return (
    <div className="sayfa-konteyner">
      {/* Üst Başlık & Dönüş */}
      <div className="sayfa-baslik-alani">
        <div>
          <button
            type="button"
            className="buton-sekonder"
            onClick={() => navigate('/app/is-emirleri')}
            style={{ marginBottom: '12px', padding: '6px 12px', fontSize: '0.85rem' }}
          >
            <ArrowLeft size={16} />
            <span>İş Emirlerine Dön</span>
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <h1 className="sayfa-basligi">İş Emri {isEmri.is_emri_numarasi}</h1>
            <GeneralPriorityBadge
              genelOncelik={isEmri.etkin_genel_oncelik}
              legacyOncelik={isEmri.etkin_oncelik_seviyesi}
            />
            <span className="etiket">{isEmriDurumMetni(isEmri.durum)}</span>
          </div>
          <p className="sayfa-alt-basligi">
            Makine: <strong>{isEmri.makine.ad}</strong> ({isEmri.makine.kod}) — Oluşturulma: {new Date(isEmri.olusturulma_zamani).toLocaleString('tr-TR')}
          </p>
          {isEmri.kaynak_genel_oncelik !== null && (
            <p className="sayfa-alt-basligi">Kaynak öncelik: {isEmri.kaynak_genel_oncelik}/5</p>
          )}
        </div>

        {/* Tahmin Detayı CTA */}
        {isEmri.tahmin_kaydi_id && (
          <button
            type="button"
            className="buton-primer"
            onClick={() => navigate(`/app/tahminler/${isEmri.tahmin_kaydi_id}`)}
          >
            <ExternalLink size={18} />
            <span>Kaynak Değerlendirmeyi Gör</span>
          </button>
        )}
      </div>

      {/* Hero Özet Kartları */}
      <div className="dashboard-grid" style={{ marginBottom: '24px' }}>
        <MetricCard
          baslik="Hedef Müdahale Zamanı"
          deger={new Date(isEmri.hedef_mudahale_zamani).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}
          aciklama={isEmri.gecikmis ? 'Gecikmiş (SLA Aşıldı)' : 'Süre İçinde (Normal)'}
          varyant={isEmri.gecikmis ? 'kritik' : 'basarili'}
        />

        <MetricCard
          baslik="Atanan Kullanıcı"
          deger={isEmri.atanan_kullanici ? isEmri.atanan_kullanici.kullanici_adi : 'Henüz Atanmadı'}
          aciklama={`Oluşturan: ${isEmri.olusturan.kullanici_adi}`}
          varyant="varsayilan"
        />

        <MetricCard
          baslik="Kaynak Öncelik Skoru"
          deger={isEmri.kaynak_karar ? sayiFormatla(isEmri.kaynak_karar.nihai_oncelik_skoru, 0) : '-'}
          aciklama={isEmri.manuel_oncelik_override ? 'Admin Tarafından Değiştirildi' : 'Model Kararıyla Uyumlu'}
          varyant={isEmri.manuel_oncelik_override ? 'uyari' : 'varsayilan'}
        />
      </div>

      {/* İş Emri Detay Kartı */}
      <div className="dashboard-panel" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '1.1rem' }}>{isEmri.baslik}</h3>
        <p className="aciklama" style={{ whiteSpace: 'pre-wrap', margin: '0 0 20px 0' }}>
          {isEmri.aciklama}
        </p>

        {/* Manuel Override Notu */}
        {isEmri.manuel_oncelik_override && isEmri.override_nedeni && (
          <div style={{ padding: '12px 16px', background: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)', borderRadius: '8px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--status-warning-text)', marginBottom: '4px' }}>
              <ShieldAlert size={16} />
              <span>Yönetici Öncelik Müdahalesi (Admin Override)</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.88rem', color: 'var(--status-warning-text)' }}>
              Neden: {isEmri.override_nedeni}
            </p>
          </div>
        )}

        {/* Aksiyon Butonları */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {gecerliGecisler.length > 0 && (
            <button
              type="button"
              className="buton-primer"
              onClick={() => {
                setHedefDurum(gecerliGecisler[0])
                setGecisModalAcik(true)
              }}
            >
              <Wrench size={18} />
              <span>Durum Geçişi Yap</span>
            </button>
          )}

          {isAdmin && (
            <button type="button" className="buton-primer" onClick={() => void atamaModaliniAc()}>
              <span>{isEmri.atanan_kullanici ? 'Yeniden Ata' : 'Kullanıcı Ata'}</span>
            </button>
          )}

          {isAdmin && (
            <button
              type="button"
              className="buton-sekonder"
              onClick={() => {
                setEtkinOncelik(isEmri.etkin_oncelik_seviyesi)
                setGenelOncelik(isEmri.etkin_genel_oncelik ?? 3)
                setOverrideModalAcik(true)
              }}
            >
              <ShieldAlert size={18} />
              <span>Öncelik Seviyesini Değiştir (Admin)</span>
            </button>
          )}
        </div>
        {gecisEngeli && <p className="aciklama" role="status" style={{ marginTop: 12 }}>{gecisEngeli}</p>}
      </div>

      {/* Kaynak Bakım Kararı Özeti */}
      {isEmri.kaynak_karar && (
        <div className="dashboard-panel" style={{ marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '1.05rem' }}>Kaynak AI Bakım Kararı Özeti</h3>

          <div className="dashboard-grid" style={{ marginBottom: '16px' }}>
            <div className="metrik-kart">
              <span className="etiket">Teknik Aciliyet</span>
              <div className="deger" style={{ fontSize: '1.35rem', marginTop: '4px' }}>
                {sayiFormatla(isEmri.kaynak_karar.teknik_aciliyet_skoru, 0)} / 100
              </div>
            </div>

            <div className="metrik-kart">
              <span className="etiket">Tedarik Riski</span>
              <div className="deger" style={{ fontSize: '1.35rem', marginTop: '4px' }}>
                {sayiFormatla(isEmri.kaynak_karar.tedarik_riski_skoru, 0)} / 100
              </div>
            </div>

            <div className="metrik-kart">
              <span className="etiket">Nihai Öncelik Skoru</span>
              <div className="deger" style={{ fontSize: '1.35rem', marginTop: '4px' }}>
                {sayiFormatla(isEmri.kaynak_karar.nihai_oncelik_skoru, 0)} / 100
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ERP Snapshot Bilgisi */}
      {isEmri.erp_ozeti && isEmri.erp_ozeti.length > 0 && (
        <div className="dashboard-panel" style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Package size={20} color="var(--primary)" />
            <h3 style={{ margin: 0, fontSize: '1.05rem' }}>İlgili Parça ve Stok Durumu</h3>
          </div>

          <div style={{ display: 'grid', gap: '10px' }}>
            {isEmri.erp_ozeti.map((item, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px 16px',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{item.parca_adi} ({item.parca_kodu})</div>
                  <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
                    Gerekli Miktar: {item.gerekli_miktar} adet
                  </div>
                </div>

                <div>
                  {item.stok_yeterli ? (
                    <span className="rozet basarili">Stok Yeterli</span>
                  ) : (
                    <span className="rozet">Stok Yetersiz / Sipariş Gerekli</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* İşlem Geçmişi (Timeline) */}
      <div className="dashboard-panel">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <History size={20} color="var(--primary)" />
          <h3 style={{ margin: 0, fontSize: '1.05rem' }}>İşlem Geçmişi</h3>
        </div>

        {isEmri.olaylar.length === 0 ? (
          <p className="aciklama">Henüz durum olayı kaydedilmedi.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {isEmri.olaylar.map((olay) => (
              <div
                key={olay.id}
                style={{
                  padding: '12px 16px',
                  borderLeft: '4px solid var(--brand-primary)',
                  backgroundColor: 'var(--bg-subtle)',
                  borderRadius: '0 8px 8px 0',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                    {olay.olay_tipi === 'ATAMA' || olay.olay_tipi === 'ATANDI' ? 'Kullanıcı ataması' : olay.olay_tipi === 'OLUSTURULDU' ? 'İş emri oluşturuldu' : olay.olay_tipi}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {new Date(olay.olusturulma_zamani).toLocaleString('tr-TR')}
                  </span>
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  İşlemi Yapan: <strong>{olay.gerceklestiren_kullanici_adi}</strong>
                  {olay.onceki_durum && olay.yeni_durum && (
                    <span>
                      {' '}— Durum: <em>{isEmriDurumMetni(olay.onceki_durum)}</em> → <strong>{isEmriDurumMetni(olay.yeni_durum)}</strong>
                    </span>
                  )}
                  {olay.onceki_genel_oncelik !== null && olay.yeni_genel_oncelik !== null && (
                    <span> — Öncelik {olay.onceki_genel_oncelik}/5 → {olay.yeni_genel_oncelik}/5</span>
                  )}
                  {olay.onceki_oncelik && olay.yeni_oncelik && (
                    <span> — Öncelik {olay.onceki_oncelik} → {olay.yeni_oncelik}</span>
                  )}
                  {typeof olay.detay?.not === 'string' && <span> — Not: {olay.detay.not}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {atamaModalAcik && (
        <div className="dialog-arkaplan">
          <div {...atamaDialog} aria-labelledby="atama-dialog-title" className="kart" style={{ maxWidth: 500, width: '100%' }}>
            <h3 id="atama-dialog-title">{isEmri.atanan_kullanici ? 'İş Emrini Yeniden Ata' : 'İş Emrine Kullanıcı Ata'}</h3>
            <p className="aciklama">Mevcut atanan: <strong>{isEmri.atanan_kullanici?.kullanici_adi ?? 'Henüz atanmadı'}</strong></p>
            {atamaHatasi && <ErrorState mesaj={atamaHatasi} />}
            {atamaCakismasi && (
              <button type="button" className="buton-sekonder" onClick={() => void guncelVeriyiYukle()}>
                Güncel Veriyi Yükle
              </button>
            )}
            <form onSubmit={(e) => void atamayiKaydet(e)}>
              <div>
                <label htmlFor="atanan-kullanici">Aktif kullanıcı</label>
                <select data-dialog-initial-focus id="atanan-kullanici" value={atanacakKullaniciId} onChange={(e) => setAtanacakKullaniciId(Number(e.target.value))} required disabled={atamaYukleniyor}>
                  <option value="">Kullanıcı seçin</option>
                  {aktifKullanicilar.map((aday) => <option key={aday.id} value={aday.id}>{aday.username}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="atama-notu">Atama notu (isteğe bağlı)</label>
                <textarea id="atama-notu" value={atamaNotu} onChange={(e) => setAtamaNotu(e.target.value)} maxLength={500} />
              </div>
              <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
                <button type="button" className="buton-sekonder" onClick={() => setAtamaModalAcik(false)} disabled={atamaYukleniyor}>İptal</button>
                <button type="submit" className="buton-primer" disabled={atamaYukleniyor || atanacakKullaniciId === ''}>{atamaYukleniyor ? 'Kaydediliyor...' : 'Atamayı Kaydet'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Durum Geçişi Modal */}
      {gecisModalAcik && (
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
          <div {...gecisDialog} aria-labelledby="gecis-dialog-title" className="kart" style={{ maxWidth: '500px', width: '100%', maxHeight: 'calc(100vh - 32px)', overflowY: 'auto' }}>
            <h3 id="gecis-dialog-title">İş Emri Durum Geçişi</h3>
            {islemHatasi && <ErrorState mesaj={islemHatasi} />}

            <form onSubmit={(e) => void durumGecisiYap(e)}>
              <div>
                <label htmlFor="hedef-durum">Hedef Durum</label>
                <select
                  data-dialog-initial-focus
                  id="hedef-durum"
                  value={hedefDurum}
                  onChange={(e) => setHedefDurum(e.target.value as IsEmriDurum)}
                >
                  {gecerliGecisler.map((d) => (
                    <option key={d} value={d}>
                      {isEmriDurumMetni(d)}
                    </option>
                  ))}
                </select>
              </div>

              {hedefDurum === 'BEKLEMEDE' && (
                <div>
                  <label htmlFor="bekleme-nedeni">Bekleme Nedeni (Zorunlu)</label>
                  <input
                    id="bekleme-nedeni"
                    type="text"
                    value={beklemeNedeni}
                    onChange={(e) => setBeklemeNedeni(e.target.value)}
                    required
                  />
                </div>
              )}

              {hedefDurum === 'TAMAMLANDI' && (
                <div>
                  <label htmlFor="tamamlama-notu">Tamamlama Notu (Zorunlu)</label>
                  <input
                    id="tamamlama-notu"
                    type="text"
                    value={tamamlamaNotu}
                    onChange={(e) => setTamamlamaNotu(e.target.value)}
                    required
                  />
                </div>
              )}

              {hedefDurum === 'IPTAL_EDILDI' && (
                <div>
                  <label htmlFor="iptal-nedeni">İptal Nedeni (Zorunlu)</label>
                  <input
                    id="iptal-nedeni"
                    type="text"
                    value={iptalNedeni}
                    onChange={(e) => setIptalNedeni(e.target.value)}
                    required
                  />
                </div>
              )}

              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <button
                  type="button"
                  className="buton-sekonder"
                  onClick={() => {
                    setGecisModalAcik(false)
                    setIslemHatasi(null)
                  }}
                  disabled={islemGonderiliyor}
                >
                  İptal
                </button>
                <button type="submit" className="buton-primer" disabled={islemGonderiliyor}>
                  {islemGonderiliyor ? 'Kaydediliyor...' : 'Geçişi Onayla'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Admin Override Modal */}
      {overrideModalAcik && (
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
          <div {...overrideDialog} aria-labelledby="override-dialog-title" className="kart" style={{ maxWidth: '500px', width: '100%', maxHeight: 'calc(100vh - 32px)', overflowY: 'auto' }}>
            <h3 id="override-dialog-title">Yönetici Öncelik Müdahalesi (Admin)</h3>
            {islemHatasi && <ErrorState mesaj={islemHatasi} />}

            <form onSubmit={(e) => void oncelikOverrideYap(e)}>
              <div>
                <label htmlFor="etkin-oncelik">Yeni Etkin Öncelik</label>
                <select
                  data-dialog-initial-focus
                  id="etkin-oncelik"
                  value={isEmri.etkin_genel_oncelik !== null ? genelOncelik : etkinOncelik}
                  onChange={(e) => {
                    if (isEmri.etkin_genel_oncelik !== null) setGenelOncelik(Number(e.target.value) as GenelOncelik)
                    else setEtkinOncelik(e.target.value as IsEmriOncelik)
                  }}
                >
                  {isEmri.etkin_genel_oncelik !== null ? (
                    [1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>Öncelik {value}/5</option>)
                  ) : (
                    <>
                      <option value="KRITIK">Kritik</option>
                      <option value="YUKSEK">Yüksek</option>
                      <option value="ORTA">Orta</option>
                      <option value="DUSUK">Düşük</option>
                    </>
                  )}
                </select>
              </div>

              <div>
                <label htmlFor="override-nedeni">Müdahale Gerekçesi (Zorunlu)</label>
                <input
                  id="override-nedeni"
                  type="text"
                  value={overrideNedeni}
                  onChange={(e) => setOverrideNedeni(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <button
                  type="button"
                  className="buton-sekonder"
                  onClick={() => {
                    setOverrideModalAcik(false)
                    setIslemHatasi(null)
                  }}
                  disabled={islemGonderiliyor}
                >
                  İptal
                </button>
                <button type="submit" className="buton-primer" disabled={islemGonderiliyor}>
                  {islemGonderiliyor ? 'Kaydediliyor...' : 'Önceliği Değiştir'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
