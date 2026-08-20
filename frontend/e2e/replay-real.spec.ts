import { expect, test } from '@playwright/test'

import { realLogin } from './real-helper'

test('gerçek artefaktlı replay smoke @real-replay', async ({ page }) => {
  test.setTimeout(15 * 60_000)
  await realLogin(page, 'ADMIN')
  const listResponse = page.waitForResponse((response) =>
    response.url().includes('/api/tahminler/replay-oturumlari/') && response.request().method() === 'GET')
  await page.goto('/app/replay')
  const list = await (await listResponse).json() as { results: Array<{ id: string; durum: string; toplam_oge: number }> }
  const ready = list.results.find((item) => item.durum === 'HAZIR' && item.toplam_oge === 250)
  if (!ready) throw new Error('Seed fixture hatası: 250 öğeli HAZIR replay bulunamadı.')

  await page.goto(`/app/replay/${ready.id}`)
  await expect(page.getByText(/İlerleme: 0 \/ 250/)).toBeVisible()
  const start = page.waitForResponse((response) => response.url().endsWith(`/api/tahminler/replay-oturumlari/${ready.id}/baslat/`))
  await page.getByRole('button', { name: 'Başlat' }).click()
  expect((await start).status()).toBe(200)
  await page.getByLabel('Batch Boyutu:').selectOption('25')

  for (let processed = 0; processed < 250; processed += 25) {
    const step = page.waitForResponse((response) =>
      response.url().endsWith(`/api/tahminler/replay-oturumlari/${ready.id}/adim/`) && response.request().method() === 'POST')
    await page.getByRole('button', { name: '25 Adım İşle' }).click()
    expect((await step).status()).toBe(200)
  }

  await expect(page.getByText('Tamamlandı', { exact: true })).toBeVisible({ timeout: 120_000 })
  await expect(page.getByText('Precision', { exact: true })).toBeVisible()
  await expect(page.getByText('Recall', { exact: true })).toBeVisible()
  await expect(page.getByText('PR-AUC', { exact: true }).or(page.getByText(/PR-AUC hesaplanamadı/))).toBeVisible()
  await expect(page.getByText('F1-Skoru (Yardımcı)')).toBeVisible()
  await expect(page.getByText('Confusion Matrix')).toBeVisible()
  await expect(page.getByText(/Accuracy|Model Doğruluğu/i)).toHaveCount(0)
})
