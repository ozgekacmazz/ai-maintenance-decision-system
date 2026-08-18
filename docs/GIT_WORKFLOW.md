# Git Workflow

## 1. Durum

Bu belge, AI Destekli Bakim Karar Sistemi icin Sprint 0 asamasinda kullanilacak uygulamali bir git yonetimi ilkesini tanimlar. Bu asamada commit veya push yapilmaz; sadece repository temeli ve belgelendirme hazirlanir.

## 2. Temel ilke

- Kullanici tarafindan yapilan mevcut degisiklikler korunacak.
- Destructive git komutlari kullanilmeyecek.
- Yeni sprint kapsaminda sadece belirtilen dosyalar degistirilecek.
- Her gorev oncesi git durumu kontrol edilecek.

## 3. Onerilen dal yapisi

- `main`: ana gelistirme ve son durum dalı.
- `feature/*`: ozellik gelistirme dallari.
- `sprint/*`: sprint bazli is akisi dallari.

## 4. Is akisi

1. Repository durumunu incele.
2. Kısa gorev planini not al.
3. Yalnizca sprint 0 kapsamındaki dosyalari olustur veya degistir.
4. Git diff ve status kontrolunu yap.
5. Uygun dogrulama adimlarini calistir.
6. Commit veya push islemi kullanici onayi olmadan yapılmaz.

## 5. Diff ve kontrol

- `git status --short` ile degisikliklerin gozden gecirilmesi gerekir.
- `git diff --check` ile whitespace ve syntax seviyesinde temel sorunlar kontrol edilir.
- Git diff icinde yer alan degisiklikler, acik riskler ve gereksiz dosyalar kapsam disinda tutularak kontrol edilecektir.

## 6. Riskler

- Yanlis branch uzerinde calisma.
- Remote ve local durumunun karistirilmasi.
- Kullanici degisikliklerinin silinmesi.

## 7. Sonraki adimlar

- Sprint 1'de detayli branch stratejisi ve pull request akisi olusturulacak.
- CI onayi, review ve merge politikasi eklenerek team calisma modeline uygun hale getirilecek.
