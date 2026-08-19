# Input-domain ve birim sözleşmesi

## Kaynaklar ve sürüm

İnsan tarafından yönetilen politika `data/metadata/input_domain_policy.json`, üretilen runtime sözleşmesi `data/metadata/input_domain_contract.json` dosyasındadır. Güncel contract sürümü `ai4i-input-domain-1.0.0`, üretim politikası `legacy-ood-boundaries-1.0.0`'dır. İstatistikler yalnız training split'ten üretilir.

Generated contract doğrudan elle düzenlenmez; `ml/scripts/generate_input_domain_contract.py` ile deterministik üretilir. Runtime prepared veri SHA-256 değerini, feature sırasını, contract/policy sürümünü ve alan yapısını doğrular. Eksik veya uyuşmayan metadata fail-fast sonuçlanır; hardcoded sınır fallback'i yoktur.

## Birimler

- Web Hızlı Analiz alanları Celsius gösterir ve kabul eder.
- Dönüşüm `K = °C + 273.15` formülüdür.
- Backend API'nin `hava_sicakligi_k` ve `proses_sicakligi_k` alanları Kelvin'dir.
- Entegrasyon ve replay snapshot'ları Kelvin kullanır.
- RPM, N·m ve dakika alanları API adlarında belirtilen birimlerdedir.

Frontend contract endpoint'inden aldığı Kelvin sınırlarını Celsius'a çevirerek yardım/validation sunar. Backend authoritative doğrulamayı canonical Kelvin değerleri üzerinde tekrar yapar.

## Sınır türleri

- `physical_min/max`: mutlak fiziksel güvenlik zarfı; absolute zero ve fiziksel olarak geçersiz değerleri engeller.
- `supported_min/max`: modelin desteklenen çalışma zarfı; dışı kontrollü validation hatasıdır.
- `observed_min/max` ve percentile değerleri: training split gözlem istatistikleri; desteklenen sınır veya güvenlik garantisi değildir.

Türetilmiş sıcaklık farkı, açısal hız ve mekanik güç de aynı feature-order sözleşmesinde doğrulanır. NaN ve sonsuz değerler kabul edilmez.

## API ve snapshot

Aktif kullanıcılar input-domain contract endpoint'ini okuyabilir. Her kalıcı `TahminKaydi`, kullanılan `input_domain_contract_surumu` değerini snapshot olarak saklar. Böylece ileride metadata değişse bile kaydın hangi sözleşmeyle doğrulandığı izlenebilir.

Validation hataları standart `400` hata gövdesinde alan bazında döner. Contract veya güvenilir yapılandırma kullanılamıyorsa inference yapılmaz ve standart `503` döner.

## Sınırlama

Supported zarf içinde olmak doğru tahmin veya güvenli makine çalışması garantisi değildir. Contract yalnız giriş kalitesi ve eğitim/runtime uyum sınırıdır.
