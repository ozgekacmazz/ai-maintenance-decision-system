import { expect, type Page } from '@playwright/test'

type Role = 'ADMIN' | 'USER'

function required(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error(`${name} ortam değişkeni gerekli.`)
  return value
}

export async function realLogin(page: Page, role: Role) {
  const apiBaseURL = process.env.E2E_API_BASE_URL ?? 'http://127.0.0.1:18000'
  const health = await page.request.get(`${apiBaseURL}/api/saglik/`)
  if (!health.ok()) throw new Error(`Gerçek E2E backend health başarısız: ${health.status()}`)
  const username = required(`E2E_${role}_USERNAME`)
  const password = required(`E2E_${role}_PASSWORD`)
  await page.goto('/login')
  await page.getByLabel('Kullanıcı adı').fill(username)
  await page.getByLabel('Parola', { exact: true }).fill(password)
  const response = page.waitForResponse((item) => item.url().endsWith('/api/auth/login/'))
  await page.getByRole('button', { name: 'Giriş yap' }).click()
  expect((await response).status(), `${role} gerçek login başarısız`).toBe(200)
  await expect(page).toHaveURL(/\/app$/)
}

export async function realLogout(page: Page) {
  await page.getByRole('button', { name: 'Çıkış Yap' }).click()
  await expect(page).toHaveURL(/\/login$/)
}

export async function openPredictionByMachineCode(page: Page, machineCode: string): Promise<string> {
  await page.goto('/app/tahminler')
  const detailLink = page.getByRole('link', { name: `${machineCode} tahmin detayını aç` })
  await expect(detailLink, `Seed fixture hatası: ${machineCode} için tek tahmin satırı gerekli.`).toHaveCount(1)
  await detailLink.click()
  await expect(page).toHaveURL(/\/app\/tahminler\/[0-9a-f-]+$/)
  const id = page.url().split('/').at(-1)
  if (!id) throw new Error(`${machineCode} tahmin kimliği URL'den okunamadı.`)
  await expect(page.getByRole('button', { name: 'Onayla' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Reddet' })).toBeVisible()
  return id
}
