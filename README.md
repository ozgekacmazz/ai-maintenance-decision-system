# AI Destekli Bakım Karar Sistemi

Bu depo, makinelerin sensör verilerinden arıza riski üreten bakım karar destek sisteminin belgelerini, uygulamasını ve ML paketini içerir.

Kalıcı tahminler ayrıca saf, versiyonlu ve açıklanabilir bir kural motoruyla teknik
aciliyet, tedarik riski ve bakım önceliği snapshot'ı üretir. Formüller ve güvenlik
sınırları [bakım öncelik motoru belgesinde](docs/MAINTENANCE_PRIORITY_ENGINE.md) yer alır.

Bakım kararı, optimistic concurrency ve immutable olay geçmişi kullanan kontrollü
[iş emri yaşam döngüsüne](docs/WORK_ORDER_WORKFLOW.md) dönüştürülebilir.

Prepared sensör kayıtları, checksum doğrulamalı ve bounded-step
[sensör replay altyapısıyla](docs/SENSOR_REPLAY.md) güvenli biçimde oynatılabilir.

## Proje durumu

Sprint 19A itibarıyla altyapı, kullanıcı/JWT akışı, merkezi hata sözleşmesi, hiyerarşik risk/fiziksel arıza tipi endpoint'i, SHAP açıklanabilirlik, versiyonlu bakım öncelik motoru, iş emri yaşam döngüsü, deterministik sensör replay altyapısı, premium ürün arayüzü, risk dashboard'u ve hızlı sensör analizi uygulanmıştır.

## Kapsam

PDF'nin zorunlu kapsamı şunlardır:

- USER ve ADMIN rolleriyle kullanıcı girişi,
- öncelik sıralı risk listesi,
- tahmin gerekçesi, önerilen aksiyon, gerekli parça ve stok bilgisini gösteren makine detay ekranı,
- kullanıcı onayı ve ret akışı,
- onaylanmış kayıtları gösteren iş emirleri ekranı,
- makine/stok, tahmin logu ve kullanıcı yönetimi sunan admin ekranları,
- demo verisini satır satır besleyen replay akışı,
- ilk üç açıklama faktörünün mutlak SHAP etkisine göre gösterilmesi,
- kullanıcı onayı olmadan iş emri oluşturulmaması.

PDF'deki FastAPI, Streamlit, AI4I, Random Forest, 0.60 eşik değeri ve örnek minimum tablo alanları öneridir. Proje teknoloji kararı Django REST Framework, React/TypeScript ve PostgreSQL'dir. AI4I demo veri seti ve Random Forest ana model adayı olarak benimsenmiştir; nihai model ve eşik ölçüm sonuçlarıyla seçilecektir.

## Temel ürün kararları

- Genel öncelik; arıza riski, makine kritikliği ve stok katsayısına dayanır ve 1–5 arasında tam sayı olarak gösterilir.
- Bakım önceliği ve tedarik önceliği, genel önceliği açıklayan yardımcı alt skorlardır.
- Sistem yalnızca iş emri taslağı sunar; kullanıcı onayından önce iş emri oluşturmaz.
- Onay ve ret kararları kullanıcı kimliği ve zamanıyla kaydedilir.
- Gerçek ERP bağlantısı ilk sürüm kapsamında değildir. ERP'ye hazır iç veri modeli ve API tasarlanacaktır.
- Kullanıcı kaydı self-service değildir; kullanıcıları ADMIN oluşturur.

## Veri ve model özeti

- Sentetik `machine_id` ve `timestamp` yalnız replay/demo amacıyla kullanılır; temporal model başarımı için kanıt değildir.
- Sıcaklık farkı ve mekanik güç özellikleri türetilir.
- Accuracy model seçiminde veya değerlendirmesinde kullanılmaz.
- Precision, recall, F1, PR-AUC, confusion matrix, false positive ve false negative değerlendirilir.
- Model joblib ile `.joblib` artefaktına kaydedilir ve uygulama çalışırken yeniden eğitilmez.
- Mevcut joblib modelleri scikit-learn `1.8.0` ile üretilmiştir; eğitim ve serving
  aynı exact sürüme sabitlenir. Sürüm yükseltmesi eski joblib ile yapılmaz: modeller
  güvenilir veriyle yeniden eğitilir, test edilir ve yeni checksum/sürümle yayımlanır.

## Belgeler

