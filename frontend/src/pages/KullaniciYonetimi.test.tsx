import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { KullaniciYonetimi } from './KullaniciYonetimi'
import * as yonetimApi from '../api/yonetim'
import * as authContext from '../app/AuthContext'
import { ApiHatasi } from '../types/apiHata'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('KullaniciYonetimi', () => {
  it('ADMIN rolünde kullanıcı listesini, yeni kullanıcı CTA butonunu ve aksiyonları sunar', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 1, username: 'demo_admin', rol: 'ADMIN' },
      yukleniyor: false,
      giris: vi.fn(),
      cikis: vi.fn(),
    })
    vi.spyOn(yonetimApi, 'kullanicilariGetir').mockResolvedValue([
      { id: 1, username: 'demo_admin', email: 'admin@demo.com', rol: 'ADMIN', is_active: true, date_joined: '2026-01-01T00:00:00Z' },
      { id: 2, username: 'demo_operator', email: 'operator@demo.com', rol: 'USER', is_active: true, date_joined: '2026-01-01T00:00:00Z' },
      { id: 3, username: 'demo_pasif', email: 'pasif@demo.com', rol: 'USER', is_active: false, date_joined: '2026-01-01T00:00:00Z' },
    ])

    render(
      <MemoryRouter>
        <KullaniciYonetimi />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Kullanıcı Yönetimi' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Yeni Kullanıcı/i })).toBeInTheDocument()
      expect(screen.getByText('demo_admin')).toBeInTheDocument()
      expect(screen.getByText('demo_operator')).toBeInTheDocument()
      expect(screen.getByText('demo_pasif')).toBeInTheDocument()
      expect(screen.getAllByRole('button', { name: /Şifre Güncelle/i })).toHaveLength(3)
    })
  })

  it('parola yardımını ve create alan hatalarının tamamını gösterir', async () => {
    const user = userEvent.setup()
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 1, username: 'demo_admin', rol: 'ADMIN' },
      yukleniyor: false, giris: vi.fn(), cikis: vi.fn(),
    })
    vi.spyOn(yonetimApi, 'kullanicilariGetir').mockResolvedValue([])
    vi.spyOn(yonetimApi, 'kullaniciOlustur').mockRejectedValue(
      new ApiHatasi(400, 'DOGRULAMA_HATASI', 'Doğrulama hatası', {
        password: ['Bu parola çok kısa.', 'Bu parola çok yaygın.'],
      }),
    )
    render(<MemoryRouter><KullaniciYonetimi /></MemoryRouter>)
    await user.click(await screen.findByRole('button', { name: /Yeni Kullanıcı/i }))
    await user.type(screen.getByLabelText('Kullanıcı Adı *'), 'yeni-user')
    await user.type(screen.getByLabelText('İlk Parola *'), 'Password123!')
    await user.click(screen.getByRole('button', { name: 'Oluştur' }))
    expect(await screen.findByText(/Bu parola çok kısa.*Bu parola çok yaygın/)).toBeInTheDocument()
    expect(screen.getByText(/En az 8 karakter; yaygın/)).toBeInTheDocument()
  })

  it('reset parola alan hatasını gösterir ve raw parolayı yansıtmaz', async () => {
    const user = userEvent.setup()
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 1, username: 'demo_admin', rol: 'ADMIN' },
      yukleniyor: false, giris: vi.fn(), cikis: vi.fn(),
    })
    vi.spyOn(yonetimApi, 'kullanicilariGetir').mockResolvedValue([
      { id: 2, username: 'hedef', email: '', rol: 'USER', is_active: true, date_joined: '2026-01-01T00:00:00Z' },
    ])
    vi.spyOn(yonetimApi, 'kullaniciSifreSifirla').mockRejectedValue(
      new ApiHatasi(400, 'DOGRULAMA_HATASI', 'Doğrulama hatası', {
        yeni_sifre: ['Bu parola tamamen sayısal olamaz.'],
      }),
    )
    render(<MemoryRouter><KullaniciYonetimi /></MemoryRouter>)
    await user.click((await screen.findAllByRole('button', { name: /Şifre Güncelle/i }))[0])
    const raw = '123456789'
    await user.type(screen.getByLabelText('Yeni Parola *'), raw)
    await user.click(screen.getByRole('button', { name: 'Parolayı Güncelle' }))
    expect(await screen.findByText('Bu parola tamamen sayısal olamaz.')).toBeInTheDocument()
    expect(screen.queryByText(raw)).not.toBeInTheDocument()
  })

  it('USER rolünde 403 erişim engeli mesajı sunar ve oturumu kapatmaz', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      kullanici: { id: 2, username: 'demo_operator', rol: 'USER' },
      yukleniyor: false,
      giris: vi.fn(),
      cikis: vi.fn(),
    })

    render(
      <MemoryRouter>
        <KullaniciYonetimi />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Bu alanı görüntülemek için YÖNETİCİ (ADMIN) yetkisi gereklidir.')).toBeInTheDocument()
    })
  })
})
