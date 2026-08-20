import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TahminGecmisi } from './TahminGecmisi'
import * as tahminApi from '../api/tahminler'
import type { SayfalanmisYanit, TahminKaydiOzet } from '../types/tahminler'
import { ApiHatasi } from '../types/apiHata'

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_LIST_RESPONSE: SayfalanmisYanit<TahminKaydiOzet> = {
  count: 25,
  next: 'http://localhost:8000/api/tahminler/kayitlar/?sayfa=2',
  previous: null,
  results: [
    {
      id: 'd9b3a1e2-4f5c-6b7a-8d9e-0f1a2b3c4d5e',
      makine: { id: 1, kod: 'M-101', ad: 'Pres Motoru 1' },
      olcum_zamani: '2026-08-19T10:30:00Z',
      risk_orani: 0.85,
      risk_uyarisi: true,
      en_yuksek_guvenilir_ariza_tipi: 'PWF',
      belirsiz_fiziksel_tip: false,
      kaynak: 'MANUEL',
      olusturan: { id: 2, kullanici_adi: 'ozge.06' },
      trace_id: 'tr-12345',
      erp_snapshot_var: true,
      nihai_oncelik_skoru: 88,
      oncelik_seviyesi: 'KRITIK',
      genel_oncelik: null,
      genel_oncelik_formul_surumu: null,
      ana_aksiyon: 'ACIL_TEKNIK_DEGERLENDIRME',
      karar_guveni: 'YUKSEK',
    },
  ],
}

function renderComponent() {
  return render(
    <MemoryRouter initialEntries={['/app/tahminler']}>
      <Routes>
        <Route path="/app/tahminler" element={<TahminGecmisi />} />
        <Route path="/app/tahminler/:id" element={<div>Detay Sayfasi</div>} />
        <Route path="/app/tahminler/yeni" element={<div>Yeni Kayit Sayfasi</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('TahminGecmisi', () => {
  it('tahmin geçmişi listesini ve filtrelerini doğru görüntüler', async () => {
    vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockResolvedValue(MOCK_LIST_RESPONSE)
    renderComponent()

    expect(screen.getByText('Tahmin Geçmişi')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Yeni Kalıcı Değerlendirme' })).toBeInTheDocument()

    expect(await screen.findByText('Pres Motoru 1')).toBeInTheDocument()
    expect(screen.getByText('M-101')).toBeInTheDocument()
    expect(screen.getByText(/85/)).toBeInTheDocument()
    expect(screen.getByText('Güç kaynaklı sorun')).toBeInTheDocument()
    expect(screen.getAllByText('Kritik').length).toBeGreaterThan(0)
    expect(screen.getByText('Acil teknik değerlendirme')).toBeInTheDocument()
    expect(screen.getAllByText('Manuel değerlendirme').length).toBeGreaterThan(0)
  })

  it('boş veri geldiğinde premium empty state sunar', async () => {
    vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    })
    renderComponent()

    expect(await screen.findByText('Kayıtlı Değerlendirme Bulunamadı')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Yeni Kalıcı Değerlendirme Başlat' })).toBeInTheDocument()
  })

  it('filtrelere tıklandığında API isteğine doğru parametreleri gönderir', async () => {
    const spy = vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockResolvedValue(MOCK_LIST_RESPONSE)
    renderComponent()

    expect(await screen.findByText('Pres Motoru 1')).toBeInTheDocument()

    const riskSelect = screen.getByLabelText('Risk Durumu')
    await userEvent.selectOptions(riskSelect, 'true')

    await waitFor(() => {
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          risk_uyarisi: true,
          sayfa: 1,
        })
      )
    })
  })

  it('satıra tıklandığında detay sayfasına yönlendirir', async () => {
    vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockResolvedValue(MOCK_LIST_RESPONSE)
    renderComponent()

    expect(await screen.findByText('Pres Motoru 1')).toBeInTheDocument()

    await userEvent.click(screen.getByText('Pres Motoru 1'))
    expect(await screen.findByText('Detay Sayfasi')).toBeInTheDocument()
  })

  it('API hatası durumunda ErrorState sunar ve tekrar deneme olanağı verir', async () => {
    let attempt = 0
    const spy = vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockImplementation(() => {
      attempt++
      if (attempt === 1) {
        return Promise.reject(new ApiHatasi(503, 'SERVIS_DISI', 'Servise ulaşılamıyor.'))
      }
      return Promise.resolve(MOCK_LIST_RESPONSE)
    })

    renderComponent()

    expect(await screen.findByText('Servise ulaşılamıyor.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Tekrar dene/i }))

    expect(await screen.findByText('Pres Motoru 1')).toBeInTheDocument()
    expect(spy).toHaveBeenCalledTimes(2)
  })
})
