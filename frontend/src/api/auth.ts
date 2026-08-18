import type { GirisYaniti, KullaniciOzeti } from '../types/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
let accessToken: string | null = null
let csrfToken: string | null = null
let refreshPromise: Promise<string> | null = null

export function accessTokeniAyarla(token: string | null) {
  accessToken = token
}

export function accessTokeniniGetir() {
  return accessToken
}

export function authBellekDurumunuSifirla() {
  accessToken = null
  csrfToken = null
  refreshPromise = null
}

async function csrfTokeniGetir(): Promise<string> {
  if (csrfToken) return csrfToken
  const response = await fetch(`${API_BASE_URL}/api/auth/csrf/`, { credentials: 'include' })
  if (!response.ok) throw new Error('CSRF başlangıç isteği başarısız oldu.')
  const data = await response.json() as { csrf_token: string }
  csrfToken = data.csrf_token
  return csrfToken
}

async function authPost(path: string, body?: unknown): Promise<Response> {
  const csrf = await csrfTokeniGetir()
  return fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export async function girisYap(username: string, password: string): Promise<GirisYaniti> {
  const response = await authPost('/api/auth/login/', { username, password })
  if (response.status === 401) throw new Error('Kullanıcı adı veya parola hatalı.')
  if (!response.ok) throw new Error('Giriş işlemi tamamlanamadı.')
  const data = await response.json() as GirisYaniti
  accessTokeniAyarla(data.access)
  return data
}

export async function accessTokeniYenile(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = authPost('/api/auth/refresh/')
      .then(async (response) => {
        if (!response.ok) throw new Error('Oturum yenilenemedi.')
        const data = await response.json() as { access: string }
        accessTokeniAyarla(data.access)
        return data.access
      })
      .catch((error) => {
        accessTokeniAyarla(null)
        throw error
      })
      .finally(() => { refreshPromise = null })
  }
  return refreshPromise
}

export async function kimlikliIstek(path: string, init: RequestInit = {}, tekrar = true): Promise<Response> {
  const headers = new Headers(init.headers)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: 'include' })
  if (response.status === 401 && tekrar) {
    await accessTokeniYenile()
    return kimlikliIstek(path, init, false)
  }
  return response
}

export async function kullaniciyiGetir(): Promise<KullaniciOzeti> {
  const response = await kimlikliIstek('/api/auth/me/')
  if (!response.ok) throw new Error('Kullanıcı bilgisi alınamadı.')
  return response.json() as Promise<KullaniciOzeti>
}

export async function cikisYap(): Promise<void> {
  try {
    await authPost('/api/auth/logout/')
  } finally {
    accessTokeniAyarla(null)
  }
}

export async function adminKontrolu(): Promise<'izinli' | 'yasak'> {
  const response = await kimlikliIstek('/api/auth/admin-kontrol/')
  if (response.status === 403) return 'yasak'
  if (!response.ok) throw new Error('Admin kontrolü tamamlanamadı.')
  return 'izinli'
}
