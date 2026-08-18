# AI Destekli Bakım Karar Sistemi

Bu depo, makinelerin sensör verilerinden arıza riski ve olası arıza türü üreten; sonucu açıklayan; makine kritikliği, stok ve tedarik bilgileriyle önceliklendiren bir bakım karar destek sisteminin Sprint 0 belgelerini içerir.

## Proje durumu

Sprint 0'da gereksinimler, mimari, veri ve makine öğrenmesi yaklaşımı, güvenlik, hata sözleşmesi ve temel teknik kararlar belgelenmiştir. Uygulama, replay akışı, veri hattı ve model henüz geliştirilmemiştir.

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

## Belgeler

- [Ürün gereksinimleri](docs/PRODUCT_REQUIREMENTS.md)
- [Mimari](docs/ARCHITECTURE.md)
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

Sprint 1 yalnız altyapıyı kapsar. Kimlik doğrulama, kullanıcı ve domain modelleri,
risk dashboard'u, tahmin/ML, replay, stok, iş emri ve ERP entegrasyonu henüz
uygulanmamıştır.
