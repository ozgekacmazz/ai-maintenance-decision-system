# Final package contents

Bu belge Sprint 21 deployable/demo bundle sözleşmesini tanımlar.

Paket; backend, frontend ve ML kaynaklarını, migration ve testleri, aktif dokümantasyonu, Docker/production yapılandırmasını, `.env.example` şablonlarını, `ml/artifacts/` altındaki doğrulanmış binary/failure-type joblib dosyalarını, `data/metadata/` sözleşmelerini ve replay için `data/processed/ai4i2020_prepared.csv` dosyasını içerir. `ARTIFACT_CHECKSUMS.sha256` runtime artifact ve verilerinin SHA-256 değerlerini listeler.

Paket; `.git`, gerçek `.env`, secret, raw AI4I verisi, virtual environment, `node_modules`, build/cache/coverage/log/IDE çıktıları ve eski ZIP dosyalarını içermez. Raw veri yeniden eğitim için UCI AI4I 2020 kaynağından veya kurumdaki doğrulanmış kopyadan edinilmeli; README'deki deterministik prepare/train komutları izlenmelidir.

## İlk çalıştırma

1. `.env.example` dosyasını `.env` olarak kopyalayıp tüm placeholder secret ve demo parolalarını değiştirin.
2. `docker compose up --build -d` komutunu çalıştırın.
3. `docker compose exec backend python manage.py migrate` ve `docker compose exec backend python manage.py check` komutlarını çalıştırın.
4. Onaylı demo ortamında environment demo hesapları tanımlıyken `docker compose exec backend python manage.py seed_demo` komutunu çalıştırın.

TLS bu Compose stack'inin önündeki güvenilir edge/load balancer'da sonlanmalı; edge `X-Forwarded-Proto` ve istemci IP bilgisini overwrite etmeli ve proxy'ye doğrudan erişim firewall ile engellenmelidir. Ayrıntılar `docs/PRODUCTION_DEPLOYMENT.md` belgesindedir.
