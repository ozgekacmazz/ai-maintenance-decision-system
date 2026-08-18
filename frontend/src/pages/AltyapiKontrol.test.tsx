import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AltyapiKontrol } from './AltyapiKontrol'

vi.mock('../app/AuthContext', () => ({
  useAuth: () => ({ kullanici: { username: 'test', rol: 'USER' }, cikis: vi.fn() }),
}))

afterEach(() => vi.restoreAllMocks())

describe('AltyapiKontrol', () => {
  it('yükleniyor durumunu gösterir', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}))
    render(<AltyapiKontrol />)
    expect(screen.getByRole('status')).toHaveTextContent('kontrol ediliyor')
  })

  it('başarılı cevapta backend ve PostgreSQL durumunu gösterir', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ durum: 'hazir', servis: 'backend', veritabani: 'bagli' }), { status: 200 }))
    render(<AltyapiKontrol />)
    await waitFor(() => expect(screen.getAllByText('bağlı')).toHaveLength(2))
  })

  it('API hatasını anlaşılır biçimde gösterir', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network'))
    render(<AltyapiKontrol />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend bağlantısı kurulamadı')
  })

  it('tekrar denendiğinde yeni istek başlatır', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network'))
    render(<AltyapiKontrol />)
    await screen.findByRole('alert')
    await userEvent.click(screen.getByRole('button', { name: 'Tekrar dene' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })
})
