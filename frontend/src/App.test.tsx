import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { authBellekDurumunuSifirla } from './api/auth'

afterEach(() => {
  authBellekDurumunuSifirla()
  vi.restoreAllMocks()
})

describe('App auth başlangıcı ve yönlendirmeleri', () => {
  it('ilk açılışta yükleniyor durumunu gösterir', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}))
    render(<App />)
    expect(screen.getByRole('status')).toHaveTextContent('Oturum yükleniyor')
  })

  it('refresh başarısızsa login ekranını gösterir', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'csrf' }), { status: 200 }))
      .mockResolvedValueOnce(new Response('{}', { status: 401 }))
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Hesabınıza giriş yapın' })).toBeInTheDocument()
  })

  it('refresh ve me başarılıysa korumalı ürün dashboard ekranını gösterir', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'csrf' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access: 'access-memory' }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 1, username: 'user', rol: 'USER' }), { status: 200 }))
      .mockImplementation((url) => {
        if (typeof url === 'string' && url.includes('/api/tahminler/kayitlar/')) {
          return Promise.resolve(new Response(JSON.stringify({ count: 0, next: null, previous: null, results: [] }), { status: 200 }))
        }
        return new Promise(() => {})
      })

    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Genel Bakış' })).toBeInTheDocument()
    expect(screen.getAllByText('Kullanıcı').length).toBeGreaterThan(0)
  })
})
