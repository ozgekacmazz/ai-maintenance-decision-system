import { expect, test } from '@playwright/test'

import { realLogin, realLogout } from './real-helper'

test.describe.configure({ mode: 'serial' })

test('production proxy headers, CSP, ADMIN ve USER smoke', async ({ page, request }) => {
  const consoleErrors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error' && message.text().toLowerCase().includes('content security policy')) {
      consoleErrors.push(message.text())
    }
  })

  const index = await request.get('/')
  expect(index.status()).toBe(200)
  expect(index.headers()['content-security-policy']).toContain("default-src 'self'")
  expect(index.headers()['content-security-policy']).not.toContain('unsafe-eval')
  expect(index.headers()['content-security-policy']).not.toContain('unsafe-inline')
  expect(index.headers()['permissions-policy']).toContain('camera=()')
  expect(index.headers()['cache-control']).toBe('no-cache')

  const health = await request.get('/api/saglik/')
  expect(health.status()).toBe(200)
  expect(health.headers()['cache-control']).toContain('no-store')
  expect(await health.json()).toMatchObject({ durum: 'hazir', migrationlar: 'uygun', model_dosyalari: 'hazir' })
  expect((await request.get('/api/docs/')).status()).toBe(404)

  await realLogin(page, 'ADMIN')
  await page.goto('/app/yonetim/tahmin-loglari')
  await expect(page.getByRole('heading', { name: 'Tahmin Logları' })).toBeVisible()
  await page.goto('/app/yonetim/makineler')
  await expect(page.getByRole('heading', { name: 'Makine Yönetimi (Admin)' })).toBeVisible()
  await page.goto('/app/yonetim/stok')
  await expect(page.getByRole('heading', { name: 'Stok ve Parça Yönetimi (Admin)' })).toBeVisible()
  await realLogout(page)

  await realLogin(page, 'USER')
  await page.goto('/app/analiz')
  await expect(page.getByRole('spinbutton', { name: /Hava sıcaklığı \(°C\)/ })).toBeVisible()
  await page.goto('/app/tahminler')
  await expect(page.getByRole('table')).toBeVisible()
  await page.goto('/app/is-emirleri')
  await expect(page.getByRole('table')).toBeVisible()
  await page.goto('/app/replay')
  await expect(page.getByRole('table')).toBeVisible()
  expect(consoleErrors).toEqual([])
})

test('production login edge rate limit JSON ve Retry-After döndürür', async ({ request }) => {
  const statuses: number[] = []
  let retryAfter: string | undefined
  for (let attempt = 0; attempt < 12; attempt += 1) {
    const response = await request.post('/api/auth/login/', {
      data: { username: 'invalid-rate-test', password: 'invalid-rate-test' },
    })
    statuses.push(response.status())
    if (response.status() === 429) {
      retryAfter = response.headers()['retry-after']
      expect(response.headers()['content-type']).toContain('application/json')
      expect(await response.json()).toMatchObject({ hata: { kod: 'ISTEK_SINIRI' } })
      break
    }
  }
  expect(statuses).toContain(429)
  expect(retryAfter).toBe('60')
})