- [Ürün gereksinimleri](docs/PRODUCT_REQUIREMENTS.md)
- [Mimari](docs/ARCHITECTURE.md)
- [Hiyerarşik tahmin akışı](docs/HIERARCHICAL_PREDICTION_FLOW.md)
- [SHAP açıklanabilirlik altyapısı](docs/SHAP_EXPLAINABILITY.md)
- [SHAP API entegrasyonu](docs/SHAP_API_INTEGRATION.md)
- [Veri ve ML planı](docs/DATA_AND_ML_PLAN.md)
- [Güvenlik planı](docs/SECURITY_PLAN.md)
- [Hata sözleşmesi](docs/ERROR_CONTRACT.md)
- [Terim sözlüğü](docs/TERIM_SOZLUGU.md)
- [Mimari karar kayıtları](docs/decisions/)

## Sprint 1: çalışan proje altyapısı

Sprint 0 kararları korunarak Django REST Framework, React/TypeScript/Vite ve
PostgreSQL için Docker Compose ile çalıştırılabilir geliştirme altyapısı eklendi.

### Gereksinimler ve ortam hazırlığı

Docker Desktop ile Docker Compose gereklidir. Depo kökünde örnek ortam dosyasını
kopyalayın; değerler yalnız yerel geliştirme içindir ve gerçek ortamlarda
değiştirilmelidir.

```powershell
Copy-Item .env.example .env
```

Kalıcı ve denetlenebilir makine tahminlerinin create/list/detail, idempotency ve ERP
snapshot sözleşmesi için [kalıcı tahmin kayıtları belgesine](docs/PREDICTION_RECORDS.md)
bakın. Stateless `/api/tahminler/risk/` veritabanına kayıt yazmaz.

### Docker ile başlatma

```powershell
docker compose up --build
```

Servis adresleri:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Sağlık kontrolü: http://localhost:8000/api/saglik/
- PostgreSQL: yerel makinede `localhost:5432`, Docker ağında `db:5432`

Migration çalıştırmak için:

```powershell
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py makemigrations --check --dry-run
```

## Sprint 3: kullanıcı yönetimi ve admin bootstrap

Ürün rol politikaları, transaction'lı kullanıcı servisleri, selector'lar ve
idempotent geliştirme/demo admin bootstrap komutu eklenmiştir. Ayrıntılar için
[rol ve yetki matrisine](docs/ROLE_PERMISSION_MATRIX.md) bakın.

İzlenmeyen `.env` dosyanızda aşağıdaki environment değişkenlerini tanımlayın:

- `ADMIN_USERNAME` (zorunlu)
- `ADMIN_PASSWORD` (zorunlu)
- `ADMIN_EMAIL` (opsiyonel)

İlk çalıştırma ve idempotent tekrar çalıştırma aynı komutla yapılır:

```powershell
docker compose exec backend python manage.py seed_admin
```

Mevcut bootstrap yöneticisinin parolasını bilinçli olarak yenilemek için:

```powershell
docker compose exec backend python manage.py seed_admin --update-password
```

Tekrar çalıştırma ikinci kullanıcı oluşturmaz ve `--update-password` verilmedikçe
mevcut parolayı değiştirmez. Parolayı komut satırı argümanı, Git kapsamındaki bir
dosya veya shell history içine yazmayın. Bu komut yalnız development/demo
bootstrap içindir; production secret yönetimi değildir. Sprint 3 henüz login,
JWT veya kullanıcı CRUD API endpoint'i içermez.

## Sprint 4: güvenli authentication

Authentication akışı `GET /api/auth/csrf/` ile başlar. Login kısa ömürlü access
tokenı JSON gövdesinde, refresh tokenı ise JavaScript'in okuyamadığı HttpOnly
cookie içinde döndürür. Refresh rotation eski tokenı blacklist eder; logout
refresh tokenı blacklist edip cookie'yi siler. Ayrıntılı sequence ve tehdit
sınırları için [authentication akışına](docs/AUTH_FLOW.md) bakın.

Frontend access tokenı yalnız React/modül belleğinde tutar; localStorage,
sessionStorage veya IndexedDB kullanılmaz. Sayfa yenilemesinde HttpOnly cookie ile
refresh ve ardından `/me/` çağrısı yapılır. Development'ta cookie `Secure=False`,
`SameSite=Lax`, `Path=/api/auth/` kullanır. Production HTTPS ortamında
`JWT_REFRESH_COOKIE_SECURE=True` zorunludur.

