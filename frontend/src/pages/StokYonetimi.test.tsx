import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { StokYonetimi } from './StokYonetimi'
import * as yonetimApi from '../api/yonetim'
import * as authContext from '../app/AuthContext'

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_STOCK_LIST = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      parca: { id: 10, parca_kodu: 'PRC-001', ad: 'Güç Rölesi', aktif: true, olusturulma_zamani: '', guncellenme_zamani: '' },
      toplam_stok: 0,
      minimum_stok: 2,
      tedarik_gun: 3,
      kullanilabilir_stok: 0,
      stok_durumu: 'MEVCUT' as const,
      stok_yeterli: false,
      guncellenme_zamani: '2026-08-19T10:00:00Z',
    },
  ],
}

describe('StokYonetimi', () => {
  it('ADMIN rolünde stok listesini ve 0 stok uyarısını sunar', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 1, username: 'admin', rol: 'ADMIN' },
      yukleniyor: false,
      giris: vi.fn(),
      cikis: vi.fn(),
    })
    vi.spyOn(yonetimApi, 'stoklariGetir').mockResolvedValue(MOCK_STOCK_LIST)

    render(
      <MemoryRouter>
        <StokYonetimi />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Güç Rölesi')).toBeInTheDocument()
      expect(screen.getByText('PRC-001')).toBeInTheDocument()
      expect(screen.getByText('Stok: 0 adet (Tükendi)')).toBeInTheDocument()
    })
  })
})
