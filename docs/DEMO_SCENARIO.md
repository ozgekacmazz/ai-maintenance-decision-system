# Sunum Senaryosu (8–12 dakika)

Demo kimlik bilgileri dokümana yazılmaz. Sunum ortamında `DEMO_ADMIN_USERNAME`,
`DEMO_ADMIN_PASSWORD`, `DEMO_USER_USERNAME` ve `DEMO_USER_PASSWORD` kullanılır.

## Sunum öncesi kontrol

- İzlenmeyen `.env` içinde dört demo credential değeri ayarlanmıştır.
- Docker servisleri healthy, migration'lar uygulanmış ve `seed_demo` başarıyla bitmiştir.
- ADMIN ve USER girişleri ayrı tarayıcı profillerinde doğrulanmıştır.
- Model artefaktları ve input-domain contract erişilebilirdir.
- Replay dataset/metadata hash'leri uyumludur; HAZIR oturum 250 gerçek öğe içerir.
- Tarayıcı cache/session temiz, zoom ve ekran çözünürlüğü uygundur.
- Akışın internet bağlantısı olmadan çalıştığı doğrulanmıştır.
- Replay uzun sürerse önceden hazırlanmış HAZIR oturumu kullanacak yedek akış hazırdır.

## Akış

1. **ADMIN giriş — `/giris`:** ADMIN environment hesabıyla giriş yapın. Rol bazlı menünün açıldığını gösterin. Giriş başarısızsa credential değerlerini ekranda göstermeden `.env` ve seed çıktısını kontrol edin.
2. **Dashboard — `/`:** Riskli tahminleri ve `Öncelik N/5` sırasını gösterin. Öncelik; teknik aciliyet, makine kritiklik seviyesi ve stok etkisini birleştiren canonical karardır. Veri yüklenmezse Tahmin Logları'na geçin.
3. **Tahmin Logları — `/admin/tahmin-loglari`:** BEKLIYOR, ONAYLANDI ve REDDEDILDI kayıtlarını; karar veren ve zamanı gösterin. TUTARSIZ normal demo durumu değildir. Filtre başarısızsa filtreleri temizleyin.
4. **Makine ve stok — `/admin/makineler`, `/admin/stok`:** Kritik makineleri, sıfır/düşük stok parçalarını gösterin. Değer değiştirmeyin; ekran yüklenmezse İş Emirleri'ndeki snapshot'ları kullanın.
5. **USER giriş — `/giris`:** Çıkış yapıp USER environment hesabıyla girin. Admin route ve API'lerinin erişilemez olduğunu gösterin. Session karışırsa ayrı tarayıcı profilini kullanın.
6. **Hızlı Analiz — `/hizli-analiz`:** Celsius değerleriyle geçerli ölçüm gönderin. Sunucu Kelvin dönüşümünü ve input-domain sözleşmesini uygular. Hazır örnek değerleri kullanın; uç değer denemeyin.
7. **Risk ve öncelik:** Sonuçta risk oranı ile `Öncelik N/5` değerini ayırın. Risk bir model çıktısıdır; kesin arıza garantisi veya calibrated probability iddiası değildir.
8. **Tahmin Detayı:** Açıklanabilirlik, önerilen aksiyon ve canonical karar bileşenlerini gösterin. SHAP alanı gelmezse karar/snapshot alanlarıyla devam edin.
9. **Onay:** BEKLIYOR bir tahmini onaylayıp iş emri oluşturun. İşlem tekrar edilirse idempotent mevcut sonucu kullanın.
10. **Red:** Başka bir BEKLIYOR tahmini gerekçeyle reddedin. Kayıt yoksa seed edilmiş REDDEDILDI örneğini gösterin; onaylanmış tahmini reddetmeyin.
11. **İş Emirleri — `/is-emirleri`:** Aksiyon, parça, stok etkisi ve SLA hedefini gösterin. Sunum sırasında durum zincirini gereksiz yere ilerletmeyin.
12. **ADMIN override ve audit:** ADMIN profiline dönüp izin verilen bir kaydın priority override/audit bilgisini gösterin. USER ile denemeyin; uygun kayıt yoksa mevcut audit örneğini salt okunur gösterin.
13. **Replay:** HAZIR replay oturumunu açın ve başlatın. Bu toplu, kontrollü bir replay'dir; gerçek zamanlı akış değildir. Süre belirsizse önceden tamamlanmış/HAZIR oturumu kullanın.
14. **Replay metrikleri:** Precision, Recall, PR-AUC ve Confusion Matrix'i gösterin. Accuracy'yi başarı KPI'ı olarak kullanmayın; sınıf dengesini ve hata türlerini açıklayın.
15. **Kapanış:** Model önerisinin canonical bakım kararı, izlenebilir audit ve insan onayıyla operasyonel iş emrine dönüştüğünü özetleyin.

Sunum sırasında demo credential, token, hash veya `.env` içeriğini ekrana vermeyin;
production veritabanında seed/reset çalıştırmayın ve model eğitimi başlatmayın.