F12 Network panelinde access tokenın login/refresh response'unda bulunduğu, fakat
refresh tokenın JSON'a girmediği doğrulanabilir. Application/Cookies panelinde
refresh cookie HttpOnly görünmelidir. Token değerlerini console'a, loglara veya
ekran görüntülerine taşımayın. Süresi dolmuş blacklist kayıtlarının bakımı:

```powershell
docker compose exec backend python manage.py flushexpiredtokens
```

## Sprint 5: hata ve takip kodu

`/api/` hataları kararlı `hata.kod`, güvenli mesaj, alan hataları ve `trace_id`
ile döner. Aynı kimlik `X-Trace-ID` header'ında ve yapılandırılmış request logunda
bulunur. Kullanıcı beklenmeyen bir hata sürerse bu takip kodunu destek ekibine
iletebilir. Ayrıntılar: [hata sözleşmesi](docs/ERROR_CONTRACT.md) ve
[güvenli loglama](docs/OBSERVABILITY.md).

## Sprint 6: bakım CRUD API'leri

Makine, parça, güncel stok ve arıza–parça kuralları için JWT korumalı, sayfalı
REST endpoint'leri eklendi. USER aktif kayıtları okuyabilir; yalnız ürün rolü ADMIN
yazabilir ve pasif kayıtları görebilir. Endpoint, filtre ve hata ayrıntıları için
[bakım API belgesine](docs/MAINTENANCE_API.md) bakın.

## Sprint 7: AI4I veri hazırlama hattı

Resmi UCI AI4I 2020 verisini doğrulayan, profilleyen ve deterministik demo alanlarıyla
hazırlayan bağımsız `ml/` paketi eklendi. Ham ve işlenmiş CSV dosyaları Git dışındadır;
ayrıntılar [veri profili](docs/DATASET_PROFILE.md) belgesindedir. Model henüz eğitilmez.

```powershell
python -m pip install -e ".\ml[dev]"
$env:PYTHONPATH="ml/src"
python ml/scripts/inspect_dataset.py
python ml/scripts/prepare_dataset.py
pytest ml/tests
python -m ruff check ml
python -m ruff format --check ml
```

Hazırlama çıktısı `data/processed/ai4i2020_prepared.csv`, güvenli metadata çıktısı
`data/metadata/ai4i2020_prepared.json` konumundadır. Sentetik `machine_id` ve
`timestamp` yalnız demo/replay içindir; gerçek makine veya temporal bilgi değildir.

## Sprint 8: binary arıza modeli

`Machine failure` hedefi için leakage-safe Logistic Regression ve Random Forest
karşılaştırması, validation tabanlı threshold seçimi ve checksum doğrulamalı model
artefaktı üretimi eklendi. Sonuçlar ve sınırlar [binary model raporundadır](docs/BINARY_MODEL_REPORT.md).

```powershell
$env:PYTHONPATH="ml/src"
python ml/scripts/train_binary_model.py
```

Komut sürümlü artefaktı `ml/artifacts/` altında üretir; bu dizin Git dışındadır.
İzlenebilir metrikler ve artefakt checksum'ı `data/metadata/binary_failure_model.json`
dosyasına yazılır. Joblib artefaktı yalnız güvenilir yerel kaynaktan ve metadata'daki
SHA-256 doğrulandıktan sonra yüklenmelidir.

## Sprint 9: binary risk tahmin API'si

JWT korumalı `POST /api/tahminler/risk/` endpoint'i kanonik sensör alanlarını
doğrular, `bakim_ml` paketindeki ortak feature engineering kodunu kullanır ve
metadata threshold'una göre risk uyarısı döndürür. Model ilk tahmin isteğinde
checksum, sürüm, feature sırası ve sınıf sözleşmesi doğrulandıktan sonra bellekte
önbelleğe alınır; uygulama çalışırken model eğitilmez. Ayrıntılar
[tahmin API belgesindedir](docs/PREDICTION_API.md).

Gerçek `.joblib` dosyası pickle tabanlı güvenlik ve boyut nedenleriyle Git'e
alınmaz. Yerel AI4I verisi hazırlandıktan sonra güvenilir artefaktı üretmek için:

```powershell
$env:PYTHONPATH="ml/src"
python ml/scripts/train_binary_model.py
```

