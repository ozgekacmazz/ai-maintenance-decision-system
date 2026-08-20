# AI Destekli Bakım Karar Sistemi

Sensör ölçümlerinden arıza riski ve fiziksel arıza sinyalleri üreten; bunları açıklanabilir bakım kararlarına ve kullanıcı onaylı iş emirlerine dönüştüren Django/React tabanlı karar destek sistemidir. Model öneri üretir, iş kuralları canonical önceliği hesaplar, kullanıcı onaylar veya reddeder; yalnız onaydan sonra iş emri oluşur. Sistem kesin arıza garantisi vermez veya makineyi otomatik durdurmaz.

## Temel özellikler

- JWT login, HttpOnly refresh cookie ve backend tarafından zorlanan `ADMIN`/`USER` rolleri
- Makine, parça, stok ve kullanıcı yönetimi; en az yetkili makine lookup
- Celsius girişli Hızlı Analiz ve Kelvin canonical API/model sınırı
- Metadata kaynaklı, sürümlü input-domain doğrulaması
- Binary failure risk, multi-label HDF/PWF/OSF/TWF inference ve SHAP açıklamaları
- Kalıcı tahmin geçmişi, detay ve immutable snapshot'lar
- Kullanıcı kontrollü Onayla/Reddet; canonical 1–5 öncelik
- Aksiyon/parça/stok bilgili iş emri, state machine, SLA, ADMIN override ve immutable audit
- ADMIN Tahmin Logları
- Gerçek prepared AI4I verisinden idempotent sensör replay; pause/resume/cancel
- Precision, Recall, PR-AUC, Confusion Matrix ve yardımcı F1 replay metrikleri
- Güvenli, idempotent demo seed ve standart hata/trace ID sözleşmesi

## Mimari

```text
Sensör girdisi
  → input-domain contract doğrulaması
  → binary risk inference
  → multi-label failure inference
  → SHAP açıklaması
  → TahminKaydi + immutable snapshot'lar
  → legacy açıklama skorları + canonical 1–5 genel öncelik
  → kullanıcı Onayla/Reddet kararı
  → iş emri + canonical SLA
  → ADMIN override → immutable audit olayı
```

Model çıktısı risk ve fiziksel sinyallerdir. Canonical öncelik deterministik iş kuralı, onay/ret kullanıcı kararı, iş emri ise sürümlü operasyon aggregate'ıdır. Ayrıntılar [mimari belgesindedir](docs/ARCHITECTURE.md).

## Teknoloji ve dizinler

- Backend: Python 3.12, Django 5.2, Django REST Framework, PostgreSQL 17
- Frontend: React 19, TypeScript 6, Vite 8, Vitest, ESLint
- ML: pandas, NumPy, scikit-learn 1.8, joblib, SHAP
- Çalıştırma: Docker Compose

```text
backend/          Django uygulaması, migration ve testler
frontend/         React/TypeScript web uygulaması
ml/               Feature, eğitim, inference ve ML test paketi
data/metadata/    Sürümlü model/veri/input-domain metadata
data/processed/   Git dışı prepared veri
docs/             Aktif teknik ve tarihsel karar belgeleri
compose.yaml      Geliştirme servisleri
.env.example      Secret içermeyen environment şablonu
```

## Kurulum ve hızlı başlangıç

Önerilen yol Docker Desktop ve Docker Compose'dur. Host komutları için Python 3.12 ve Node.js **22.13+** gerekir; daha eski Node 22 sürümleri transit paket engine kontrolünü karşılamaz.

