# ADR-001: Teknoloji Yığını

## Durum

Kabul edildi.

## Bağlam

Resmî PDF backend, frontend, veritabanı ve model kütüphanesi seçimini geliştiriciye bırakır. Python, FastAPI, PostgreSQL, scikit-learn ve Streamlit yalnız öneridir.

## Karar

- Backend: Python, Django ve Django REST Framework
- Frontend: React, TypeScript ve Vite
- Veritabanı: PostgreSQL
- Veri ve ML: pandas, scikit-learn, joblib ve SHAP
- Yerel çalışma: Docker Compose
- API belgeleme: OpenAPI

Model joblib ile `.joblib` uzantılı artefakta kaydedilecektir.

## Gerekçe

Django ve DRF kimlik doğrulama, sunucu tarafı rol kontrolü, admin işlevleri ve API geliştirme için uygundur. React/TypeScript ekran kapsamını ayrık ve test edilebilir tutar. PostgreSQL operasyonel ilişkiler ve denetim izi için uygun bir temeldir.

## Sonuçlar

Ayrık frontend/backend yapısı iki toolchain ve ek entegrasyon testi gerektirir. Bu maliyet, net sorumluluklar ve sürdürülebilirlik için kabul edilmiştir. FastAPI/Streamlit kullanmamak PDF ile çelişmez.

Gerçek ERP entegrasyonu ilk sürüm kapsamında değildir; iç veri modeli ve API gelecekteki ERP adaptörüne hazır tasarlanacaktır.
