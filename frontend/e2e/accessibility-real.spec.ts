import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

import { realLogin, realLogout } from './real-helper'

async function expectNoSeriousViolations(page: Page, routeName: string) {
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  const blocking = result.violations.filter((item) => item.impact === 'critical' || item.impact === 'serious')
  expect(blocking, `${routeName}: ${blocking.map((item) => `${item.id} (${item.nodes.length})`).join(', ')}`).toEqual([])
}

test('login route axe ve klavye erişimi', async ({ page }) => {
  await page.goto('/login')
  await expectNoSeriousViolations(page, 'Login')
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('Kullanıcı adı')).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('Parola', { exact: true })).toBeFocused()
})

test('USER ana route matrisi axe critical/serious sıfır', async ({ page }) => {
  await realLogin(page, 'USER')
  for (const [name, route] of [
    ['Dashboard', '/app'],
    ['Hızlı Analiz', '/app/analiz'],
    ['Tahmin Geçmişi', '/app/tahminler'],
    ['İş Emirleri', '/app/is-emirleri'],
    ['Replay Listesi', '/app/replay'],
    ['Yetkisiz Erişim', '/app/yonetim/makineler'],
  ] as const) {
    await page.goto(route)
    await expect(page.locator('main')).toBeVisible()
    await expectNoSeriousViolations(page, name)
  }
  await page.keyboard.press('Home')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'İçeriğe geç' })).toBeFocused()
})

test('ADMIN yönetim route matrisi axe critical/serious sıfır', async ({ page }) => {
  await realLogin(page, 'ADMIN')
  for (const [name, route] of [
    ['Makine Yönetimi', '/app/yonetim/makineler'],
    ['Stok Yönetimi', '/app/yonetim/stok'],
    ['Kullanıcı Yönetimi', '/app/yonetim/kullanicilar'],
    ['Tahmin Logları', '/app/yonetim/tahmin-loglari'],
  ] as const) {
    await page.goto(route)
    await expect(page.locator('main')).toBeVisible()
    await expectNoSeriousViolations(page, name)
  }
  await realLogout(page)
})

test('ADMIN kullanıcı modalı focus trap, Escape ve opener focus restore', async ({ page }) => {
  await realLogin(page, 'ADMIN')
  await page.goto('/app/yonetim/kullanicilar')

  const opener = page.getByRole('button', { name: 'Yeni Kullanıcı' })
  await opener.click()
  const dialog = page.getByRole('dialog', { name: 'Yeni Kullanıcı Tanımla' })
  await expect(dialog).toBeVisible()
  await expect(page.getByLabel('Kullanıcı Adı *')).toBeFocused()
  await expectNoSeriousViolations(page, 'Kullanıcı create modalı')

  await page.keyboard.press('Shift+Tab')
  await expect(dialog.getByRole('button', { name: 'Yeni kullanıcı penceresini kapat' })).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect(dialog.getByRole('button', { name: 'Oluştur' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(dialog.getByRole('button', { name: 'Yeni kullanıcı penceresini kapat' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel('Kullanıcı Adı *')).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await expect(opener).toBeFocused()

  const resetOpener = page.getByRole('button', { name: 'Şifre Güncelle' }).first()
  await resetOpener.click()
  const resetDialog = page.getByRole('dialog', { name: 'Parola Sıfırla' })
  await expect(page.getByLabel('Yeni Parola *')).toBeFocused()
  await expectNoSeriousViolations(page, 'Kullanıcı parola sıfırlama modalı')
  await page.keyboard.press('Escape')
  await expect(resetDialog).toBeHidden()
  await expect(resetOpener).toBeFocused()
})