Docker Compose, `ml/` dizinini salt okunur bağlar. Model dosyası yoksa backend ve
sağlık endpoint'i çalışmaya devam eder; yalnız tahmin endpoint'i standart `503`
döndürür. Sprint 9 kontrolleri:

```powershell
docker compose build backend
docker compose up -d db backend
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend pytest
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
```

## Sprint 10: arıza tipi etiket analizi

AI4I arıza tipi etiketlerinin multi-label yapısını, RNF tutarsızlığını ve
mevcut binary split içindeki dağılımı tekrarlanabilir biçimde analiz etmek için:

```powershell
$env:PYTHONPATH="ml/src"
python ml/scripts/analyze_failure_labels.py
```

Sonuçlar [arıza tipi etiket analizi](docs/FAILURE_LABEL_ANALYSIS.md) belgesinde ve
`data/metadata/failure_label_analysis.json` metadata dosyasında yer alır. Bu
sprint model eğitmez veya mevcut tahmin API'sini değiştirmez.

## Sprint 11: fiziksel arıza tipi modeli

TWF, HDF, PWF ve OSF için dört bağımsız pipeline'dan oluşan multi-label
modeli çevrimdışı eğitmek için:

```powershell
$env:PYTHONPATH="ml/src"
python ml/scripts/train_failure_type_model.py
```

Deney ayrıntıları [failure-type model raporunda](docs/FAILURE_TYPE_MODEL_REPORT.md),
kullanım sınırları [model kartında](docs/MODEL_CARD_FAILURE_TYPE.md) yer alır.
`ml/artifacts/failure-type-1.0.0.joblib` pickle tabanlı olduğu için Git dışında
tutulur; uygulama çalışırken eğitim yapılmaz.

## Sprint 12: hiyerarşik tahmin API'si

Mevcut `POST /api/tahminler/risk/` endpoint'i önce binary riski hesaplar ve yalnız
risk threshold'u aşıldığında fiziksel arıza tipi modelini çalıştırır. HDF/PWF/OSF
operasyonel aday, TWF yetersiz destekli deneysel sinyal, RNF ise model dışıdır.
İki artefakt ayrı checksum doğrulaması ve lazy cache kullanır. Ayrıntılar
[hiyerarşik tahmin akışında](docs/HIERARCHICAL_PREDICTION_FLOW.md) ve
[API sözleşmesinde](docs/PREDICTION_API.md) yer alır.

## Sprint 13: doğrulanmış SHAP açıklamaları

Binary risk ve dört fiziksel arıza tipi pipeline'ı için pozitif sınıfı açıklayan,
SHAP sürüm shape'lerini normalize eden ve tam katkı vektöründe additivity
doğrulayan ortak ML katmanı eklendi. Validation örneğinden deterministik ve yalnız
toplulaştırılmış global önem raporu üretilebilir. Django/API entegrasyonu Sprint 14
kapsamındadır; ayrıntılar [SHAP açıklanabilirlik belgesindedir](docs/SHAP_EXPLAINABILITY.md).

### Test ve kalite kontrolleri

```powershell
docker compose exec backend pytest
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
docker compose exec frontend npm test -- --run
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
```

Logları izlemek ve servisleri durdurmak için:

```powershell
docker compose logs -f
docker compose down
```

`docker compose down -v` PostgreSQL verisini kalıcı olarak siler; yalnız veriyi
bilerek sıfırlamak istediğinizde kullanın.

Windows/OneDrive altında dosya değişiklikleri algılanmazsa Docker Desktop dosya
paylaşım izinlerini kontrol edin. Gerekirse Vite polling ayarı ayrıca açılabilir;
varsayılan yapı gereksiz polling kullanmaz.

### Henüz uygulanmayan özellikler

SHAP, tahmin kaydı, replay, risk dashboard'u, öncelik motoru,
karar/iş emri ve ERP entegrasyonu sonraki sprintlerin kapsamındadır.

## Sprint 2: temel veri modeli

Özel `Kullanici` modeli ile makine, parça, güncel stok ve arıza–parça kuralı
modelleri eklenmiştir. Şema, ilişkiler, constraint ve index gerekçeleri için
[Sprint 2 ER diyagramına](docs/ER_DIAGRAM.md) bakın. Ürün rolü (`USER`/`ADMIN`)
Django'nun `is_staff` ve `is_superuser` yetkilerinden bağımsızdır.

Migration durumunu doğrulamak için:

```powershell
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py showmigrations
docker compose exec backend python manage.py makemigrations --check --dry-run
```
