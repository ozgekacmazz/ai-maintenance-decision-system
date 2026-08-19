import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Sidebar } from './Sidebar'
import * as auth from '../../app/AuthContext'

afterEach(() => vi.restoreAllMocks())

describe('Sidebar tahmin bağlantıları', () => {
  it('normal geçmişi korur ve admin loglarını gerçek routea bağlar', () => {
    vi.spyOn(auth, 'useAuth').mockReturnValue({
      kullanici: { id: 1, username: 'admin', rol: 'ADMIN' },
      yukleniyor: false, giris: vi.fn(), cikis: vi.fn(),
    })
    render(<MemoryRouter><Sidebar acik onKapat={vi.fn()} /></MemoryRouter>)
    expect(screen.getByRole('link', { name: /Tahmin Geçmişi/ })).toHaveAttribute('href', '/app/tahminler')
    expect(screen.getByRole('link', { name: /Tahmin Logları/ })).toHaveAttribute('href', '/app/yonetim/tahmin-loglari')
  })

  it('USER için yönetim bağlantılarını gizler', () => {
    vi.spyOn(auth, 'useAuth').mockReturnValue({
      kullanici: { id: 2, username: 'operator', rol: 'USER' },
      yukleniyor: false, giris: vi.fn(), cikis: vi.fn(),
    })
    render(<MemoryRouter><Sidebar acik onKapat={vi.fn()} /></MemoryRouter>)
    expect(screen.getByRole('link', { name: /Tahmin Geçmişi/ })).toHaveAttribute('href', '/app/tahminler')
    expect(screen.queryByRole('link', { name: /Tahmin Logları/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Kullanıcı Yönetimi/ })).not.toBeInTheDocument()
  })
})