Depo kökünde:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py check
```

`.env` Git'e eklenmemeli; placeholder secret ve parolalar güçlü, ortama özgü değerlerle değiştirilmelidir. Frontend <http://localhost:5173>, backend <http://localhost:8000>, sağlık endpoint'i <http://localhost:8000/api/saglik/> adresindedir.

```powershell
docker compose logs -f
docker compose down
```

`docker compose down -v` veritabanı volume'unu kalıcı siler; normal durdurma komutu değildir. Windows/OneDrive altında mount değişiklikleri görünmezse Docker Desktop dosya paylaşım izinlerini kontrol edin.

## Model ve veri artefaktları

Ham/prepared CSV ve `.joblib` dosyaları Git dışında tutulur ve Compose tarafından salt okunur bağlanır. Model metadata'sındaki SHA-256, runtime sürümü, feature sırası ve sınıf sözleşmesi doğrulanmadan joblib yüklenmez. Artefakt yoksa sağlık endpoint'i çalışır; inference standart `503` döndürür. Eğitim uygulama başlangıcının parçası değildir.

Güvenilir yerel veriden yeniden üretim, depo kökünde:

```powershell
$env:PYTHONPATH="ml/src"
python ml/scripts/prepare_dataset.py
python ml/scripts/train_binary_model.py
python ml/scripts/train_failure_type_model.py
python ml/scripts/generate_input_domain_contract.py
```

## Demo seed

İzlenmeyen `.env` içinde `DEMO_ADMIN_USERNAME`, `DEMO_ADMIN_PASSWORD`, `DEMO_USER_USERNAME` ve `DEMO_USER_PASSWORD` zorunludur. Parolalar Django validator'larını geçmelidir. `DEBUG=False` ortamında ayrıca bilinçli `ALLOW_DEMO_SEED_IN_PRODUCTION=True` opt-in gerekir.

Depo kökünde, backend container'ında:

```powershell
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo
```

Komut idempotenttir, environment parolası değişirse canonical demo hesabının hashini günceller ve raw parola/hash yazdırmaz. Doğrulanmış seed 9 makine, 10 tahmin (5 bekleyen, 4 onaylanan, 1 reddedilen), 4 iş emri ve HAZIR durumda 250 gerçek replay öğesi üretir. Sunum akışı: [DEMO_SCENARIO](docs/DEMO_SCENARIO.md).

## Test, lint ve build

Backend — depo kökünden, container içinde:

```powershell
docker compose exec backend pytest
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
docker compose exec backend python -m compileall -q apps config
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
```

Frontend — host üzerinde `frontend/` dizininde:

```powershell
npm ci
npm test -- --run
npm run lint
npm run build
```

ML — host üzerinde depo kökünde:

```powershell
$env:PYTHONPATH="ml/src"
python -m pytest ml/tests
```

Son doğrulanan sonuçlar [FINAL_VERIFICATION](docs/FINAL_VERIFICATION.md) belgesindedir.

## Kullanıcı akışları ve yetkilendirme

- USER: giriş, makine lookup, Hızlı Analiz, tahmin geçmişi/detayı, izinli Onayla/Reddet ve iş emri operasyonları.
- ADMIN: USER yetkilerine ek olarak makine/parça/stok/kullanıcı CRUD, Tahmin Logları, replay mutation, atama, iptal ve priority override.
- `/api/makine-secenekleri/` aktif makine lookup'ıdır; admin CRUD endpoint'i değildir.
- Frontend `AdminRoute` yalnız UX korumasıdır; authoritative kontrol backend permission sınıflarındadır.

## ML değerlendirme yaklaşımı

Binary aday seçimi validation PR-AUC ile yapılır; threshold validation setinde seçilir ve test split yalnız final değerlendirmede kullanılır. Güncel threshold metadata'dan okunur (`0.22958333333333336`). Risk skoru kalibre edilmiş olasılık olarak sunulmaz. Ana replay metrikleri Precision, Recall, PR-AUC ve Confusion Matrix; F1 yardımcı metriktir. Multi-label `subset_accuracy` yalnız ayrı diagnostic olabilir ve binary replay metriği değildir.

SHAP, binary risk modelinin ve çalıştırılan fiziksel failure-type modellerinin pozitif sınıf çıktısını açıklar; nedensellik veya garanti değildir. RNF inference hedefi değil, yalnız ground truth politikasıdır.

## Canonical genel öncelik ve SLA

Sürüm `general-priority-1.0.0`:

```text
stok_katsayisi = 1 + tedarik_riski_skoru / 100
ham_genel_oncelik = risk_orani × makine_kritikligi × stok_katsayisi
```

Decimal/ROUND_HALF_UP ile quantize edilen ham değer 0–2→1, >2–4→2, >4–6→3, >6–8→4, >8–10→5 aralıklarına dönüştürülür. Legacy 0–100 skorlar yalnız açıklama/uyumluluk içindir; eski kayıtlar nullable canonical alanlarla gösterilir ve otomatik backfill yapılmaz.

İş emri kaynak önceliği immutable kalır; etkin öncelik ADMIN override ile değişebilir. `general-priority-sla-1.0.0`: 1→168, 2→120, 3→72, 4→24, 5→4 saat.

## Replay

Replay checksum doğrulamalı prepared AI4I test split'inden en fazla 1000 öğe oluşturur; demo seed 250 gerçek öğe seçer ve oturumu `HAZIR` bırakır. Kullanıcı başlatır; adımlar production tahmin servisini çağırır ve başarılı öğeleri `TahminKaydi` ile bağlar. Final metrik yalnız `TAMAMLANDI` oturumun başarılı öğelerinden hesaplanır. PR-AUC risk skorlarından hesaplanır; tek sınıflı durumda unavailable uyarısı döner. Binary replay response'unda Accuracy yoktur ve sahte tamamlanmış replay/metrik üretilmez.

## Input-domain ve sıcaklık birimleri

Hızlı Analiz UI Celsius kabul eder ve `K = °C + 273.15` ile dönüştürür. Backend API, entegrasyon ve replay canonical olarak Kelvin kullanır. Sürüm kontrollü contract training split istatistiklerinden üretilir; fiziksel, supported ve observed sınırları ayırır. SHA-256 ve feature-order uyuşmazlığı fail-fast sonuçlanır; hardcoded fallback yoktur. Ayrıntılar: [INPUT_DOMAIN](docs/INPUT_DOMAIN.md).

## Authentication, parola ve hata sözleşmesi

Django `UserAttributeSimilarity`, `MinimumLength`, `CommonPassword` ve `NumericPassword` validator'ları kullanıcı create/reset akışlarında authoritative kaynaktır. Parolalar yalnız `set_password()` ile hashlenir; raw değer response/loglara girmez. Access token frontend belleğinde, refresh token HttpOnly cookie'dedir. Gerçek secret, credential, ham veri ve model artefaktları repository'ye yazılmamalıdır.

```json
{
  "hata": {
    "kod": "DOGRULAMA_HATASI",
    "mesaj": "Gönderilen bilgilerde doğrulama hataları var.",
    "alanlar": {"alan": ["Kullanıcı dostu hata."]},
    "trace_id": "istemci-ve-log-ile-eslesen-kimlik"
  }
}
```

Validation `400`, auth `401`, permission `403`, bulunamayan kaynak `404`, conflict `409`, model/config unavailable `503` döner. Teknik exception ve stack trace sızdırılmaz.

## Bilinen sınırlamalar

- AI4I kimlik/zaman alanları sentetiktir; gerçek ekipman veya temporal genelleme kanıtı değildir.
- Gerçek ERP, MQTT/Kafka broker, background worker, bildirim, stok rezervasyonu ve satın alma entegrasyonu yoktur.
- Replay gerçek zamanlı IoT akışı değil, kontrollü HTTP batch simülasyonudur.
- Risk skoru kalibrasyon kanıtı olmayan model skorudur.
- TWF deneysel/yetersiz destekli sinyaldir; production deployment ve Sprint 21 bu teslim kapsamında değildir.

## Aktif belgeler

API sözleşmesi ve authenticated Swagger kullanımı için [OpenAPI dokümanı](docs/API_OPENAPI.md), izole browser teslim testleri için [E2E test dokümanı](docs/E2E_TESTING.md) kullanılır.

- [Ürün gereksinimleri](docs/PRODUCT_REQUIREMENTS.md)
- [Mimari](docs/ARCHITECTURE.md)
- [Bakım öncelik motoru](docs/MAINTENANCE_PRIORITY_ENGINE.md)
- [İş emri yaşam döngüsü](docs/WORK_ORDER_WORKFLOW.md)
- [Sensör replay](docs/SENSOR_REPLAY.md)
- [Input-domain sözleşmesi](docs/INPUT_DOMAIN.md)
- [Binary model kartı](docs/MODEL_CARD_BINARY_FAILURE.md)
- [Failure-type model kartı](docs/MODEL_CARD_FAILURE_TYPE.md)
- [Tahmin API](docs/PREDICTION_API.md)
- [Bakım API](docs/MAINTENANCE_API.md)
- [Authentication](docs/AUTH_FLOW.md)
- [Rol ve yetki matrisi](docs/ROLE_PERMISSION_MATRIX.md)
- [Güvenlik](docs/SECURITY_PLAN.md)
- [Hata sözleşmesi](docs/ERROR_CONTRACT.md)
- [Demo senaryosu](docs/DEMO_SCENARIO.md)
- [Final doğrulama](docs/FINAL_VERIFICATION.md)
- [Accessibility denetimi](docs/ACCESSIBILITY.md)
- [Security denetimi](docs/SECURITY_AUDIT.md)
- [Performance baz çizgisi](docs/PERFORMANCE_BASELINE.md)
- [Production deployment](docs/PRODUCTION_DEPLOYMENT.md)
- [Backup/restore](docs/BACKUP_RESTORE.md)
- [Final runbook](docs/FINAL_RUNBOOK.md)

`docs/decisions/` altındaki ADR'ler ve eski sprint bağlamı taşıyan analiz/raporlar tarihsel karar kanıtıdır; güncel çalışma davranışı için bu README ve aktif sözleşmeler esas alınır.
