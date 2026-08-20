import { expect, test } from '@playwright/test'

import { openPredictionByMachineCode, realLogin, realLogout } from './real-helper'

test.describe.configure({ mode: 'serial' })

test('gerçek red, onay, iş emri, admin log ve canonical override journey', async ({ page }) => {
  const rejectionReason = 'Sprint 21 gerçek E2E saha doğrulaması nedeniyle reddedildi.'
  const workOrderTitle = 'Sprint 21 gerçek E2E bakım iş emri'
  const overrideReason = 'Sprint 21 gerçek E2E canonical öncelik doğrulaması'

  await realLogin(page, 'USER')
  const rejectId = await openPredictionByMachineCode(page, 'M-DEMO-103')
  await page.getByRole('button', { name: 'Reddet' }).click()
  await page.getByLabel('Red nedeni (isteğe bağlı)').fill(rejectionReason)
  const rejectResponse = page.waitForResponse((response) =>
    response.url().endsWith(`/api/tahminler/kayitlar/${rejectId}/reddet/`) && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Reddetmeyi Onayla' }).click()
  expect((await rejectResponse).status()).toBe(201)
  await expect(page.getByText('Bu değerlendirme reddedildi')).toBeVisible()
  await expect(page.getByText(`Neden: ${rejectionReason}`)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Reddet' })).toHaveCount(0)
  await page.reload()
  await expect(page.getByText('Bu değerlendirme reddedildi')).toBeVisible()

  const approveId = await openPredictionByMachineCode(page, 'M-DEMO-108')
  await page.getByRole('button', { name: 'Onayla' }).click()
  await expect(page.getByRole('heading', { name: 'Bakım Kararını Onayla' })).toBeVisible()
  await page.getByLabel('İş Emri Başlığı').fill(workOrderTitle)
  await page.getByLabel('Açıklama ve Talimatlar').fill('Gerçek E2E akışında üretim servis katmanı doğrulaması.')
  const createResponse = page.waitForResponse((response) =>
    response.url().endsWith('/api/bakim/is-emirleri/') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Onayla ve İş Emri Oluştur' }).click()
  const create = await createResponse
  expect(create.status()).toBe(201)
  const created = await create.json() as { id: string; is_emri_numarasi: string }
  await expect(page).toHaveURL(new RegExp(`/app/is-emirleri/${created.id}$`))
  await expect(page.getByText(`İş Emri ${created.is_emri_numarasi}`)).toBeVisible()
  await expect(page.getByText(workOrderTitle)).toBeVisible()
  await expect(page.getByText(/Öncelik [1-5]\/5/).first()).toBeVisible()
  await expect(page.getByText('İlgili Parça ve Stok Durumu')).toBeVisible()

  await page.goto(`/app/tahminler/${approveId}`)
  await expect(page.getByText('Bu bakım kararı onaylandı')).toBeVisible()
  await expect(page.getByRole('button', { name: created.is_emri_numarasi })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Onayla' })).toHaveCount(0)
  await page.reload()
  await expect(page.getByText('Bu bakım kararı onaylandı')).toBeVisible()

  await realLogout(page)
  await realLogin(page, 'ADMIN')
  await page.goto('/app/yonetim/tahmin-loglari')
  await page.getByLabel('Karar durumu').selectOption('REDDEDILDI')
  await expect(page.getByRole('table').getByText(rejectionReason)).toBeVisible()
  await page.getByLabel('Karar durumu').selectOption('ONAYLANDI')
  await expect(page.getByRole('link', { name: created.is_emri_numarasi })).toBeVisible()

  const detailResponse = page.waitForResponse((response) =>
    response.url().endsWith(`/api/bakim/is-emirleri/${created.id}/`) && response.request().method() === 'GET')
  await page.goto(`/app/is-emirleri/${created.id}`)
  const before = await (await detailResponse).json() as {
    kaynak_genel_oncelik: number; etkin_genel_oncelik: number; hedef_mudahale_zamani: string; version: number
  }
  const target = before.etkin_genel_oncelik === 5 ? 4 : 5
  await page.getByRole('button', { name: 'Öncelik Seviyesini Değiştir (Admin)' }).click()
  await page.getByLabel('Yeni Etkin Öncelik').selectOption(String(target))
  await page.getByLabel('Müdahale Gerekçesi (Zorunlu)').fill(overrideReason)
  const overrideResponse = page.waitForResponse((response) =>
    response.url().endsWith(`/api/bakim/is-emirleri/${created.id}/oncelik-override/`) && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Önceliği Değiştir' }).click()
  const override = await overrideResponse
  expect(override.status()).toBe(200)
  const after = await override.json() as typeof before
  expect(after.kaynak_genel_oncelik).toBe(before.kaynak_genel_oncelik)
  expect(after.etkin_genel_oncelik).toBe(target)
  expect(after.version).toBe(before.version + 1)
  expect(after.hedef_mudahale_zamani).not.toBe(before.hedef_mudahale_zamani)
  await expect(page.getByText(overrideReason)).toBeVisible()
  await expect(page.getByText(`— Öncelik ${before.etkin_genel_oncelik}/5 → ${target}/5`)).toBeVisible()
  await page.reload()
  await expect(page.getByText(overrideReason)).toBeVisible()

  await realLogout(page)
  await realLogin(page, 'USER')
  await page.goto(`/app/is-emirleri/${created.id}`)
  await expect(page.getByRole('button', { name: 'Öncelik Seviyesini Değiştir (Admin)' })).toHaveCount(0)
})
