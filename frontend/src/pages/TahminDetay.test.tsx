import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TahminDetay } from './TahminDetay'
import * as tahminApi from '../api/tahminler'
import type { TahminKaydiDetay } from '../types/tahminler'
import { ApiHatasi } from '../types/apiHata'

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_DETAIL_FULL: TahminKaydiDetay = {
  id: 'd9b3a1e2-4f5c-6b7a-8d9e-0f1a2b3c4d5e',
  tekrarlandi: false,
  makine: { id: 101, kod: 'M-101', ad: 'Pres Motoru 1', kritiklik_snapshot: 5 },
  olcum_zamani: '2026-08-19T10:30:00Z',
  olusturulma_zamani: '2026-08-19T10:30:05Z',
  kaynak: 'MANUEL',
  sensor_snapshot: {
    urun_tipi: 'M',
    hava_sicakligi_k: 300.0,
    proses_sicakligi_k: 310.0,
    donus_hizi_rpm: 1500,
    tork_nm: 40.0,
    takim_asinmasi_dk: 108,
  },
  tahmin: {
    risk_orani: 0.85,
    risk_uyarisi: true,
    threshold: 0.229,
    model_version: 'binary-failure-1.0.0',
    pipeline_version: '1.0.0',
    base_value: 0.1,
  },
  failure_type_durum: 'DEGERLENDIRILDI',
  failure_type_model_version: 'failure-type-1.0.0',
  failure_type_pipeline_version: '1.0.0',
  belirsiz_fiziksel_tip: false,
  aciklanabilirlik_durum: 'ACIKLANDI',
  ariza_tipleri: [
    {
      id: 1,
      kod: 'PWF',
      olasilik: 0.92,
      threshold: 0.29,
      esik_asildi: true,
      guvenilir: true,
      deneysel: false,
      guven_durumu: 'YETERLI_DESTEK',
      operasyonel_kullanima_uygun: true,
      siralama: 1,
      shap_etkileri: [],
    },
    {
      id: 2,
      kod: 'TWF',
      olasilik: 0.18,
      threshold: 0.05,
      esik_asildi: true,
      guvenilir: false,
      deneysel: true,
      guven_durumu: 'YETERSIZ_DESTEK',
      operasyonel_kullanima_uygun: false,
      siralama: 2,
      shap_etkileri: [],
    },
  ],
  shap_etkileri: [
    {
      feature: 'tork_nm',
      gorunen_ad: 'Tork',
      original_feature_value: 40.0,
      model_feature_value: 1.1,
      birim: 'Nm',
      shap_value: 0.45,
      yon: 'RISKI_ARTIRIR',
    },
  ],
  erp_snapshotlari: [
    {
      id: 10,
      ariza_tipi: 'PWF',
      parca_kodu_snapshot: 'PRC-001',
      parca_adi_snapshot: 'Güç Rlesi',
      gerekli_miktar: 1,
      stok_durumu: 'MEVCUT',
      toplam_stok: 0,
      kullanilabilir_stok: 0,
      minimum_stok: 2,
      tedarik_gun: 3,
      stok_yeterli: false,
      deneysel: false,
      onerilen_aksiyon_snapshot: 'Tedarik siparişi oluşturun.',
    },
    {
      id: 11,
      ariza_tipi: 'TWF',
      parca_kodu_snapshot: 'PRC-002',
      parca_adi_snapshot: 'Kesici Uç',
      gerekli_miktar: 2,
      stok_durumu: 'KAYIT_YOK',
      toplam_stok: null,
      kullanilabilir_stok: null,
      minimum_stok: null,
      tedarik_gun: null,
      stok_yeterli: false,
      deneysel: true,
      onerilen_aksiyon_snapshot: 'ERP eşlemesi kontrol edilmeli.',
    },
  ],
  olusturan: { id: 2, kullanici_adi: 'ozge.06' },
  trace_id: 'tr-998877',
  bakim_karari: {
    motor_surumu: 'maintenance-priority-1.0.0',
    teknik_aciliyet_skoru: 89,
    tedarik_riski_skoru: 10,
    nihai_oncelik_skoru: 75,
    oncelik_seviyesi: 'KRITIK',
    genel_oncelik: 4,
    stok_katsayisi: '1.10',
    ham_genel_oncelik: '4.6750',
    genel_oncelik_formul_surumu: 'general-priority-1.0.0',
    ana_aksiyon: 'ACIL_TEKNIK_DEGERLENDIRME',
    destekleyici_aksiyonlar: ['STOK_VERISINI_DOGRULA', 'TEDARIK_SURECINI_BASLAT'],
    ana_ariza_tipi: 'PWF',
    karar_guveni: 'YUKSEK',
    gerekceler: [
      {
        kod: 'RISK_HIGH',
        mesaj: 'Yüksek risk oranı nedeniyle acil teknik değerlendirme önerilir.',
        etki: 'ARTIRAN',
        puan_etkisi: 40,
      },
    ],
    uyarilar: [
      {
        kod: 'STOCK_ZERO',
        mesaj: 'Kullanılabilir stok tükenmiştir.',
      },
    ],
    olusturulma_zamani: '2026-08-19T10:30:05Z',
  },
  red_bilgisi: null,
  is_emri_bilgisi: null,
}

