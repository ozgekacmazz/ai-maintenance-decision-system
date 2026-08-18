import { useState, type FormEvent } from 'react'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Info,
  TrendingDown,
  TrendingUp,
  Minus,
} from 'lucide-react'

import { hizliRiskTahmini } from '../api/tahminler'
import type { RiskTahminiGirdi, RiskTahminiYaniti } from '../types/tahminler'
import {
  arizaTipiMetni,
  yonMetni,
} from '../types/tahminler'
import { ApiHatasi } from '../types/apiHata'
import { ErrorState } from '../components/feedback/ErrorState'

const VARSAYILAN_GIRDI: RiskTahminiGirdi = {
  urun_tipi: 'L',
  hava_sicakligi_k: 298.1,
  proses_sicakligi_k: 308.6,
  donus_hizi_rpm: 1551,
  tork_nm: 42.8,
  takim_asinmasi_dk: 0,
}

export function HizliAnaliz() {
  const [girdi, setGirdi] = useState<RiskTahminiGirdi>(VARSAYILAN_GIRDI)
  const [analizEdiliyor, setAnalizEdiliyor] = useState(false)
  const [sonuc, setSonuc] = useState<RiskTahminiYaniti | null>(null)
  const [hata, setHata] = useState<string | null>(null)
  const [alanHatalari, setAlanHatalari] = useState<Record<string, string[]>>({})
  const [traceId, setTraceId] = useState<string | null>(null)
  const [teknikAcik, setTeknikAcik] = useState(false)

  function alanDegistir(anahtar: keyof RiskTahminiGirdi, deger: string) {
    setGirdi((onceki) => ({
      ...onceki,
      [anahtar]: anahtar === 'urun_tipi' ? (deger as 'L' | 'M' | 'H') : parseFloat(deger) || 0,
    }))
    if (alanHatalari[anahtar]) {
      setAlanHatalari((onceki) => {
        const yeni = { ...onceki }
        delete yeni[anahtar]
        return yeni
      })
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setAnalizEdiliyor(true)
    setHata(null)
    setAlanHatalari({})
    setTraceId(null)

    try {
      const res = await hizliRiskTahmini(girdi)
      setSonuc(res)
    } catch (err: unknown) {
      if (err instanceof ApiHatasi) {
        setHata(err.message)
        setTraceId(err.traceId ?? null)
        if (err.alanlar && typeof err.alanlar === 'object') {
          const formatted: Record<string, string[]> = {}
          for (const [k, v] of Object.entries(err.alanlar)) {
            formatted[k] = Array.isArray(v) ? v.map(String) : [String(v)]
          }
          setAlanHatalari(formatted)
        }
      } else {
        const errObj = err as { mesaj?: string; message?: string }
        setHata(errObj.mesaj ?? errObj.message ?? 'Analiz işlemi tamamlanamadı.')
      }
    } finally {
      setAnalizEdiliyor(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div>
        <h2>Hızlı Sensör Analizi</h2>
        <p className="aciklama" style={{ margin: 0 }}>
          Sensör ölçüm değerlerini girerek anlık arıza riski ve karar desteği elde edin.
        </p>
      </div>

      <div className="analiz-layout">
        {/* Form Alanı */}
        <div className="dashboard-panel">
          <h3 style={{ marginBottom: '20px' }}>Sensör Ölçüm Değerleri</h3>

          <form onSubmit={(e) => void submit(e)}>
            <div className="form-grid">
              <div className="form-grid-tam">
                <label htmlFor="urun_tipi">Ürün Tipi</label>
                <select
                  id="urun_tipi"
                  value={girdi.urun_tipi}
                  onChange={(e) => alanDegistir('urun_tipi', e.target.value)}
                >
                  <option value="L">L (Hafif Üretim / Kalite L)</option>
                  <option value="M">M (Orta Üretim / Kalite M)</option>
                  <option value="H">H (Ağır Üretim / Kalite H)</option>
                </select>
                {alanHatalari.urun_tipi && (
                  <p className="alan-hatasi">{alanHatalari.urun_tipi.join(' ')}</p>
                )}
              </div>

              <div>
                <label htmlFor="hava_sicakligi_k">Hava Sıcaklığı</label>
                <div className="input-birimli">
                  <input
                    id="hava_sicakligi_k"
                    type="number"
                    step="0.1"
                    min="0"
                    value={girdi.hava_sicakligi_k}
                    onChange={(e) => alanDegistir('hava_sicakligi_k', e.target.value)}
                  />
                  <span className="input-birim">K</span>
                </div>
                {alanHatalari.hava_sicakligi_k && (
                  <p className="alan-hatasi">{alanHatalari.hava_sicakligi_k.join(' ')}</p>
                )}
              </div>

              <div>
                <label htmlFor="proses_sicakligi_k">Proses Sıcaklığı</label>
                <div className="input-birimli">
                  <input
                    id="proses_sicakligi_k"
                    type="number"
                    step="0.1"
                    min="0"
                    value={girdi.proses_sicakligi_k}
                    onChange={(e) => alanDegistir('proses_sicakligi_k', e.target.value)}
                  />
                  <span className="input-birim">K</span>
                </div>
                {alanHatalari.proses_sicakligi_k && (
                  <p className="alan-hatasi">{alanHatalari.proses_sicakligi_k.join(' ')}</p>
                )}
              </div>

              <div>
                <label htmlFor="donus_hizi_rpm">Dönüş Hızı</label>
                <div className="input-birimli">
                  <input
                    id="donus_hizi_rpm"
                    type="number"
                    step="1"
                    min="0"
                    value={girdi.donus_hizi_rpm}
                    onChange={(e) => alanDegistir('donus_hizi_rpm', e.target.value)}
                  />
                  <span className="input-birim">rpm</span>
                </div>
                {alanHatalari.donus_hizi_rpm && (
                  <p className="alan-hatasi">{alanHatalari.donus_hizi_rpm.join(' ')}</p>
                )}
              </div>

              <div>
                <label htmlFor="tork_nm">Tork</label>
                <div className="input-birimli">
                  <input
                    id="tork_nm"
                    type="number"
                    step="0.1"
                    min="0"
                    value={girdi.tork_nm}
                    onChange={(e) => alanDegistir('tork_nm', e.target.value)}
                  />
                  <span className="input-birim">Nm</span>
                </div>
                {alanHatalari.tork_nm && (
                  <p className="alan-hatasi">{alanHatalari.tork_nm.join(' ')}</p>
                )}
              </div>

              <div className="form-grid-tam">
                <label htmlFor="takim_asinmasi_dk">Takım Aşınması</label>
                <div className="input-birimli">
                  <input
                    id="takim_asinmasi_dk"
                    type="number"
                    step="1"
                    min="0"
                    value={girdi.takim_asinmasi_dk}
                    onChange={(e) => alanDegistir('takim_asinmasi_dk', e.target.value)}
                  />
                  <span className="input-birim">dakika</span>
                </div>
                {alanHatalari.takim_asinmasi_dk && (
                  <p className="alan-hatasi">{alanHatalari.takim_asinmasi_dk.join(' ')}</p>
                )}
              </div>
            </div>

            {hata && <ErrorState mesaj={hata} traceId={traceId} />}

            <button
              type="submit"
              disabled={analizEdiliyor}
              style={{ marginTop: '12px' }}
            >
              {analizEdiliyor ? (
                <>
                  <Activity size={18} className="animate-spin" />
                  <span>Sensör Analizi Yapılıyor…</span>
                </>
              ) : (
                <>
                  <Activity size={18} />
                  <span>Sensör Analizini Başlat</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Sonuç Paneli */}
        <div className="analiz-sonuc-paneli">
          {sonuc ? (
            <>
              {/* Main Result Card */}
              <div className="sonuc-hero-kart">
                <span className="urun">Analiz Değerlendirmesi</span>

                <div className={`sonuc-hero-yuzde ${sonuc.risk_uyarisi ? '' : 'dusuk'}`}>
                  %{Math.round(sonuc.risk_orani * 100)}
                </div>

                <div className="sonuc-hero-mesaj">
                  {sonuc.risk_uyarisi ? (
                    <div style={{ color: 'var(--status-critical-text)', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' }}>
                      <AlertTriangle size={20} />
                      <span>Bu ölçüm bakım açısından incelenmeli.</span>
                    </div>
                  ) : (
                    <div style={{ color: 'var(--status-success-text)', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' }}>
                      <CheckCircle2 size={20} />
                      <span>Bu ölçümde belirgin bir arıza sinyali görülmedi.</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Physical Failure Type Breakdown */}
              {sonuc.ariza_tipi_degerlendirmesi && (
                <div className="dashboard-panel" style={{ padding: '20px' }}>
                  <h4 style={{ margin: '0 0 12px 0', fontSize: '0.95rem', fontWeight: 700 }}>
                    Fiziksel Arıza Tipi Görünümü
                  </h4>

                  {sonuc.ariza_tipi_degerlendirmesi.guvenilir_adaylar.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {sonuc.ariza_tipi_degerlendirmesi.guvenilir_adaylar.map((aday) => (
                        <div
                          key={aday.kod}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: '10px 14px',
                            background: 'var(--status-critical-bg)',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--status-critical-border)',
                          }}
                        >
                          <span style={{ fontWeight: 700, color: 'var(--status-critical-text)' }}>
                            {arizaTipiMetni(aday.kod)} ({aday.kod})
                          </span>
                          <span style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--status-critical-text)' }}>
                            %{Math.round(aday.olasilik * 100)} olasılık
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : sonuc.ariza_tipi_degerlendirmesi.belirsiz_fiziksel_tip ? (
                    <div className="bilgi" style={{ margin: 0 }}>
                      <p style={{ margin: 0, fontWeight: 600 }}>
                        Risk sinyali var ancak güvenilir bir fiziksel arıza tipi belirlenemedi. Teknik inceleme önerilir.
                      </p>
                    </div>
                  ) : (
                    <p style={{ margin: 0, fontSize: '0.88rem', color: 'var(--text-muted)' }}>
                      Öne çıkan belirgin bir fiziksel arıza tipi tespit edilmedi.
                    </p>
                  )}

                  {/* TWF Experimental Signal Warning */}
                  {sonuc.ariza_tipi_degerlendirmesi.deneysel_sinyaller.some((s) => s.esik_asildi) && (
                    <div className="hata" style={{ marginTop: '12px', marginBottom: 0, fontSize: '0.88rem' }}>
                      <strong>Deneysel Sinyal:</strong> Takım aşınması sinyali algılandı (Veri desteği sınırlı).
                    </div>
                  )}
                </div>
              )}

              {/* Explainability / Top Feature Impacts */}
              {sonuc.aciklanabilirlik?.risk_aciklamasi?.ilk_etkiler &&
                sonuc.aciklanabilirlik.risk_aciklamasi.ilk_etkiler.length > 0 && (
                  <div className="dashboard-panel" style={{ padding: '20px' }}>
                    <h4 style={{ margin: '0 0 16px 0', fontSize: '0.95rem', fontWeight: 700 }}>
                      Riski Etkileyen Başlıca Değerler
                    </h4>

                    <div className="etki-kartlari-grid">
                      {sonuc.aciklanabilirlik.risk_aciklamasi.ilk_etkiler.map((etki) => {
                        const deger =
                          typeof etki.original_feature_value === 'boolean'
                            ? etki.original_feature_value
                              ? 'Evet'
                              : 'Hayır'
                            : typeof etki.original_feature_value === 'number'
                            ? etki.original_feature_value.toLocaleString('tr-TR', { maximumFractionDigits: 2 })
                            : String(etki.original_feature_value)

                        let yonCls = 'etki-yon notr'
                        let YonIkon = Minus
                        if (etki.yon === 'RISKI_ARTIRIR') {
                          yonCls = 'etki-yon artirir'
                          YonIkon = TrendingUp
                        } else if (etki.yon === 'RISKI_AZALTIR') {
                          yonCls = 'etki-yon azaltir'
                          YonIkon = TrendingDown
                        }

                        return (
                          <div key={etki.feature} className="etki-karti">
                            <div className="etki-sol">
                              <span className="etki-adi">{etki.gorunen_ad}</span>
                              <span className="etki-deger">
                                Ölçülen: <strong>{deger}</strong> {etki.birim ?? ''}
                              </span>
                            </div>

                            <div className={yonCls}>
                              <YonIkon size={14} />
                              <span>{yonMetni(etki.yon)}</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

              {/* Collapsible Technical Details */}
              <div className="teknik-akordeon">
                <button
                  type="button"
                  className="teknik-akordeon-butonu"
                  onClick={() => setTeknikAcik(!teknikAcik)}
                >
                  <span>Teknik Detaylar ve Model Sürümü</span>
                  {teknikAcik ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {teknikAcik && (
                  <div className="teknik-akordeon-icerik">
                    <div><strong>Model Sürümü:</strong> {sonuc.model_version}</div>
                    <div><strong>Pipeline Sürümü:</strong> {sonuc.pipeline_version}</div>
                    <div><strong>Karar Eşik Değeri:</strong> {sonuc.threshold.toFixed(4)}</div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="dashboard-panel" style={{ textAlign: 'center', padding: '48px 24px' }}>
              <div className="empty-state-ikon" style={{ margin: '0 auto 16px auto' }}>
                <Info size={28} />
              </div>
              <h3 style={{ margin: '0 0 8px 0' }}>Analiz sonucu burada görüntülenecek.</h3>
              <p className="aciklama" style={{ margin: 0 }}>
                Sensör ölçüm değerlerini girip analizi başlatın.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
