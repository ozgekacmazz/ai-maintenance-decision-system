import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Login } from './Login'

const giris = vi.fn()
vi.mock('../app/AuthContext', () => ({ useAuth: () => ({ giris }) }))

describe('Login', () => {
  it('form alanlarını ve erişilebilir parola görünürlüğünü sunar', async () => {
    render(<Login />)
    expect(screen.getByLabelText('Kullanıcı adı')).toBeInTheDocument()
    const parola = screen.getByLabelText('Parola')
    expect(parola).toHaveAttribute('type', 'password')
    await userEvent.click(screen.getByRole('button', { name: 'Parolayı göster' }))
    expect(parola).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: 'Parolayı gizle' })).toBeInTheDocument()
  })

  it('eksik alanlarda doğrulama mesajı gösterir', async () => {
    render(<Login />)
    await userEvent.click(screen.getByRole('button', { name: 'Giriş yap' }))
    expect(screen.getByRole('alert')).toHaveTextContent('zorunludur')
  })

  it('başarılı submit için giris fonksiyonunu çağırır', async () => {
    giris.mockResolvedValue(undefined)
    render(<Login />)
    await userEvent.type(screen.getByLabelText('Kullanıcı adı'), 'user')
    await userEvent.type(screen.getByLabelText('Parola'), 'gizli-deger')
    await userEvent.click(screen.getByRole('button', { name: 'Giriş yap' }))
    expect(giris).toHaveBeenCalledWith('user', 'gizli-deger')
  })
})
