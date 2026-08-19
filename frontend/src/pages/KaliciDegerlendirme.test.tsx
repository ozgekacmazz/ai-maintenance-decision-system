import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { KaliciDegerlendirme } from './KaliciDegerlendirme'
import * as bakimApi from '../api/bakim'
import * as tahminApi from '../api/tahminler'
import type { MakineOzet, SayfalanmisYanit, TahminKaydiDetay } from '../types/tahminler'
import { ApiHatasi } from '../types/apiHata'

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_MAKINELER: SayfalanmisYanit<MakineOzet> = {
  count: 2,
  next: null,
  previous: null,
  results: [
    { id: 101, kod: 'M-101', ad: 'Pres Motoru 1', tip: 'Pres', kritiklik: 5, aktif: true },
    { id: 102, kod: 'M-102', ad: 'CNC Torna 2', tip: 'Torna', kritiklik: 3, aktif: true },
  ],
}

const MOCK_CREATE_RESPONSE: TahminKaydiDetay = {
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
  ariza_tipleri: [],
  shap_etkileri: [],
  erp_snapshotlari: [],
  olusturan: { id: 2, kullanici_adi: 'ozge.06' },
  trace_id: 'tr-998877',
  bakim_karari: null,
}

function renderComponent() {
  return render(
    <MemoryRouter initialEntries={['/app/tahminler/yeni']}>
      <Routes>
        <Route path="/app/tahminler/yeni" element={<KaliciDegerlendirme />} />
        <Route path="/app/tahminler/:id" element={<div>Kayit Detay Sayfasi</div>} />
        <Route path="/app/tahminler" element={<div>Tahmin Gecmisi Sayfasi</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('KaliciDegerlendirme', () => {
  it('makine listesini yükler ve form alanlarını sunar', async () => {
    vi.spyOn(bakimApi, 'makineleriGetir').mockResolvedValue(MOCK_MAKINELER)
    renderComponent()

    await waitFor(() => {
      expect(screen.getByLabelText('Makine Seçimi')).toBeInTheDocument()
      expect(screen.getByText('M-101 — Pres Motoru 1')).toBeInTheDocument()
    })

    expect(screen.getByLabelText(/Ürün Tipi/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Hava Sıcaklığı/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Değerlendirmeyi Kaydet' })).toBeInTheDocument()
  })

  it('başarılı kayıtta POST /api/tahminler/kayitlar/ çağırır ve detaya yönlendirir', async () => {
    vi.spyOn(bakimApi, 'makineleriGetir').mockResolvedValue(MOCK_MAKINELER)
    const createSpy = vi
      .spyOn(tahminApi, 'kaliciTahminKaydiOlustur')
      .mockResolvedValue(MOCK_CREATE_RESPONSE)

    renderComponent()
    await waitFor(() => expect(screen.getByText('M-101 — Pres Motoru 1')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: 'Değerlendirmeyi Kaydet' }))

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          makine_id: 101,
          kaynak: 'MANUEL',
          idempotency_key: expect.any(String),
          sensor_verisi: expect.objectContaining({
            urun_tipi: 'M',
            hava_sicakligi_k: 300,
          }),
        })
      )
    })

    await waitFor(() => {
      expect(screen.getByText('Kayit Detay Sayfasi')).toBeInTheDocument()
    })
  })

  it('submit sırasında tekrar tıklamayı ve duplicate submit yapmayı engeller', async () => {
    vi.spyOn(bakimApi, 'makineleriGetir').mockResolvedValue(MOCK_MAKINELER)

    let resolveCreate: (val: TahminKaydiDetay) => void = () => {}
    const createPromise = new Promise<TahminKaydiDetay>((res) => {
      resolveCreate = res
    })
    vi.spyOn(tahminApi, 'kaliciTahminKaydiOlustur').mockReturnValue(createPromise)

    renderComponent()
    await waitFor(() => expect(screen.getByText('M-101 — Pres Motoru 1')).toBeInTheDocument())

    const btn = screen.getByRole('button', { name: 'Değerlendirmeyi Kaydet' })
    await userEvent.click(btn)

    expect(btn).toBeDisabled()
    expect(screen.getByText('Kaydediliyor…')).toBeInTheDocument()

    resolveCreate(MOCK_CREATE_RESPONSE)
    await waitFor(() => expect(screen.getByText('Kayit Detay Sayfasi')).toBeInTheDocument())
  })

  it('409 çakışma hatasında kullanıcı dostu mesaj gösterir', async () => {
    vi.spyOn(bakimApi, 'makineleriGetir').mockResolvedValue(MOCK_MAKINELER)
    vi.spyOn(tahminApi, 'kaliciTahminKaydiOlustur').mockRejectedValue(
      new ApiHatasi(409, 'IDEMPOTENCY_CAKISMASI', 'Çakışma var.')
    )

    renderComponent()
    await waitFor(() => expect(screen.getByText('M-101 — Pres Motoru 1')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: 'Değerlendirmeyi Kaydet' }))

    await waitFor(() => {
      expect(
        screen.getByText('Bu kayıt isteği önceki bir işlemle çakıştı. Bilgileri kontrol edip yeni bir değerlendirme başlatın.')
      ).toBeInTheDocument()
    })
  })
})
