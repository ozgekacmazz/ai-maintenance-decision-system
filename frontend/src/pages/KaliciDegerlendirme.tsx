import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, Save, ArrowLeft, Building2 } from 'lucide-react'
import { makineleriGetir } from '../api/bakim'
import { kaliciTahminKaydiOlustur } from '../api/tahminler'
import type { MakineOzet, RiskTahminiGirdi } from '../types/tahminler'
import { ApiHatasi } from '../types/apiHata'
import { ErrorState } from '../components/feedback/ErrorState'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'

function UUIDUret(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

function SuAnkiDatetimeLocal(): string {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

export function KaliciDegerlendirme() {
  const navigate = useNavigate()

  // Makine listesi yükleme durumları
  const [makineler, setMakineler] = useState<MakineOzet[]>([])
  const [makinelerYukleniyor, setMakinelerYukleniyor] = useState(true)
  const [makineHatasi, setMakineHatasi] = useState<string | null>(null)

  // Form durumları
  const [makineId, setMakineId] = useState<string>('')
  const [olcumZamani, setOlcumZamani] = useState<string>(SuAnkiDatetimeLocal())
  const [girdi, setGirdi] = useState<RiskTahminiGirdi>({
    urun_tipi: 'M',
    hava_sicakligi_k: 300.0,
    proses_sicakligi_k: 310.0,
    donus_hizi_rpm: 1500,
    tork_nm: 40.0,
    takim_asinmasi_dk: 108,
  })

  // Idempotency Key: logical request başladığında 1 kere üretilir
  const [idempotencyKey, setIdempotencyKey] = useState<string>(UUIDUret)

  // Submit durumları
  const [gonderiliyor, setGonderiliyor] = useState(false)
  const [hata, setHata] = useState<string | null>(null)
  const [bilgiMesaji, setBilgiMesaji] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [alanHatalari, setAlanHatalari] = useState<Record<string, string[]>>({})

  // Form alanları değiştiğinde yeni logical request olduğu için idempotency key yenilenir
  const yenileIdempotencyVeState = () => {
    setIdempotencyKey(UUIDUret())
    setAlanHatalari({})
    setHata(null)
    setBilgiMesaji(null)
  }

  useEffect(() => {
    const makineleriYukle = async () => {
      setMakinelerYukleniyor(true)
      setMakineHatasi(null)
      try {
        const res = await makineleriGetir()
        setMakineler(res.results)
        if (res.results.length > 0) {
          setMakineId(String(res.results[0].id))
        }
      } catch (err: unknown) {
        const errorObj = err as { mesaj?: string; message?: string }
        setMakineHatasi(errorObj.mesaj ?? errorObj.message ?? 'Makine listesi alınamadı.')
      } finally {
        setMakinelerYukleniyor(false)
      }
    }
    void makineleriYukle()
  }, [])

  const alanDegistir = <K extends keyof RiskTahminiGirdi>(alan: K, deger: string) => {
    yenileIdempotencyVeState()
    if (alan === 'urun_tipi') {
      setGirdi((prev) => ({ ...prev, urun_tipi: deger as 'L' | 'M' | 'H' }))
    } else {
      const sayi = parseFloat(deger)
      setGirdi((prev) => ({ ...prev, [alan]: Number.isNaN(sayi) ? 0 : sayi }))
    }
  }

  const makineDegistir = (idStr: string) => {
    yenileIdempotencyVeState()
    setMakineId(idStr)
  }

  const zamanDegistir = (zamanStr: string) => {
    yenileIdempotencyVeState()
    setOlcumZamani(zamanStr)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!makineId) {
      setHata('Lütfen geçerli bir makine seçin.')
      return
    }

    setGonderiliyor(true)
    setHata(null)
    setBilgiMesaji(null)
    setTraceId(null)
    setAlanHatalari({})

    try {
      const isoZaman = new Date(olcumZamani).toISOString()
      const kayitRes = await kaliciTahminKaydiOlustur({
        makine_id: Number(makineId),
        olcum_zamani: isoZaman,
        kaynak: 'MANUEL',
        idempotency_key: idempotencyKey,
        sensor_verisi: girdi,
      })

      if (kayitRes.tekrarlandi) {
        setBilgiMesaji('Bu değerlendirme daha önce kaydedilmiş. Mevcut kayıt açılıyor…')
      } else {
        setBilgiMesaji('Değerlendirme başarıyla kaydedildi.')
      }

      setTimeout(() => {
        navigate(`/app/tahminler/${kayitRes.id}`)
      }, 750)
    } catch (err: unknown) {
      if (err instanceof ApiHatasi) {
        if (err.status === 409) {
          setHata('Bu kayıt isteği önceki bir işlemle çakıştı. Bilgileri kontrol edip yeni bir değerlendirme başlatın.')
        } else if (err.status === 400 && err.alanlar) {
          const cleanAlanlar: Record<string, string[]> = {}
          for (const [k, v] of Object.entries(err.alanlar)) {
            const cleanKey = k.replace(/^sensor_verisi\./, '')
            cleanAlanlar[cleanKey] = Array.isArray(v) ? v.map(String) : [String(v)]
          }
          setAlanHatalari(cleanAlanlar)
          setHata(err.message)
        } else {
          setHata(err.message)
        }
        setTraceId(err.traceId ?? null)
      } else {
        const genErr = err as { message?: string }
        setHata(genErr.message ?? 'Kayıt işlemi sırasında bir hata oluştu.')
      }
    } finally {
      setGonderiliyor(false)
    }
  }

  return (
    <div className="sayfa-konteyner">
      <div className="sayfa-baslik-alani">
        <div>
          <button
            type="button"
            className="buton-sekonder"
            onClick={() => navigate('/app/tahminler')}
            style={{ marginBottom: '12px', padding: '6px 12px', fontSize: '0.85rem' }}
          >
            <ArrowLeft size={16} />
            <span>Tahmin Geçmişine Dön</span>
          </button>
          <h1 className="sayfa-basligi">Yeni Kalıcı Değerlendirme</h1>
          <p className="sayfa-alt-basligi">
            Makine ve sensör ölçümlerini kurumsal bakım kaydı olarak saklayın ve karar destek çıktısı alın.
          </p>
        </div>
      </div>

      <div style={{ maxWidth: '960px' }}>
        <div className="dashboard-panel">
          <form onSubmit={(e) => void handleSubmit(e)}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Building2 size={20} color="var(--primary)" />
              <span>Ekipman ve Zaman Bağlamı</span>
            </h3>

            {makinelerYukleniyor ? (
              <LoadingSkeleton adet={2} />
            ) : makineHatasi ? (
              <ErrorState mesaj={makineHatasi} />
            ) : (
              <div className="form-grid-2" style={{ marginBottom: '24px' }}>
                <div>
                  <label htmlFor="makine_id">Makine Seçimi</label>
                  <select
                    id="makine_id"
                    value={makineId}
                    onChange={(e) => makineDegistir(e.target.value)}
                    disabled={gonderiliyor || makineler.length === 0}
                  >
                    {makineler.length === 0 ? (
                      <option value="">Aktif makine bulunamadı</option>
                    ) : (
                      makineler.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.kod} — {m.ad}
                        </option>
                      ))
                    )}
                  </select>
                  {alanHatalari.makine_id && (
                    <p className="alan-hatasi">{alanHatalari.makine_id.join(' ')}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="olcum_zamani">Ölçüm Zamanı</label>
                  <input
                    id="olcum_zamani"
                    type="datetime-local"
                    value={olcumZamani}
                    onChange={(e) => zamanDegistir(e.target.value)}
                    disabled={gonderiliyor}
                  />
                  {alanHatalari.olcum_zamani && (
                    <p className="alan-hatasi">{alanHatalari.olcum_zamani.join(' ')}</p>
                  )}
                </div>
              </div>
            )}

            <h3 style={{ margin: '24px 0 20px 0', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={20} color="var(--primary)" />
              <span>Sensör Ölçüm Değerleri</span>
            </h3>

            <div className="form-grid-2">
              <div>
                <label htmlFor="urun_tipi">Ürün Tipi</label>
                <select
                  id="urun_tipi"
                  value={girdi.urun_tipi}
                  onChange={(e) => alanDegistir('urun_tipi', e.target.value)}
                  disabled={gonderiliyor}
                >
                  <option value="L">Düşük Kalite (L)</option>
                  <option value="M">Orta Kalite (M)</option>
                  <option value="H">Yüksek Kalite (H)</option>
                </select>
                {alanHatalari['urun_tipi'] && (
                  <p className="alan-hatasi">{alanHatalari['urun_tipi'].join(' ')}</p>
                )}
              </div>

              <div>
                <label htmlFor="hava_sicakligi_k">
                  Hava Sıcaklığı <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>(290.0 - 310.0 K)</span>
                </label>
                <div className="input-birimli">
                  <input
                    id="hava_sicakligi_k"
                    type="number"
                    step="0.1"
                    min="290"
                    max="310"
                    value={girdi.hava_sicakligi_k}
                    onChange={(e) => alanDegistir('hava_sicakligi_k', e.target.value)}
                    disabled={gonderiliyor}
                  />
                  <span className="input-birim">K</span>
                </div>
                {(alanHatalari.hava_sicakligi_k || alanHatalari['sensor_verisi.hava_sicakligi_k']) && (
                  <p className="alan-hatasi">{(alanHatalari.hava_sicakligi_k || alanHatalari['sensor_verisi.hava_sicakligi_k']).join(' ')}</p>
                )}
              </div>

              <div>
                <label htmlFor="proses_sicakligi_k">
                  Proses Sıcaklığı <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>(300.0 - 320.0 K)</span>
                </label>
                <div className="input-birimli">
                  <input
                    id="proses_sicakligi_k"
                    type="number"
                    step="0.1"
                    min="300"
                    max="320"
                    value={girdi.proses_sicakligi_k}
                    onChange={(e) => alanDegistir('proses_sicakligi_k', e.target.value)}
                    disabled={gonderiliyor}
                  />
                  <span className="input-birim">K</span>
                </div>
                {(alanHatalari.proses_sicakligi_k || alanHatalari['sensor_verisi.proses_sicakligi_k']) && (
                  <p className="alan-hatasi">{(alanHatalari.proses_sicakligi_k || alanHatalari['sensor_verisi.proses_sicakligi_k']).join(' ')}</p>
                )}
              </div>

              <div>
                <label htmlFor="donus_hizi_rpm">
                  Dönüş Hızı <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>(1000 - 3200 rpm)</span>
                </label>
                <div className="input-birimli">
                  <input
                    id="donus_hizi_rpm"
                    type="number"
                    step="1"
                    min="1000"
                    max="3200"
                    value={girdi.donus_hizi_rpm}
                    onChange={(e) => alanDegistir('donus_hizi_rpm', e.target.value)}
                    disabled={gonderiliyor}
                  />
                  <span className="input-birim">rpm</span>
                </div>
                {(alanHatalari.donus_hizi_rpm || alanHatalari['sensor_verisi.donus_hizi_rpm']) && (
                  <p className="alan-hatasi">{(alanHatalari.donus_hizi_rpm || alanHatalari['sensor_verisi.donus_hizi_rpm']).join(' ')}</p>
                )}
              </div>

              <div>
                <label htmlFor="tork_nm">
                  Tork <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>(1.0 - 90.0 Nm)</span>
                </label>
                <div className="input-birimli">
                  <input
                    id="tork_nm"
                    type="number"
                    step="0.1"
                    min="1"
                    max="90"
                    value={girdi.tork_nm}
                    onChange={(e) => alanDegistir('tork_nm', e.target.value)}
                    disabled={gonderiliyor}
                  />
                  <span className="input-birim">Nm</span>
                </div>
                {(alanHatalari.tork_nm || alanHatalari['sensor_verisi.tork_nm']) && (
                  <p className="alan-hatasi">{(alanHatalari.tork_nm || alanHatalari['sensor_verisi.tork_nm']).join(' ')}</p>
                )}
              </div>

              <div className="form-grid-tam">
                <label htmlFor="takim_asinmasi_dk">
                  Takım Aşınması <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>(0 - 300 dk)</span>
                </label>
                <div className="input-birimli">
                  <input
                    id="takim_asinmasi_dk"
                    type="number"
                    step="1"
                    min="0"
                    max="300"
                    value={girdi.takim_asinmasi_dk}
                    onChange={(e) => alanDegistir('takim_asinmasi_dk', e.target.value)}
                    disabled={gonderiliyor}
                  />
                  <span className="input-birim">dk</span>
                </div>
                {(alanHatalari.takim_asinmasi_dk || alanHatalari['sensor_verisi.takim_asinmasi_dk']) && (
                  <p className="alan-hatasi">{(alanHatalari.takim_asinmasi_dk || alanHatalari['sensor_verisi.takim_asinmasi_dk']).join(' ')}</p>
                )}
              </div>
            </div>

            {bilgiMesaji && (
              <div className="empty-state" style={{ padding: '12px', background: 'var(--status-success-bg)', color: 'var(--status-success-text)', borderRadius: '8px', marginTop: '16px' }}>
                <p style={{ margin: 0, fontWeight: 600 }}>{bilgiMesaji}</p>
              </div>
            )}

            {hata && <ErrorState mesaj={hata} traceId={traceId} />}

            <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
              <button
                type="submit"
                className="buton-primer"
                disabled={gonderiliyor || makinelerYukleniyor || makineler.length === 0}
              >
                {gonderiliyor ? (
                  <>
                    <Activity size={18} className="animate-spin" />
                    <span>Kaydediliyor…</span>
                  </>
                ) : (
                  <>
                    <Save size={18} />
                    <span>Değerlendirmeyi Kaydet</span>
                  </>
                )}
              </button>

              <button
                type="button"
                className="buton-sekonder"
                disabled={gonderiliyor}
                onClick={() => navigate('/app/tahminler')}
              >
                İptal
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
