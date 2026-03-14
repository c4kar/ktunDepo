# Intake Agent - Yapılacak İyileştirmeler

## Priorite 1: Ders Eşleştirme Sorunları

- [x] **Fuzzy match threshold düşürüldü** (`75` → `65`)
  - Sorun: Türkçe/ASCII karakter farkı skoru düşürüyordu
  - Çözüm: Threshold ve alias tablosu eklendi

- [x] **Ders adı alias tablosu eklendi** (`PathResolver.COURSE_ALIASES`)
  - "Devre Analizi II" → `devre-analizi-2` ✓
  - "DifDenk" → `diferansiyel-denklemler` ✓
  - "Lineer Algebra" → `lineer-cebir` ✓
  - 23 alias kaydı — test: 17/17 geçti

- [x] **EEM klasör isimleri kebab-case ASCII'ye dönüştürüldü**
  - `İş_Sağlığı` → `is-sagligi`
  - `Mühendislik Mekaniği` → `muhendislik-mekanigi`
  - `DifDenk` → `diferansiyel-denklemler`
  - `Devre Analizi 2` → `devre-analizi-2`
  - Toplam: EEM-1 (7) + EEM-2 (8) = 15 klasör + alt klasörler
  - 1061 dosya korundu

## Priorite 2: Dönem Tespiti

- [x] **EEM-3, EEM-4... klasörleri otomatik oluşturulmalı**
  - Path resolver'da dönem yoksa otomatik oluşturma eklendi (`PathResolver.resolve`) ✓

- [ ] **Intake folder'dan dönem tespiti iyileştirilmeli**
  - `_intake/EEM-2/` altındaki dosyalar doğru algılanıyor
  - Ancak LLM bazen yanlış dönem tahmini yapıyor

## Priorite 3: Dosya Adı Üretimi

- [x] **Türkçe karakter dönüşümü test edildi**
  - `y-delta-aktif-guc`, `is-sagligi` gibi örneklerde başarılı ✓

- [x] **Konu slug'ları kısaltıldı** 
  - Claude promptu güncellendi (maks 3 kelime, tireli)
  - Örnek: `sinav_ac-devre-fazor-soru_tarihsiz_v1.jpg` ✓

## Priorite 4: Diğer

- [x] **Qdrant duplicate detection aktif edildi**
  - Docker container (`qdrant-test`) ayağa kaldırıldı ✓

- [ ] **Çok küçük dosyalar reddediliyor**
  - < 5KB dosyalar "Teknik hata" veriyor
  - Bu istenen davranış mı?

- [ ] **Review klasörüne taşınan dosyalar için bildirim**
  - Telegram bot entegrasyonu?

## Test Sonuçları (2026-03-10)

```
Toplam dosya: 185
Başarılı: ~150+
İnceleme: ~10
Hata/Reddedilen: ~20
```

## Notlar

- Agent temel işlevini görüyor
- En büyük sorun: "Devre Analizi II" → "Devre Analizi" eşleşmemesi
- Hızlı çözüm: alias eşleşmesi eklemek
