# Playwright E2E Testleri

## Hızlı UI contract paketi

```bash
cd frontend
npm ci
npm run test:e2e:install
npm run test:e2e
```

Bu paket gerçek React uygulamasını Chromium'da açar; auth/rol guard, admin sayfaları, Celsius→Kelvin request ve standart hata/stale-result davranışını kontrollü API interception ile doğrular. Test adlarındaki `contract` ifadesi bunun gerçek backend/replay smoke testi olmadığını açık eder.

Gerçek ürün yolculukları ve replay ayrı çalıştırılır:

```bash
npm run test:e2e:real
npm run test:e2e:replay
npm run test:e2e:all
```

`test:e2e:real` gerçek JWT login, tahmin reddetme, onay/iş emri oluşturma, admin log filtreleri ve canonical priority override/audit akışını çalıştırır. `test:e2e:replay` açıkça `@real-replay` etiketli, artefaktlı 250 öğelik production replay servis smoke testidir. Yerel ölçümde replay yaklaşık 42–50 saniye sürmüştür.

Artefaktlar yalnız failure/retry durumunda `frontend/test-results/` ve `frontend/playwright-report/` altına yazılır; Git tarafından ignore edilir. Testlerde `waitForTimeout`, CSS class selector veya repository'de saklanan storage state kullanılmaz.

## İzole gerçek servis ortamı

Gerçek backend smoke için `compose.e2e.yaml` her zaman ayrı project name ile kullanılır:

```bash
docker compose -p sensor-21a-e2e -f compose.e2e.yaml up --build
```

Gerekli değerler process environment'ından sağlanır: `E2E_POSTGRES_PASSWORD`, `E2E_DJANGO_SECRET_KEY`, `E2E_DEMO_ADMIN_PASSWORD`, `E2E_DEMO_USER_PASSWORD`. Bunlar kaynak koda, trace'e veya screenshot adına yazılmaz. Ortam `sensor_e2e` DB'si ve Compose-project scoped volume kullanır; development/production DB veya volume'lerine bağlanmaz.

Browser testleri ayrıca `E2E_ADMIN_USERNAME`, `E2E_ADMIN_PASSWORD`, `E2E_USER_USERNAME` ve `E2E_USER_PASSWORD` bekler. Her tam gerçek koşudan önce yalnız backend container'ında şu güvenlik kontrollü komut çalıştırılır:

```bash
python manage.py reset_e2e
```

Komut DB adının tam olarak `sensor_e2e` olduğunu doğrulamadan hiçbir destructive işlem yapmaz; ardından `flush --no-input`, migration ve `seed_demo` çalıştırır. Son durumda 5 BEKLIYOR, 4 ONAYLANDI, 1 REDDEDILDI, 0 TUTARSIZ tahmin ile 1 HAZIR/250 öğeli replay sözleşmesini doğrular. İki ardışık koşunun her biri bu temiz başlangıçla çalıştırılmalıdır.

Harici ortamda Playwright için `PLAYWRIGHT_EXTERNAL_SERVER=1`, `PLAYWRIGHT_BASE_URL=http://127.0.0.1:15173` ve gerekirse `E2E_API_BASE_URL=http://127.0.0.1:18000` ayarlanır. 250 öğelik gerçek replay smoke hızlı contract paketine dahil değildir; artefaktlı izole Compose ortamında ayrı smoke olarak koşulur ve sahte tamamlanmış metrik enjekte edilmez.

Sorun giderme: browser eksikse `npm run test:e2e:install`; servis kullanılıyorsa backend `/api/saglik/` ve frontend URL'sini kontrol edin. E2E Compose dosyasını development veya production credential/DB ile çalıştırmayın.
