import { expect, test } from '@playwright/test'

import { login, mockSession } from './api-fixture'

test('USER login, rol ayrımı, yetkisiz ekran ve logout UI contract', async ({ page }) => {
  await mockSession(page, 'USER')
  await login(page, 'USER')

  await expect(page.getByText('Makine Yönetimi')).toHaveCount(0)
  await page.goto('/app/yonetim/makineler')
  await expect(page.getByRole('heading', { name: 'Bu bölüme erişim yetkiniz yok' })).toBeVisible()
  await expect(page.getByText('E2E kritik demo makinesi')).toHaveCount(0)

  await page.getByRole('button', { name: 'Çıkış Yap' }).click()
  await expect(page).toHaveURL(/\/login$/)
})

test('ADMIN yönetim menüsü ve salt okunur ana sayfalar UI contract', async ({ page }) => {
  await mockSession(page, 'ADMIN')
  await login(page, 'ADMIN')

  await page.getByRole('link', { name: 'Makine Yönetimi' }).click()
  await expect(page.getByRole('heading', { name: 'Makine Yönetimi', exact: true })).toBeVisible()
  await expect(page.getByText('E2E Kritik Pres')).toBeVisible()
  await page.getByRole('link', { name: 'Stok Yönetimi' }).click()
  await expect(page.getByRole('heading', { name: 'Stok Yönetimi', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Tahmin Logları' }).click()
  await expect(page.getByRole('heading', { name: 'Tahmin Logları', exact: true })).toBeVisible()
  await expect(page.getByRole('table').getByText('Reddedildi')).toBeVisible()
})
