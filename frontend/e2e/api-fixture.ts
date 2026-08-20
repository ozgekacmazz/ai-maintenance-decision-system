import type { Page, Route } from '@playwright/test'

type Role = 'ADMIN' | 'USER'

const emptyPage = { count: 0, next: null, previous: null, results: [] }

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

export async function mockSession(page: Page, role: Role) {
  let authenticated = false
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path === '/api/auth/csrf/') return json(route, { csrf_token: 'e2e-csrf' })
    if (path === '/api/auth/refresh/') {
      return authenticated
        ? json(route, { access: 'e2e-access' })
        : json(route, { hata: { kod: 'KIMLIK_GEREKLI', mesaj: 'Oturum yok.', alanlar: {}, trace_id: null } }, 401)
    }
    if (path === '/api/auth/login/') {
      authenticated = true
      return json(route, { access: 'e2e-access', kullanici: { id: 1, username: role === 'ADMIN' ? 'e2e-admin' : 'e2e-user', email: '', rol: role, is_active: true } })
    }
    if (path === '/api/auth/me/') return json(route, { id: 1, username: role === 'ADMIN' ? 'e2e-admin' : 'e2e-user', email: '', rol: role, is_active: true })
    if (path === '/api/auth/logout/') {
      authenticated = false
      return json(route, { mesaj: 'Oturum kapatıldı.' })
    }
    if (path === '/api/auth/admin-kontrol/') return role === 'ADMIN' ? json(route, { durum: 'izinli', rol: role }) : json(route, { hata: { kod: 'YETKI_REDDEDILDI', mesaj: 'Yetki yok.', alanlar: {}, trace_id: null } }, 403)
    if (path === '/api/tahminler/kayitlar/') return json(route, emptyPage)
    if (path === '/api/makineler/') return json(route, { ...emptyPage, count: 1, results: [{ id: 1, makine_kodu: 'E2E-M-01', ad: 'E2E Kritik Pres', kritiklik_seviyesi: 5, aktif: true, olusturulma_zamani: '2026-08-19T10:00:00Z', guncellenme_zamani: '2026-08-19T10:00:00Z' }] })
    if (path === '/api/stoklar/') return json(route, { ...emptyPage, count: 1, results: [{ id: 1, parca: { id: 10, parca_kodu: 'E2E-PRC-01', ad: 'E2E Kritik Röle', aktif: true, olusturulma_zamani: '', guncellenme_zamani: '' }, toplam_stok: 0, minimum_stok: 2, tedarik_gun: 3, kullanilabilir_stok: 0, stok_durumu: 'MEVCUT', stok_yeterli: false, guncellenme_zamani: '2026-08-19T10:00:00Z' }] })
    if (path === '/api/tahminler/loglari/') return json(route, { ...emptyPage, count: 1, results: [{ id: 'e2e-prediction', olcum_zamani: '2026-08-19T12:00:00Z', makine: { id: 1, kod: 'E2E-M-01', ad: 'E2E Kritik Pres' }, kaynak: 'MANUEL', risk_orani: 0.82, risk_uyarisi: true, genel_oncelik: 5, legacy_oncelik_seviyesi: 'KRITIK', legacy_nihai_oncelik_skoru: 90, karar_durumu: 'REDDEDILDI', karar_veren: 'e2e-admin', karar_zamani: '2026-08-19T12:10:00Z', karar_nedeni: 'E2E güvenli karar sözleşmesi', is_emri_bilgisi: null, onay_bilgisi: null, red_bilgisi: { neden: 'E2E güvenli karar sözleşmesi', karar_veren: 'e2e-admin', karar_zamani: '2026-08-19T12:10:00Z' } }] })
    if (path === '/api/parcalar/' || path === '/api/ariza-parca-kurallari/' || path === '/api/tahminler/replay-oturumlari/' || path === '/api/auth/kullanicilar/') return json(route, emptyPage)
    await route.fallback()
  })
}

export async function login(page: Page, role: Role) {
  const password = role === 'ADMIN' ? process.env.E2E_ADMIN_PASSWORD : process.env.E2E_USER_PASSWORD
  if (!password) throw new Error(`E2E_${role}_PASSWORD ortam değişkeni gerekli.`)
  await page.goto('/login')
  await page.getByLabel('Kullanıcı adı').fill(role === 'ADMIN' ? 'e2e-admin' : 'e2e-user')
  await page.getByLabel('Parola', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Giriş yap' }).click()
  await page.getByRole('heading', { name: 'Makine Sağlığı ve Bakım Görünümü' }).waitFor()
}