function renderComponent(tahminId = 'd9b3a1e2-4f5c-6b7a-8d9e-0f1a2b3c4d5e') {
  return render(
    <MemoryRouter initialEntries={[`/app/tahminler/${tahminId}`]}>
      <Routes>
        <Route path="/app/tahminler/:tahminId" element={<TahminDetay />} />
        <Route path="/app/tahminler" element={<div>Tahmin Gecmisi Sayfasi</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('TahminDetay', () => {
  it('tahmin detaylarını, sensör snapshot, ERP ve bakım kararlarını eksiksiz sunar', async () => {
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockResolvedValue(MOCK_DETAIL_FULL)
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('Pres Motoru 1 Değerlendirmesi')).toBeInTheDocument()
      expect(screen.getByText('M-101')).toBeInTheDocument()
      expect(screen.getByText('Manuel değerlendirme')).toBeInTheDocument()
      expect(screen.getByText('%85')).toBeInTheDocument()
      expect(screen.getByText('Risk eşiği aşıldı')).toBeInTheDocument()
    })

    // Sensör Snapshot
    expect(screen.getByText('Ölçeğin Alındığı Anki Sensör Değerleri')).toBeInTheDocument()
    expect(screen.getByText('1.500')).toBeInTheDocument()

    // Failure types (PWF & TWF experimental)
    expect(screen.getAllByText('Güç kaynaklı sorun').length).toBeGreaterThan(0)
    expect(screen.getByText('Deneysel sinyal (Veri desteği sınırlı)')).toBeInTheDocument()

    // SHAP user-friendly & formatted numeric value
    expect(screen.getByText('Riski Etkileyen Başlıca Değerler')).toBeInTheDocument()
    expect(screen.getByText('Riski artırıyor')).toBeInTheDocument()
    expect(screen.getAllByText('40').length).toBeGreaterThan(0)

    // ERP Stok Ayrımı (0 vs KAYIT_YOK)
    expect(screen.getByText('Stok: 0 adet')).toBeInTheDocument()
    expect(screen.getByText('ERP stok kaydı bulunamadı')).toBeInTheDocument()

    // Bakım Kararı & Skorlar
    expect(screen.getByText('Sistem Bakım Kararı')).toBeInTheDocument()
    expect(screen.getByText('89')).toBeInTheDocument()
    expect(screen.getByText('75')).toBeInTheDocument()
    expect(screen.getByText('Yüksek risk oranı nedeniyle acil teknik değerlendirme önerilir.')).toBeInTheDocument()
    expect(screen.getByText('Stok bilgisini doğrula')).toBeInTheDocument()
    expect(screen.getByText('Tedarik sürecini başlat')).toBeInTheDocument()
  })

  it('teknik detaylar akordeonu varsayılan olarak kapalıdır ve kullanıcı tıklandığında açılır', async () => {
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockResolvedValue(MOCK_DETAIL_FULL)
    renderComponent()

    await waitFor(() => expect(screen.getByText('Pres Motoru 1 Değerlendirmesi')).toBeInTheDocument())

    expect(screen.queryByText(/binary-failure-1.0.0/)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Teknik Detaylar/ }))
    expect(screen.getByText(/binary-failure-1.0.0/)).toBeInTheDocument()
    expect(screen.getByText(/tr-998877/)).toBeInTheDocument()
  })

  it('kararsız uygun tahminde onay ve red aksiyonlarını, onay modalında iş emri sonucunu açıkça gösterir', async () => {
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockResolvedValue(MOCK_DETAIL_FULL)
    renderComponent()

    await waitFor(() => expect(screen.getByRole('button', { name: 'Onayla' })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Reddet' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Onayla' }))

    expect(screen.getByText('Bakım Kararını Onayla')).toBeInTheDocument()
    expect(screen.getByText(/onayladığınızda bakım ekibi için bir iş emri oluşturulacaktır/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Onayla ve İş Emri Oluştur' })).toBeInTheDocument()
  })

  it('başarılı reddetmede güncel kaydı gösterir ve karar aksiyonlarını kaldırır', async () => {
    const reddedilmisKayit: TahminKaydiDetay = {
      ...MOCK_DETAIL_FULL,
      red_bilgisi: {
        reddeden: 'bakim.uzmani',
        reddetme_zamani: '2026-08-19T12:00:00Z',
        red_nedeni: 'Sensör kalibrasyonu bekleniyor.',
      },
    }
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockResolvedValue(MOCK_DETAIL_FULL)
    const reddetMock = vi.spyOn(tahminApi, 'tahminReddet').mockResolvedValue(reddedilmisKayit)
    renderComponent()

    await waitFor(() => expect(screen.getByRole('button', { name: 'Reddet' })).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: 'Reddet' }))
    await userEvent.type(screen.getByLabelText('Red nedeni (isteğe bağlı)'), 'Sensör kalibrasyonu bekleniyor.')
    await userEvent.click(screen.getByRole('button', { name: 'Reddetmeyi Onayla' }))

    await waitFor(() => expect(screen.getByText('Bu değerlendirme reddedildi')).toBeInTheDocument())
    expect(reddetMock).toHaveBeenCalledWith(MOCK_DETAIL_FULL.id, 'Sensör kalibrasyonu bekleniyor.')
    expect(screen.queryByText('Değerlendirmeyi Reddet')).not.toBeInTheDocument()
    expect(screen.getByText('Reddeden: bakim.uzmani')).toBeInTheDocument()
    expect(screen.getByText(/Tarih:/)).toBeInTheDocument()
    expect(screen.getByText('Neden: Sensör kalibrasyonu bekleniyor.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Onayla' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reddet' })).not.toBeInTheDocument()
  })

  it('reddetme hatasını modal içinde gösterir, kaydı değiştirmez ve tekrar denemeye izin verir', async () => {
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockResolvedValue(MOCK_DETAIL_FULL)
    const reddetMock = vi.spyOn(tahminApi, 'tahminReddet')
      .mockRejectedValueOnce(new ApiHatasi(503, 'SERVIS_HATASI', 'Reddetme tamamlanamadı.', {}, 'trace-red-1'))
      .mockResolvedValueOnce({
        ...MOCK_DETAIL_FULL,
        red_bilgisi: {
          reddeden: 'bakim.uzmani',
          reddetme_zamani: '2026-08-19T12:00:00Z',
          red_nedeni: 'Kullanıcı tarafından reddedildi.',
        },
      })
    renderComponent()

    await waitFor(() => expect(screen.getByRole('button', { name: 'Reddet' })).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: 'Reddet' }))
    await userEvent.click(screen.getByRole('button', { name: 'Reddetmeyi Onayla' }))

    await waitFor(() => expect(screen.getByText(/Reddetme tamamlanamadı/)).toBeInTheDocument())
    expect(screen.getAllByText(/trace-red-1/).length).toBeGreaterThan(0)
    expect(screen.getByText('Değerlendirmeyi Reddet')).toBeInTheDocument()
    expect(screen.queryByText('Bu değerlendirme reddedildi')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Reddetmeyi Onayla' }))
    await waitFor(() => expect(reddetMock).toHaveBeenCalledTimes(2))
  })

  it('önceden reddedilmiş tahminde red özetini gösterir ve karar aksiyonlarını gizler', async () => {
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockResolvedValue({
      ...MOCK_DETAIL_FULL,
      red_bilgisi: {
        reddeden: 'operator.1',
        reddetme_zamani: '2026-08-19T12:00:00Z',
        red_nedeni: 'Yanlış alarm.',
      },
    })
    renderComponent()

    await waitFor(() => expect(screen.getByText('Bu değerlendirme reddedildi')).toBeInTheDocument())
    expect(screen.getByText('Reddeden: operator.1')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Onayla' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reddet' })).not.toBeInTheDocument()
  })

  it('önceden onaylanmış tahminde iş emri özetini gösterir ve karar aksiyonlarını gizler', async () => {
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockResolvedValue({
      ...MOCK_DETAIL_FULL,
      is_emri_bilgisi: {
        id: '7f42480e-4dc6-4de5-a5c0-6d1f947cd271',
        is_emri_numarasi: 'WO-2026-7F42480E4DC6',
        durum: 'ACIK',
        olusturan: 'bakim.uzmani',
        olusturulma_zamani: '2026-08-19T12:00:00Z',
      },
    })
    renderComponent()

    await waitFor(() => expect(screen.getByText('Bu bakım kararı onaylandı')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'WO-2026-7F42480E4DC6' })).toBeInTheDocument()
    expect(screen.getByText('Durum: Açık')).toBeInTheDocument()
    expect(screen.getByText('Onaylayan: bakim.uzmani')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Onayla' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reddet' })).not.toBeInTheDocument()
  })

  it('red ve iş emri bilgisi birlikte geldiğinde savunmacı olarak karar aksiyonlarını gizler', async () => {
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockResolvedValue({
      ...MOCK_DETAIL_FULL,
      red_bilgisi: {
        reddeden: 'operator.1',
        reddetme_zamani: '2026-08-19T12:00:00Z',
        red_nedeni: 'Yanlış alarm.',
      },
      is_emri_bilgisi: {
        id: '7f42480e-4dc6-4de5-a5c0-6d1f947cd271',
        is_emri_numarasi: 'WO-2026-7F42480E4DC6',
        durum: 'ACIK',
        olusturan: 'bakim.uzmani',
        olusturulma_zamani: '2026-08-19T12:00:00Z',
      },
    })
    renderComponent()

    await waitFor(() => expect(screen.getByText('Bu değerlendirme reddedildi')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Onayla' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reddet' })).not.toBeInTheDocument()
  })

  it('reddetme isteği sürerken ikinci gönderimi engeller', async () => {
    let resolveRed: (kayit: TahminKaydiDetay) => void = () => {}
    const redPromise = new Promise<TahminKaydiDetay>((resolve) => {
      resolveRed = resolve
    })
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockResolvedValue(MOCK_DETAIL_FULL)
    const reddetMock = vi.spyOn(tahminApi, 'tahminReddet').mockReturnValue(redPromise)
    renderComponent()

    await waitFor(() => expect(screen.getByRole('button', { name: 'Reddet' })).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: 'Reddet' }))
    const submitButton = screen.getByRole('button', { name: 'Reddetmeyi Onayla' })
    await userEvent.click(submitButton)

    expect(screen.getByRole('button', { name: 'Reddediliyor...' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Reddediliyor...' }))
    expect(reddetMock).toHaveBeenCalledTimes(1)

    resolveRed({ ...MOCK_DETAIL_FULL, red_bilgisi: null })
    await waitFor(() => expect(screen.queryByText('Değerlendirmeyi Reddet')).not.toBeInTheDocument())
  })

  it('404 durumunda kullanıcı dostu bulunamadı ekranı sunar', async () => {
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockRejectedValue(
      new ApiHatasi(404, 'KAYIT_BULUNAMADI', 'Bulunamadı.')
    )
    renderComponent('invalid-uuid')

    await waitFor(() => {
      expect(screen.getByText('Değerlendirme Bulunamadı')).toBeInTheDocument()
    })
  })

  it('403 yetki hatasında oturumu kapatmadan yetki yok uyarısı sunar', async () => {
    vi.spyOn(tahminApi, 'tahminKaydiDetayiGetir').mockRejectedValue(
      new ApiHatasi(403, 'YETKISIZ_ERISIM', 'Yetkiniz yok.')
    )
    renderComponent()

    await waitFor(() => {
      expect(screen.getByText('Erişim Yetkisi Yok')).toBeInTheDocument()
    })
  })
})
