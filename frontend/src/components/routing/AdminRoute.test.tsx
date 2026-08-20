import { StrictMode, useEffect } from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminRoute } from './AdminRoute'
import * as auth from '../../app/AuthContext'
import type { KullaniciOzeti } from '../../types/auth'

afterEach(() => vi.restoreAllMocks())

const admin = { id: 1, username: 'admin', rol: 'ADMIN' as const }
const user = { id: 2, username: 'operator', rol: 'USER' as const }

function AdminChild({ api }: { api: () => void }) {
  useEffect(api, [api])
  return <h1>Admin içeriği</h1>
}

function routeRender(path: string, api = vi.fn()) {
  return {
    api,
    ...render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/app" element={<h1>Genel Bakış</h1>} />
          <Route path="/app/yonetim" element={<AdminRoute />}>
            <Route path="kullanicilar" element={<AdminChild api={api} />} />
            <Route path="stok" element={<AdminChild api={api} />} />
            <Route path="makineler" element={<AdminChild api={api} />} />
            <Route path="tahmin-loglari" element={<AdminChild api={api} />} />
          </Route>
        </Routes>
      </MemoryRouter>
    ),
  }
}

describe('AdminRoute', () => {
  it.each([
    '/app/yonetim/kullanicilar',
    '/app/yonetim/stok',
    '/app/yonetim/makineler',
    '/app/yonetim/tahmin-loglari',
  ])('ADMIN için %s child routeunu açar', (path) => {
    vi.spyOn(auth, 'useAuth').mockReturnValue({ kullanici: admin, yukleniyor: false, giris: vi.fn(), cikis: vi.fn() })
    const { api } = routeRender(path)
    expect(screen.getByRole('heading', { name: 'Admin içeriği' })).toBeInTheDocument()
    expect(api).toHaveBeenCalledTimes(1)
  })

  it.each([
    '/app/yonetim/kullanicilar',
    '/app/yonetim/stok',
    '/app/yonetim/makineler',
    '/app/yonetim/tahmin-loglari',
  ])('USER doğrudan %s açtığında childı mount etmez ve API çağırmaz', (path) => {
    vi.spyOn(auth, 'useAuth').mockReturnValue({ kullanici: user, yukleniyor: false, giris: vi.fn(), cikis: vi.fn() })
    const { api } = routeRender(path)
    expect(screen.getByRole('heading', { name: 'Bu bölüme erişim yetkiniz yok' })).toBeInTheDocument()
    expect(screen.queryByText('Admin içeriği')).not.toBeInTheDocument()
    expect(api).not.toHaveBeenCalled()
    expect(screen.getByRole('link', { name: 'Ana sayfaya dön' })).toHaveAttribute('href', '/app')
  })

  it('auth yüklenirken childı mount etmez ve erken yetkisiz ekran göstermez', () => {
    vi.spyOn(auth, 'useAuth').mockReturnValue({ kullanici: null, yukleniyor: true, giris: vi.fn(), cikis: vi.fn() })
    const { api } = routeRender('/app/yonetim/stok')
    expect(screen.getByRole('status')).toHaveTextContent('Oturum yükleniyor')
    expect(screen.queryByText('Bu bölüme erişim yetkiniz yok')).not.toBeInTheDocument()
    expect(api).not.toHaveBeenCalled()
  })

  it('eksik rolü güvenli biçimde yetkisiz kabul eder', () => {
    const missingRole = { id: 3, username: 'eksik' } as unknown as KullaniciOzeti
    vi.spyOn(auth, 'useAuth').mockReturnValue({ kullanici: missingRole, yukleniyor: false, giris: vi.fn(), cikis: vi.fn() })
    const { api } = routeRender('/app/yonetim/makineler')
    expect(screen.getByText('Bu bölüme erişim yetkiniz yok')).toBeInTheDocument()
    expect(api).not.toHaveBeenCalled()
  })

  it('StrictMode altında yetkisiz childı mount etmez', () => {
    vi.spyOn(auth, 'useAuth').mockReturnValue({ kullanici: user, yukleniyor: false, giris: vi.fn(), cikis: vi.fn() })
    const api = vi.fn()
    render(<StrictMode><MemoryRouter initialEntries={['/app/yonetim/kullanicilar']}><Routes><Route path="/app/yonetim" element={<AdminRoute />}><Route path="kullanicilar" element={<AdminChild api={api} />} /></Route></Routes></MemoryRouter></StrictMode>)
    expect(screen.getByText('Bu bölüme erişim yetkiniz yok')).toBeInTheDocument()
    expect(api).not.toHaveBeenCalled()
  })
})
