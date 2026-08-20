import { expect, test } from '@playwright/test'

import { login, mockSession } from './api-fixture'

test('intercepted Replay UI contract metrikleri Accuracy olmadan gösterir', async ({ page }) => {
  await mockSession(page, 'ADMIN')
  const detail = {
    id: 'replay-ui-contract', makine: { id: 1, kod: 'E2E-M-01', ad: 'E2E Kritik Pres' },
    split: 'test', durum: 'TAMAMLANDI', baslangic_ofseti: 0, toplam_oge: 250,
    varsayilan_batch_boyutu: 5, sanal_aralik_saniye: 60,
    baslatilma_zamani: '2026-08-19T10:00:00Z', tamamlanma_zamani: '2026-08-19T10:05:00Z',
    iptal_zamani: null, hata_mesaji: null,
    ilerleme: { bekleyen: 0, isleniyor: 0, basarili: 250, basarisiz: 0, atlandi: 0, tamamlanma_yuzdesi: 100 },
    olusturulma_zamani: '2026-08-19T09:55:00Z', version: 2,
    metrikler: {
      degerlendirilen_oge_sayisi: 250,
      binary: { precision: 0.8, recall: 0.9, f1: 0.847, pr_auc: 0.92, support: 50, predicted_positive: 55,
        confusion_matrix: { true_negative: 190, false_positive: 10, false_negative: 5, true_positive: 45 } },
      failure_types: {}, rnf_ground_truth_count: 0, metrik_uyarilari: [],
    },
    olaylar: [], son_ogeler: [],
  }
  await page.route('**/api/tahminler/replay-oturumlari/replay-ui-contract/', (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify(detail) }))
  await page.route('**/api/tahminler/replay-oturumlari/replay-ui-contract/ogeler/**', (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ count: 0, next: null, previous: null, results: [] }) }))

  await login(page, 'ADMIN')
  await page.goto('/app/replay/replay-ui-contract')
  await expect(page.getByText('E2E Kritik Pres Replay Oturumu')).toBeVisible()
  await expect(page.getByText('Precision', { exact: true })).toBeVisible()
  await expect(page.getByText('Recall', { exact: true })).toBeVisible()
  await expect(page.getByText('PR-AUC', { exact: true })).toBeVisible()
  await expect(page.getByText('Confusion Matrix')).toBeVisible()
  await expect(page.getByText(/Accuracy|Model Doğruluğu/i)).toHaveCount(0)
})
