import { expect, test } from '@playwright/test'

import { login, mockSession } from './api-fixture'

test('Hızlı Analiz Celsius girdisini Kelvin payload olarak gönderir ve stale sonucu temizler', async ({ page }) => {
  await mockSession(page, 'USER')
  let payload: Record<string, number> | null = null
  let riskCall = 0
  await page.route('**/api/tahminler/input-domain/', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      schema_version: '1', contract_version: 'input-domain-1.0.0',
      fields: {
        hava_sicakligi_k: { supported_min: 290, supported_max: 310 },
        proses_sicakligi_k: { supported_min: 300, supported_max: 320 },
        donus_hizi_rpm: { supported_min: 1000, supported_max: 3000 },
        tork_nm: { supported_min: 1, supported_max: 100 },
        takim_asinmasi_dk: { supported_min: 0, supported_max: 300 },
      },
    }),
  }))
  await page.route('**/api/tahminler/risk/', async (route) => {
    riskCall += 1
    payload = route.request().postDataJSON() as Record<string, number>
    if (riskCall > 1) return route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ hata: { kod: 'GECERSIZ_ISTEK', mesaj: 'Sensör değerini kontrol edin.', alanlar: { tork_nm: ['Geçersiz değer.'] }, trace_id: 'safe-e2e-trace' } }) })
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ risk_orani: 0.82, risk_uyarisi: true, threshold: 0.5, model_version: 'e2e', pipeline_version: 'e2e', ariza_tipi_degerlendirmesi: null, aciklanabilirlik: null }) })
  })

  await login(page, 'USER')
  await page.getByRole('link', { name: 'Hızlı Analiz' }).click()
  await expect(page.getByLabel(/Hava sıcaklığı \(°C\)/)).toBeVisible()
  await page.getByRole('button', { name: 'Sensör Analizini Başlat' }).click()
  await expect(page.getByText('%82')).toBeVisible()
  expect(payload?.hava_sicakligi_k).toBeCloseTo(298.1, 5)
  expect(payload?.proses_sicakligi_k).toBeCloseTo(308.6, 5)

  await page.getByLabel('Tork').fill('42')
  await page.getByRole('button', { name: 'Sensör Analizini Başlat' }).click()
  await expect(page.getByRole('alert')).toContainText('Sensör değerini kontrol edin.')
  await expect(page.getByText('%82')).toHaveCount(0)
  await expect(page.getByText('Takip kodu: safe-e2e-trace')).toBeVisible()
  await expect(page.getByText(/Traceback|SELECT|DoesNotExist/)).toHaveCount(0)
})
