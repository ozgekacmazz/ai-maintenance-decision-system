import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ReplayListesi } from './ReplayListesi'
import * as replayApi from '../api/replay'
import * as bakimApi from '../api/bakim'
import * as authContext from '../app/AuthContext'

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_REPLAY_LIST = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 'rep-101',
      makine: { id: 1, kod: 'M-101', ad: 'Pres Motoru 1' },
      split: 'test' as const,
      durum: 'HAZIR' as const,
      baslangic_ofseti: 0,
      toplam_oge: 250,
      varsayilan_batch_boyutu: 5,
      sanal_aralik_saniye: 60,
      baslatilma_zamani: null,
      tamamlanma_zamani: null,
      iptal_zamani: null,
      hata_mesaji: null,
      ilerleme: {
        bekleyen: 250,
        isleniyor: 0,
        basarili: 0,
        basarisiz: 0,
        atlandi: 0,
        tamamlanma_yuzdesi: 0,
      },
      olusturulma_zamani: '2026-08-19T10:00:00Z',
      version: 1,
    },
  ],
}

describe('ReplayListesi', () => {
  it('replay oturumlarını ve durum bilgilerini doğru sunar', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 1, username: 'admin', rol: 'ADMIN' },
      yukleniyor: false,
      giris: vi.fn(),
      cikis: vi.fn(),
    })
    vi.spyOn(bakimApi, 'makineleriGetir').mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
    vi.spyOn(replayApi, 'replayOturumlariniGetir').mockResolvedValue(MOCK_REPLAY_LIST)

    render(
      <MemoryRouter>
        <ReplayListesi />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Pres Motoru 1')).toBeInTheDocument()
    })
    expect(screen.getByText('Hazır')).toBeInTheDocument()
  })
})
