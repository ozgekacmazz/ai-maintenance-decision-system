import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Dashboard } from './Dashboard'
import * as tahminApi from '../api/tahminler'
import type { TahminKaydiOzet } from '../types/tahminler'

vi.mock('../app/AuthContext', () => ({
  useAuth: () => ({ kullanici: { username: 'testuser', rol: 'USER' }, cikis: vi.fn() }),
}))

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_KAYIT: TahminKaydiOzet = {
  id: 'b6c81e3d-88b7-4a30-8000-000000000001',
  makine: { id: 10, kod: 'M101', ad: 'CNC Torna 1' },
  olcum_zamani: '2026-08-19T10:00:00Z',
  risk_orani: 0.7842,
  risk_uyarisi: true,
  en_yuksek_guvenilir_ariza_tipi: 'PWF',
  belirsiz_fiziksel_tip: false,
  kaynak: 'SISTEM',
  olusturan: { id: 1, kullanici_adi: 'admin' },
  trace_id: 'tr-12345',
  erp_snapshot_var: false,
  nihai_oncelik_skoru: 85.0,
  oncelik_seviyesi: 'YUKSEK',
  ana_aksiyon: 'ONCELIKLI_BAKIM_PLANLA',
  karar_guveni: 'YUKSEK',
}

describe('Dashboard', () => {
  it('yüklenme sırasında skeleton gösterir', () => {
    vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockImplementation(() => new Promise(() => {}))
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    )
    expect(screen.getByRole('status', { name: 'Veriler yükleniyor' })).toBeInTheDocument()
  })

  it('veri olmadığında empty state gösterir', async () => {
    vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    })

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Henüz değerlendirilmiş bir kayıt yok')).toBeInTheDocument()
    })
    expect(screen.getAllByText('0')).toHaveLength(3)
  })

  it('başarılı kayıtlarda gerçek count ve kart verilerini gösterir', async () => {
    vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockImplementation(async (params) => {
      if (params?.risk_uyarisi && params?.sirala === '-nihai_oncelik') {
        return { count: 5, next: null, previous: null, results: [MOCK_KAYIT] }
      }
      if (params?.risk_uyarisi) {
        return { count: 5, next: null, previous: null, results: [] }
      }
      if (params?.oncelik_seviyesi === 'KRITIK') {
        return { count: 2, next: null, previous: null, results: [] }
      }
      return { count: 12, next: null, previous: null, results: [] }
    })

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('12')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    expect(screen.getByText('CNC Torna 1')).toBeInTheDocument()
    expect(screen.getByText('KOD: M101')).toBeInTheDocument()
    expect(screen.getByText('%78')).toBeInTheDocument()
    expect(screen.getByText('Yüksek')).toBeInTheDocument()
    expect(screen.getByText('Güç kaynaklı sorun')).toBeInTheDocument()
    expect(screen.getByText('Öncelikli bakım planla')).toBeInTheDocument()
  })

  it('Öncelikli Riskler listesi çekilirken risk_uyarisi=true parametresini gönderir', async () => {
    const apiMock = vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    })

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(apiMock).toHaveBeenCalledWith({
        risk_uyarisi: true,
        sirala: '-nihai_oncelik',
        sayfa_boyutu: 10,
      })
    })
  })

  it('backend hatası durumunda hata mesajı ve tekrar dene butonu sunar', async () => {
    vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockRejectedValue({
      mesaj: 'Sunucu hatası oluştu',
      trace_id: 'tr-err-999',
    })

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Sunucu hatası oluştu')
      expect(screen.getByText('Takip kodu: tr-err-999')).toBeInTheDocument()
    })

    const retryMock = vi.spyOn(tahminApi, 'tahminKayitlariniGetir').mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    })

    await userEvent.click(screen.getByRole('button', { name: 'Tekrar dene' }))
    await waitFor(() => expect(retryMock).toHaveBeenCalled())
  })
})
