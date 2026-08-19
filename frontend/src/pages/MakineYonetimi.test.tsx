import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MakineYonetimi } from './MakineYonetimi'
import * as yonetimApi from '../api/yonetim'
import * as authContext from '../app/AuthContext'

afterEach(() => {
  vi.restoreAllMocks()
})

const MOCK_MACHINE_LIST = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      makine_kodu: 'M-101',
      ad: 'Pres Motoru 1',
      kritiklik_seviyesi: 5,
      aktif: true,
      olusturulma_zamani: '2026-08-19T10:00:00Z',
      guncellenme_zamani: '2026-08-19T10:00:00Z',
    },
  ],
}

describe('MakineYonetimi', () => {
  it('ADMIN rolünde makine listesini sunar', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 1, username: 'admin', rol: 'ADMIN' },
      yukleniyor: false,
      giris: vi.fn(),
      cikis: vi.fn(),
    })
    vi.spyOn(yonetimApi, 'makineleriGetirFull').mockResolvedValue(MOCK_MACHINE_LIST)

    render(
      <MemoryRouter>
        <MakineYonetimi />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Pres Motoru 1')).toBeInTheDocument()
      expect(screen.getByText('M-101')).toBeInTheDocument()
    })
  })
})
