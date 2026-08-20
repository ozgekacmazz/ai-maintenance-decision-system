import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TahminLoglari } from './TahminLoglari'
import * as api from '../api/tahminler'
import { ApiHatasi } from '../types/apiHata'

afterEach(() => vi.restoreAllMocks())

const log = {
  id: 'prediction-1', olcum_zamani: '2026-08-19T12:00:00Z',
  makine: { id: 1, kod: 'M-101', ad: 'Pres Motoru' }, kaynak: 'MANUEL' as const,
  risk_orani: 0.82, risk_uyarisi: true, genel_oncelik: 5 as const,
  legacy_oncelik_seviyesi: 'KRITIK' as const, legacy_nihai_oncelik_skoru: 90,
  karar_durumu: 'ONAYLANDI' as const, karar_veren: 'bakim.uzmani',
  karar_zamani: '2026-08-19T12:10:00Z', karar_nedeni: null,
  is_emri_bilgisi: { id: 'wo-1', is_emri_numarasi: 'WO-001', durum: 'ACIK', olusturan: 'bakim.uzmani', olusturulma_zamani: '2026-08-19T12:10:00Z' },
  onay_bilgisi: { id: 'wo-1', is_emri_numarasi: 'WO-001', durum: 'ACIK', olusturan: 'bakim.uzmani', olusturulma_zamani: '2026-08-19T12:10:00Z' }, red_bilgisi: null,
}

describe('TahminLoglari', () => {
  it('canonical karar, öncelik, kullanıcı ve bağlantıları gösterir', async () => {
    vi.spyOn(api, 'tahminLoglariniGetir').mockResolvedValue({ count: 1, next: null, previous: null, results: [log] })
    render(<MemoryRouter><TahminLoglari /></MemoryRouter>)
    expect(await screen.findByText('Pres Motoru')).toBeInTheDocument()
    expect(screen.getAllByText('Onaylandı').length).toBeGreaterThan(0)
    expect(screen.getByText('bakim.uzmani')).toBeInTheDocument()
    expect(screen.getAllByText('Öncelik 5/5').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'WO-001' })).toHaveAttribute('href', '/app/is-emirleri/wo-1')
    expect(screen.getByRole('link', { name: 'Detay' })).toHaveAttribute('href', '/app/tahminler/prediction-1')
  })

  it('filtre değişikliğini API parametresine taşır ve temizler', async () => {
    const request = vi.spyOn(api, 'tahminLoglariniGetir').mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
    render(<MemoryRouter><TahminLoglari /></MemoryRouter>)
    fireEvent.change(screen.getByLabelText('Karar durumu'), { target: { value: 'REDDEDILDI' } })
    await waitFor(() => expect(request).toHaveBeenLastCalledWith(expect.objectContaining({ karar_durumu: 'REDDEDILDI', sayfa: 1 })))
    fireEvent.click(screen.getByRole('button', { name: 'Filtreleri temizle' }))
    await waitFor(() => expect(request).toHaveBeenLastCalledWith(expect.objectContaining({ karar_durumu: undefined, sayfa: 1 })))
  })

  it('403 yanıtını güvenli yetki mesajıyla gösterir', async () => {
    vi.spyOn(api, 'tahminLoglariniGetir').mockRejectedValue(new ApiHatasi(403, 'YETKI_YOK', 'Reddedildi', {}, 'trace-403'))
    render(<MemoryRouter><TahminLoglari /></MemoryRouter>)
    expect(await screen.findByText('Bu bölüme erişim yetkiniz yok.')).toBeInTheDocument()
    expect(screen.getByText('Takip kodu: trace-403')).toBeInTheDocument()
  })
})
