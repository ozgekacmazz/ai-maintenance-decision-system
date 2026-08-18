import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  AlertTriangle,
  Cpu,
  PackageCheck,
  PackageX,
  PackageSearch,
  Wrench,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react'
import { tahminKaydiDetayiGetir } from '../api/tahminler'
import type { TahminKaydiDetay } from '../types/tahminler'
import {
  anaAksiyonMetni,
  arizaTipiMetni,
  destekleyiciAksiyonMetni,
  kararGuveniMetni,
  kaynakMetni,
  oncelikSeviyesiMetni,
  sayiFormatla,
  urunTipiMetni,
  yonMetni,
} from '../types/tahminler'
import { ApiHatasi } from '../types/apiHata'
import { StatusBadge } from '../components/feedback/StatusBadge'
import { MetricCard } from '../components/data-display/MetricCard'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { ErrorState } from '../components/feedback/ErrorState'

export function TahminDetay() {
  const { tahminId } = useParams<{ tahminId: string }>()
  const navigate = useNavigate()

  const [yukleniyor, setYukleniyor] = useState(true)
  const [hata, setHata] = useState<string | null>(null)
  const [durumKodu, setDurumKodu] = useState<number | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [kayit, setKayit] = useState<TahminKaydiDetay | null>(null)

  // Akordeon durumları
  const [teknikAcik, setTeknikAcik] = useState(false)

  useEffect(() => {
    if (!tahminId) return

    const veriGetir = async () => {
      setYukleniyor(true)
      setHata(null)
      setDurumKodu(null)
      setTraceId(null)

      try {
        const res = await tahminKaydiDetayiGetir(tahminId)
        setKayit(res)
      } catch (err: unknown) {
        if (err instanceof ApiHatasi) {
          setDurumKodu(err.status)
          setHata(err.message)
          setTraceId(err.traceId ?? null)
        } else {
          const genErr = err as { message?: string }
          setHata(genErr.message ?? 'Kayıt detayları yüklenirken bir hata oluştu.')
        }
      } finally {
        setYukleniyor(false)
      }
    }

    void veriGetir()
  }, [tahminId])

  if (yukleniyor) {
    return (
      <div className="sayfa-konteyner">
        <LoadingSkeleton adet={8} />
      </div>
    )
  }

  if (hata || !kayit) {
    if (durumKodu === 404) {
      return (
        <div className="sayfa-konteyner">
          <div className="dashboard-panel" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <HelpCircle size={48} color="var(--text-secondary)" style={{ margin: '0 auto 16px auto' }} />
            <h2>Değerlendirme Bulunamadı</h2>
            <p className="aciklama" style={{ marginBottom: '24px' }}>
              Aradığınız {tahminId} numaralı tahmin kaydı sistemde bulunamadı veya silinmiş olabilir.
            </p>
            <button
              type="button"
              className="buton-primer"
              onClick={() => navigate('/app/tahminler')}
            >
              <ArrowLeft size={18} />
              <span>Tahmin Geçmişine Dön</span>
            </button>
          </div>
        </div>
      )
    }

    if (durumKodu === 403) {
      return (
        <div className="sayfa-konteyner">
          <div className="dashboard-panel" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <AlertTriangle size={48} color="var(--status-critical-text)" style={{ margin: '0 auto 16px auto' }} />
            <h2>Erişim Yetkisi Yok</h2>
            <p className="aciklama" style={{ marginBottom: '24px' }}>
              Bu değerlendirme kaydını görüntülemek için gerekli yetkiniz bulunmamaktadır.
            </p>
            <button
              type="button"
              className="buton-primer"
              onClick={() => navigate('/app/tahminler')}
            >
              <ArrowLeft size={18} />
              <span>Tahmin Geçmişine Dön</span>
            </button>
          </div>
        </div>
      )
    }

    return (
      <div className="sayfa-konteyner">
        <ErrorState
          mesaj={hata ?? 'Kayıt detayları yüklenemedi.'}
          traceId={traceId}
          onRetry={() => {
            if (tahminId) void tahminKaydiDetayiGetir(tahminId).then(setKayit)
          }}
        />
      </div>
    )
  }

  const { tahmin, makine, sensor_snapshot, bakim_karari } = kayit

  return (
    <div className="sayfa-konteyner">
      {/* Üst Navigasyon ve Başlık */}
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <h1 className="sayfa-basligi">{makine.ad} Değerlendirmesi</h1>
            <span className="etiket">{makine.kod}</span>
            <span className="etiket">{kaynakMetni(kayit.kaynak)}</span>
          </div>
          <p className="sayfa-alt-basligi">
            Ölçüm Zamanı: {new Date(kayit.olcum_zamani).toLocaleString('tr-TR')} (Oluşturulma: {new Date(kayit.olusturulma_zamani).toLocaleString('tr-TR')})
          </p>
        </div>
      </div>

      {/* Hero Özet Kartı */}
      <div className="dashboard-grid" style={{ marginBottom: '24px' }}>
        <MetricCard
          baslik="Hesaplanan Risk Oranı"
          deger={`%${Math.round(tahmin.risk_orani * 100)}`}
          aciklama={tahmin.risk_uyarisi ? 'Risk eşiği aşıldı' : 'Normal (Risk uyarısı yok)'}
          varyant={tahmin.risk_uyarisi ? 'kritik' : 'varsayilan'}
        />

        <MetricCard
          baslik="Nihai Bakım Önceliği"
          deger={bakim_karari ? oncelikSeviyesiMetni(bakim_karari.oncelik_seviyesi) : 'Belirtilmedi'}
          aciklama={bakim_karari ? anaAksiyonMetni(bakim_karari.ana_aksiyon) : 'Karar henüz üretilmedi'}
          varyant={bakim_karari?.oncelik_seviyesi === 'KRITIK' ? 'kritik' : 'varsayilan'}
        />

        <MetricCard
          baslik="Karar Güven Seviyesi"
          deger={bakim_karari ? kararGuveniMetni(bakim_karari.karar_guveni) : 'Belirtilmedi'}
          aciklama="Model ve kural motoru tutarlılığı"
          varyant="varsayilan"
        />
      </div>

      {/* Bakım Kararı Özeti */}
      {bakim_karari && (
        <div className="dashboard-panel" style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Wrench size={22} color="var(--primary)" />
            <h3 style={{ margin: 0 }}>Sistem Bakım Kararı</h3>
            <StatusBadge oncelik={bakim_karari.oncelik_seviyesi} />
          </div>

          <div className="dashboard-grid" style={{ marginBottom: '20px' }}>
            <div className="metrik-kart">
              <span className="etiket">Teknik Aciliyet Skoru</span>
              <div className="deger" style={{ fontSize: '1.5rem', marginTop: '4px' }}>
                {bakim_karari.teknik_aciliyet_skoru} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>/ 100</span>
              </div>
            </div>

            <div className="metrik-kart">
              <span className="etiket">Tedarik Riski Skoru</span>
              <div className="deger" style={{ fontSize: '1.5rem', marginTop: '4px' }}>
                {bakim_karari.tedarik_riski_skoru} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>/ 100</span>
              </div>
            </div>

            <div className="metrik-kart">
              <span className="etiket">Nihai Öncelik Skoru</span>
              <div className="deger" style={{ fontSize: '1.5rem', marginTop: '4px' }}>
                {bakim_karari.nihai_oncelik_skoru} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>/ 100</span>
              </div>
            </div>
          </div>

          {/* Karar Gerekçeleri */}
          {bakim_karari.gerekceler && bakim_karari.gerekceler.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <h4 style={{ margin: '0 0 8px 0', fontSize: '0.95rem' }}>Karar Gerekçeleri</h4>
              <ul style={{ margin: 0, paddingLeft: '20px', color: 'var(--text-main)', fontSize: '0.9rem' }}>
                {bakim_karari.gerekceler.map((g, idx) => (
                  <li key={idx} style={{ marginBottom: '4px' }}>
                    {g.mesaj}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Destekleyici Aksiyonlar */}
          {bakim_karari.destekleyici_aksiyonlar && bakim_karari.destekleyici_aksiyonlar.length > 0 && (
            <div style={{ marginBottom: '16px' }}>
              <h4 style={{ margin: '0 0 8px 0', fontSize: '0.95rem' }}>Önerilen Destekleyici Aksiyonlar</h4>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {bakim_karari.destekleyici_aksiyonlar.map((aksiyon, idx) => (
                  <span key={idx} className="etiket" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                    {destekleyiciAksiyonMetni(aksiyon)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Karar Uyarıları */}
          {bakim_karari.uyarilar && bakim_karari.uyarilar.length > 0 && (
            <div style={{ background: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)', borderRadius: '8px', padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-warning-text)', fontWeight: 600, marginBottom: '6px' }}>
                <AlertTriangle size={18} />
                <span>Sistem Uyarısı</span>
              </div>
              {bakim_karari.uyarilar.map((u, idx) => (
                <p key={idx} style={{ margin: 0, fontSize: '0.875rem', color: 'var(--status-warning-text)' }}>
                  {u.mesaj}
                </p>
              ))}
            </div>
          )}

          <p style={{ margin: '16px 0 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
            Sistem karar desteği sağlar; otomatik makine durdurma komutu üretmez.
          </p>
        </div>
      )}

      {/* Sensör Snapshot Bölümü (Read-Only) */}
      <div className="dashboard-panel" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          <Cpu size={20} color="var(--primary)" />
          <h3 style={{ margin: 0 }}>Ölçeğin Alındığı Anki Sensör Değerleri</h3>
        </div>
        <p className="aciklama" style={{ marginBottom: '16px' }}>
          Bu değerler değerlendirme oluşturulduğu andaki ölçümleri gösterir.
        </p>

        <div className="dashboard-grid">
          <div className="metrik-kart">
            <span className="etiket">Ürün Tipi</span>
            <div className="deger" style={{ fontSize: '1.25rem' }}>
              {urunTipiMetni(sensor_snapshot.urun_tipi)}
            </div>
          </div>

          <div className="metrik-kart">
            <span className="etiket">Hava Sıcaklığı</span>
            <div className="deger" style={{ fontSize: '1.25rem' }}>
              {sayiFormatla(sensor_snapshot.hava_sicakligi_k)} <span style={{ fontSize: '0.85rem' }}>K</span>
            </div>
          </div>

          <div className="metrik-kart">
            <span className="etiket">Proses Sıcaklığı</span>
            <div className="deger" style={{ fontSize: '1.25rem' }}>
              {sayiFormatla(sensor_snapshot.proses_sicakligi_k)} <span style={{ fontSize: '0.85rem' }}>K</span>
            </div>
          </div>

          <div className="metrik-kart">
            <span className="etiket">Dönüş Hızı</span>
            <div className="deger" style={{ fontSize: '1.25rem' }}>
              {sayiFormatla(sensor_snapshot.donus_hizi_rpm, 0)} <span style={{ fontSize: '0.85rem' }}>rpm</span>
            </div>
          </div>

          <div className="metrik-kart">
            <span className="etiket">Tork</span>
            <div className="deger" style={{ fontSize: '1.25rem' }}>
              {sayiFormatla(sensor_snapshot.tork_nm)} <span style={{ fontSize: '0.85rem' }}>Nm</span>
            </div>
          </div>

          <div className="metrik-kart">
            <span className="etiket">Takım Aşınması</span>
            <div className="deger" style={{ fontSize: '1.25rem' }}>
              {sayiFormatla(sensor_snapshot.takim_asinmasi_dk, 0)} <span style={{ fontSize: '0.85rem' }}>dakika</span>
            </div>
          </div>
        </div>
      </div>

      {/* Physical Failure Types */}
      <div className="dashboard-panel" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '1.05rem' }}>Fiziksel Arıza Tipi Değerlendirmesi</h3>

        {kayit.belirsiz_fiziksel_tip ? (
          <div style={{ padding: '16px', background: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)', borderRadius: '8px' }}>
            <p style={{ margin: 0, color: 'var(--status-warning-text)', fontWeight: 600 }}>
              Risk sinyali var ancak güvenilir bir fiziksel arıza tipi belirlenemedi. Teknik inceleme önerilir.
            </p>
          </div>
        ) : kayit.ariza_tipleri && kayit.ariza_tipleri.length > 0 ? (
          <div style={{ display: 'grid', gap: '12px' }}>
            {kayit.ariza_tipleri.map((at) => (
              <div
                key={at.id}
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
                  <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                    {arizaTipiMetni(at.kod)} <span className="etiket">({at.kod})</span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    Olasılık: %{Math.round(at.olasilik * 100)} (Karar Eşiği: %{Math.round(at.threshold * 100)})
                  </div>
                </div>

                <div>
                  {at.deneysel || at.kod === 'TWF' ? (
                    <span className="etiket uyari" style={{ background: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)', color: 'var(--status-warning-text)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <AlertTriangle size={14} />
                      <span>Deneysel sinyal (Veri desteği sınırlı)</span>
                    </span>
                  ) : at.guvenilir ? (
                    <span className="etiket basarili" style={{ background: 'var(--status-success-bg)', border: '1px solid var(--status-success-border)', color: 'var(--status-success-text)' }}>
                      Güvenilir Aday
                    </span>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="aciklama" style={{ margin: 0 }}>
            Bu değerlendirmede eşik üzeri fiziksel arıza tipi belirlenmemiştir.
          </p>
        )}
      </div>

      {/* SHAP / Model Feature Impacts */}
      {kayit.shap_etkileri && kayit.shap_etkileri.length > 0 && (
        <div className="dashboard-panel" style={{ marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 4px 0', fontSize: '1.05rem' }}>Riski Etkileyen Başlıca Değerler</h3>
          <p className="aciklama" style={{ marginBottom: '16px' }}>
            Bu göstergeler model kararını etkileyen ölçümleri açıklar; kesin fiziksel arıza nedenini kanıtlamaz.
          </p>

          <div style={{ display: 'grid', gap: '12px' }}>
            {kayit.shap_etkileri.map((etki, idx) => {
              const Icon = etki.yon === 'RISKI_ARTIRIR' ? TrendingUp : etki.yon === 'RISKI_AZALTIR' ? TrendingDown : Minus
              const color = etki.yon === 'RISKI_ARTIRIR' ? 'var(--status-critical-text)' : etki.yon === 'RISKI_AZALTIR' ? 'var(--status-success-text)' : 'var(--text-secondary)'

              return (
                <div
                  key={idx}
                  style={{
                    padding: '12px 16px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600 }}>{etki.gorunen_ad}</div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Ölçülen: <strong>{sayiFormatla(etki.original_feature_value)}</strong> {etki.birim ?? ''}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color, fontWeight: 600, fontSize: '0.9rem' }}>
                    <Icon size={16} />
                    <span>{yonMetni(etki.yon)}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ERP Snapshot Section */}
      <div className="dashboard-panel" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '1.05rem' }}>Parça ve Stok Durumu</h3>

        {!kayit.erp_snapshotlari || kayit.erp_snapshotlari.length === 0 ? (
          <div style={{ padding: '16px', background: 'var(--bg-secondary)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <PackageSearch size={24} color="var(--text-secondary)" />
            <p className="aciklama" style={{ margin: 0 }}>
              Bu değerlendirme için doğrulanmış parça eşlemesi bulunmuyor.
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '12px' }}>
            {kayit.erp_snapshotlari.map((erp) => {
              const stokYok = erp.stok_durumu === 'KAYIT_YOK'
              const stokSifir = erp.stok_durumu === 'MEVCUT' && erp.kullanilabilir_stok === 0

              return (
                <div
                  key={erp.id}
                  style={{
                    padding: '16px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <strong style={{ fontSize: '1rem' }}>{erp.parca_adi_snapshot}</strong>
                      <span className="etiket">{erp.parca_kodu_snapshot}</span>
                      <span className="etiket" style={{ background: 'var(--bg-secondary)' }}>
                        {arizaTipiMetni(erp.ariza_tipi)}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                      <span>Gerekli Miktar: <strong>{erp.gerekli_miktar} adet</strong></span>

                      {stokYok ? (
                        <span style={{ color: 'var(--status-warning-text)', fontWeight: 600 }}>
                          ERP stok kaydı bulunamadı
                        </span>
                      ) : stokSifir ? (
                        <span style={{ color: 'var(--status-critical-text)', fontWeight: 600 }}>
                          Stok: 0 adet
                        </span>
                      ) : (
                        <span>Stok: <strong>{erp.kullanilabilir_stok ?? 0} adet</strong> (Min: {erp.minimum_stok ?? '-'})</span>
                      )}

                      {erp.tedarik_gun !== null && (
                        <span>Tedarik Süresi: <strong>{erp.tedarik_gun} gün</strong></span>
                      )}
                    </div>

                    {erp.onerilen_aksiyon_snapshot && (
                      <p style={{ margin: '8px 0 0 0', fontSize: '0.85rem', color: 'var(--text-main)' }}>
                        Önerilen Aksiyon: <em>{erp.onerilen_aksiyon_snapshot}</em>
                      </p>
                    )}
                  </div>

                  <div>
                    {stokYok ? (
                      <span className="etiket" style={{ background: 'var(--status-warning-bg)', color: 'var(--status-warning-text)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <PackageSearch size={14} />
                        Stok Kaydı Eksik
                      </span>
                    ) : erp.stok_yeterli ? (
                      <span className="etiket" style={{ background: 'var(--status-success-bg)', color: 'var(--status-success-text)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <PackageCheck size={14} />
                        Stok Yeterli
                      </span>
                    ) : (
                      <span className="etiket" style={{ background: 'var(--status-critical-bg)', color: 'var(--status-critical-text)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <PackageX size={14} />
                        Stok Yetersiz
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Collapsible Technical Details */}
      <div className="teknik-akordeon">
        <button
          type="button"
          className="teknik-akordeon-butonu"
          onClick={() => setTeknikAcik(!teknikAcik)}
        >
          <span>Teknik Detaylar ve Model Metadata</span>
          {teknikAcik ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {teknikAcik && (
          <div className="teknik-akordeon-icerik">
            <div><strong>Tahmin Kayıt ID:</strong> {kayit.id}</div>
            <div><strong>Destek / Takip Kodu (Trace ID):</strong> {kayit.trace_id}</div>
            <div><strong>Binary Model Sürümü:</strong> {tahmin.model_version}</div>
            <div><strong>Binary Pipeline Sürümü:</strong> {tahmin.pipeline_version}</div>
            <div><strong>Binary Eşik Değeri:</strong> {tahmin.threshold.toFixed(4)}</div>
            {kayit.failure_type_model_version && (
              <div><strong>Fiziksel Tip Model Sürümü:</strong> {kayit.failure_type_model_version}</div>
            )}
            {bakim_karari?.motor_surumu && (
              <div><strong>Bakım Karar Motoru Sürümü:</strong> {bakim_karari.motor_surumu}</div>
            )}
            <div><strong>Oluşturan Kullanıcı:</strong> {kayit.olusturan.kullanici_adi} (ID: {kayit.olusturan.id})</div>
          </div>
        )}
      </div>
    </div>
  )
}
