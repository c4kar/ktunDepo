# ktunDepo — Toplu Materyal Alım Ajanı
## Revize Uygulama Planı v2 — OpenCode için

> Bu döküman, `_intake/` klasörüne yığılan ders materyallerini otomatik olarak
> inceleyen, anlayan, eleyen, yeniden adlandıran ve doğru klasöre yerleştiren
> agentic sistemin eksiksiz uygulama planıdır.
>
> **Temel Felsefe:** Bir notun değerini Python kodu anlayamaz. Sayfa sayısı,
> dosya boyutu, metin yoğunluğu gibi sayısal metrikler bir materyalin gerçek
> katkısını ölçemez. Tek sayfalık el yazısıyla yazılmış bir sınav sorusu,
> metin katmanı olmayan bir tarama olabilir ve Python bunu göremez.
> Bu yüzden bu sistemde **LLM birincil yargıçtır.** Python yalnızca
> açıkça bozuk ve anlamsız dosyaları eliyor, geri kalanın kararını LLM'e bırakıyor.

---

## BÖLÜM 0 — SİSTEMİ ANLAMADAN BAŞLAMA

### Temel Gerçekler

**Gerçek 1 — Veri akışı tek yönlü ve geri döndürülemezdir:**
```
_intake/{ders_adı}/
        │
        ▼
  [Agent Pipeline]
        │
        ├──→ EEM-X/{Ders Adı}/          (KABUL — depoya alındı)
        ├──→ _rejected/{ders_adı}/      (RED — açıkça kalitesiz)
        └──→ _review/{ders_adı}/        (BEKLEMEDE — ajan emin olamadı)
```

**Gerçek 2 — Ajan asla silmez:**
Her dosyanın başına ne geldiği izlenebilir olmalıdır. `_rejected/` ve `_review/`
klasörleri birer arşivdir. Dosyalar orada kalır, sadece sen manuel olarak silebilirsin.

**Gerçek 3 — Her dosya için iki çıktı üretilir:**
1. Dosyanın kendisi → uygun klasöre taşınır, adı değiştirilir
2. Bir JSON raporu → karar gerekçesi, analiz sonuçları, token kullanımı

**Gerçek 4 — LLM birincil yargıçtır:**
Python yalnızca teknik olarak bozuk veya fiziksel olarak anlamsız dosyaları
eliyor (açılamayan, 0 byte, geçersiz format). Bunların dışında **her dosya
LLM tarafından görülür ve değerlendirilir.** "Sayfa sayısı az, metin az,
görsel ağırlıklı" gibi gerekçeler Python için red kriteri değildir — çünkü
bu tür dosyalar en değerli materyaller olabilir (el yazısı sınav sorusu,
tek sayfalık formül kağıdı, taranmış ders notu).

---

## BÖLÜM 1 — KLASÖR SÖZLEŞMESİ

Ajan başlamadan önce aşağıdaki klasörlerin var olup olmadığını kontrol eder,
yoksa oluşturur. `EEM-X/` klasörlerine **asla dokunmaz** (sadece yeni dosya ekler).

```
ktunDepo/
│
├── _intake/                          ← KULLANICI BURAYA YIĞIYOR
│   └── {ders_adı}/                   ← Örn: "Fizik I", "Lineer Cebir"
│       ├── herhangi_bir_dosya.pdf
│       ├── WhatsApp Image 2022.jpg
│       ├── tarama001.pdf
│       └── ...                       ← Düzensiz, orijinal dosyalar
│
├── _rejected/                        ← Red edilen dosyalar (kalıcı arşiv)
│   └── {ders_adı}/
│       ├── bozuk_dosya.pdf
│       └── rejection_report.json
│
├── _review/                          ← Ajan emin olamadı, admin kararı lazım
│   └── {ders_adı}/
│       ├── belirsiz_materyal.pdf
│       └── review_note.json          ← Ajan neden kararsız kaldı?
│
├── _reports/                         ← Her çalışmanın kayıtları
│   ├── intake_run_20240115_143022/
│   │   ├── summary.json              ← Genel özet
│   │   ├── fizik_vize_2022.json      ← Dosya başına detaylı rapor
│   │   └── ocr_queue.json            ← OCR bekleyen dosyalar listesi
│   └── ...
│
├── EEM-1/
│   ├── Fizik/
│   │   ├── Fizik I/
│   │   │   ├── LMS/
│   │   │   │   └── [yeni LMS sunumları buraya]
│   │   │   └── [diğer yeni materyaller buraya]
│   │   └── Fizik II/
│   ├── Lineer Cebir/
│   └── ...
├── EEM-2/
│   └── ...
└── README.md
```

---

## BÖLÜM 2 — PIPELINE MİMARİSİ

Her dosya için pipeline şu sırayla çalışır. Bir adım başarısız olduğunda
dosya `_review/` klasörüne alınır, hata loglanır ve **sonraki dosyaya geçilir.**
Pipeline asla tamamen durmamalıdır.

```
┌──────────────────────────────────────────────────────────────────┐
│  ADIM 1 — TEKNİK TARAMA                                         │
│  Dosyayı aç, temel profili çıkar. 0 token.                      │
│  Sadece fiziksel olarak bozuk dosyaları burada ele.             │
└─────────────────────────────┬────────────────────────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │  Dosya açılabiliyor mu?        │
              │  Format geçerli mi?            │
              └───────┬───────────────┬────────┘
                  EVET│               │HAYIR
                      │               ▼
                      │         _rejected/ + rapor
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  ADIM 2 — İÇERİK HAZIRLAMA                                      │
│  LLM'e gönderilecek içeriği hazırla.                            │
│  Metin varsa: ilk sayfayı çıkar                                 │
│  Metin yoksa: ilk sayfayı görüntüye çevir (vision için)         │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  ADIM 3 — LLM ANALİZİ (Birincil Karar Noktası)                 │
│  Claude dosyayı görür/okur ve tam analiz yapar.                 │
│  Kabul / Red / Review kararını LLM verir.                       │
└─────────────────────────────┬────────────────────────────────────┘
                              │
         ┌────────────────────┼──────────────────────┐
      RED│               REVIEW│                KABUL│
         ▼                    ▼                      ▼
   _rejected/           _review/              ADIM 4'e geç
   + rapor              + rapor
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  ADIM 4 — DUPLICATE TESPİTİ                                     │
│  Vektör DB'de aynı/benzer materyal var mı?                      │
└─────────────────────────────┬────────────────────────────────────┘
                              │
         ┌────────────────────┼──────────────────────┐
  DUPLICATE│            BENZER│                YOK│
           ▼                  ▼                   ▼
      _rejected/          _review/           ADIM 5'e geç
      + rapor              + rapor
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  ADIM 5 — DOSYA ADI OLUŞTURMA                                   │
│  Standart formatta yeni isim üret (LLM analiz sonucundan)       │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  ADIM 6 — HEDEF YOL TESPİTİ                                     │
│  EEM-X/{Ders}/{alt_klasör}/ yolunu belirle                      │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  ADIM 7 — RAPOR YAZIMI                                          │
│  Tüm kararları, gerekçeleri, token kullanımını kaydet           │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  ADIM 8 — DOSYAYI TAŞI                                          │
│  copy2 + remove ile güvenli taşıma                              │
│  OCR gerekliyse kuyruğa ekle                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## BÖLÜM 3 — ADIM 1: TEKNİK TARAMA

**0 token. Sadece Python.**

Bu adımın tek görevi dosyanın fiziksel olarak işlenebilir olup olmadığını
anlamaktır. İçerik kalitesi hakkında hiçbir karar verilmez.

```python
def scan_file(file_path: str) -> dict:
    profile = {
        "filename_original": os.path.basename(file_path),
        "extension": Path(file_path).suffix.lower(),
        "size_kb": os.path.getsize(file_path) / 1024,
        "size_mb": os.path.getsize(file_path) / (1024 * 1024),
    }

    # Uzantı kontrolü
    SUPPORTED = {".pdf", ".pptx", ".docx", ".jpg", ".jpeg", ".png", ".mp4", ".mkv"}
    if profile["extension"] not in SUPPORTED:
        raise UnsupportedFormatError(f"Desteklenmeyen format: {profile['extension']}")

    # Boyut kontrolü — sadece gerçekten boş dosyalar
    if profile["size_kb"] < 5:
        raise EmptyFileError("Dosya 5KB altında, muhtemelen boş veya bozuk")

    # PDF'e özgü bilgiler
    if profile["extension"] == ".pdf":
        try:
            reader = PdfReader(file_path)
            profile["page_count"] = len(reader.pages)

            # Metin katmanı var mı?
            sample_text = ""
            for page in reader.pages[:3]:  # İlk 3 sayfayı dene
                sample_text += page.extract_text() or ""
            profile["has_text_layer"] = len(sample_text.strip()) > 50
            profile["first_page_text"] = reader.pages[0].extract_text() or ""

            # Görüntü ağırlıklı mı?
            first_page = reader.pages[0]
            image_count = len(first_page.images) if hasattr(first_page, 'images') else 0
            profile["first_page_has_images"] = image_count > 0

        except Exception as e:
            raise CorruptedFileError(f"PDF açılamadı: {e}")

    # PPTX/DOCX için temel bilgi
    elif profile["extension"] in {".pptx", ".docx"}:
        profile["has_text_layer"] = True  # Office formatları zaten metin içerir
        profile["page_count"] = None       # Slayt/sayfa sayısı ayrıca çekilir

    # Görüntü dosyaları
    elif profile["extension"] in {".jpg", ".jpeg", ".png"}:
        profile["has_text_layer"] = False  # Görüntü = OCR gerekli
        profile["page_count"] = 1

    return profile
```

**Bu adımda red edilecekler (tek istisna):**

| Durum | Karar | Gerekçe |
|---|---|---|
| Desteklenmeyen uzantı (.exe, .zip, .rar) | RED | Format anlamsız |
| Dosya boyutu < 5 KB | RED | Fiziksel olarak boş |
| PDF açılamıyor (corrupt) | RED | Teknik olarak işlenemez |

**Bu adımda RED edilmeyecekler (önceki versiyonda hataydı):**

| Durum | Eski (Yanlış) | Yeni (Doğru) |
|---|---|---|
| Sayfa sayısı < 2 | RED | LLM'e gönder |
| Metin katmanı yok | RED adayı | LLM'e gönder (vision ile) |
| Küçük dosya boyutu (>5KB) | RED | LLM'e gönder |
| Düşük metin yoğunluğu | RED adayı | LLM'e gönder |

> ⚠️ **Neden bu değişim kritik?**
> Tek sayfalık el yazısıyla yazılmış bir sınav sorusu:
> - Sayfa sayısı: 1 → eski sistemde RED
> - Metin katmanı: YOK → eski sistemde RED adayı
> - Metin yoğunluğu: 0 → eski sistemde RED
>
> Oysa bu dosya, depoda olmayan 2019 final soruları olabilir.
> **Python bu kararı veremez. LLM verebilir.**

---

## BÖLÜM 4 — ADIM 2: İÇERİK HAZIRLAMA

LLM'e gönderilecek içeriği hazırla. Bu adım dosyanın türüne göre farklı çalışır.

### Senaryo A — Metin katmanı olan PDF / PPTX / DOCX

```python
def prepare_text_content(file_path: str, profile: dict) -> dict:
    if profile["extension"] == ".pdf" and profile["has_text_layer"]:
        # İlk 2 sayfanın metnini al (yeterli bağlam için)
        reader = PdfReader(file_path)
        text = ""
        for i, page in enumerate(reader.pages[:2]):
            text += f"\n--- SAYFA {i+1} ---\n"
            text += page.extract_text() or ""

        return {
            "mode": "text",
            "content": text[:3000],  # Max 3000 karakter — LLM için yeterli
            "pages_sampled": min(2, profile["page_count"])
        }
```

### Senaryo B — Metin katmanı OLMAYAN PDF (taranmış, el yazısı, fotoğraf)

Bu senaryo önceki versiyonda eksikti. Metin olmayan dosyalar en değerli
materyaller olabilir. Claude'un vision kapasitesini kullan.

```python
def prepare_vision_content(file_path: str, profile: dict) -> dict:
    # İlk sayfayı yüksek çözünürlüklü görüntüye çevir
    from pdf2image import convert_from_path
    from PIL import Image
    import base64, io

    pages = convert_from_path(
        file_path,
        first_page=1,
        last_page=min(2, profile.get("page_count", 1)),  # Max 2 sayfa
        dpi=200  # 200 DPI: okunabilir ama çok büyük değil
    )

    images_b64 = []
    for page_img in pages:
        # Görüntüyü base64'e çevir
        buffer = io.BytesIO()
        page_img.save(buffer, format="JPEG", quality=85)
        b64 = base64.b64encode(buffer.getvalue()).decode()
        images_b64.append(b64)

    return {
        "mode": "vision",
        "images": images_b64,
        "page_count": profile.get("page_count", 1),
        "note": "Metin katmanı yok, görsel olarak analiz ediliyor"
    }
```

### Senaryo C — Görüntü dosyası (JPG, PNG)

```python
def prepare_image_content(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    ext = Path(file_path).suffix.lower().replace(".", "")
    media_type = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    return {
        "mode": "vision",
        "images": [b64],
        "media_type": media_type,
        "note": "Görüntü dosyası, vision ile analiz ediliyor"
    }
```

### Senaryo D — Video dosyası (MP4, MKV)

Video içeriğini analiz edemeyiz. Ama dosyanın var olması ve adının anlamlı
olması kabul için yeterli olabilir.

```python
def prepare_video_content(file_path: str, profile: dict) -> dict:
    return {
        "mode": "metadata_only",
        "filename": profile["filename_original"],
        "size_mb": profile["size_mb"],
        "note": "Video dosyası — içerik analizi yapılamaz, sadece metadata ile değerlendir"
    }
```

---

## BÖLÜM 5 — ADIM 3: LLM ANALİZİ (BİRİNCİL KARAR NOKTASI)

Bu adım sistemin kalbidir. **Tek LLM çağrısı** burada yapılır.
LLM hem dosyanın ne olduğunu anlar hem de kabul/red kararını verir.

### System Prompt

```
Sen ktunDepo'nun baş editörüsün. Konya Teknik Üniversitesi Mühendislik
Fakültesi'nin dijital ders materyali deposunu yönetiyorsun.

Görevin: Sana gönderilen materyali inceleyip depoya alınmaya değer olup
olmadığına karar vermek.

DEPO HAKKINDA:
- Dönem bazlı organize: EEM-1, EEM-2, EEM-3...
- Her dönemde: Fizik I/II, Matematik, Lineer Cebir, Kimya, Devre Analizi,
  Elektronik, Lojik Devreler, Mühendislik Mekaniği, DifDenk, vb.
- Hedef kitle: Mühendislik öğrencileri
- Değer verilen materyaller: Sınav soruları (çözümlü veya çözümsüz),
  ders notları (el yazısı dahil), formül özetleri, LMS sunumları,
  laboratuvar föyleri

KRİTİK KARAR KURALLARI:
1. Tek sayfalık bir materyal bile değerli olabilir. Sayfa sayısına göre
   karar verme. El yazısıyla yazılmış tek sayfa sınav sorusu paha biçilmezdir.

2. Metin okunamıyor olsa bile (taranmış, el yazısı, düşük çözünürlük)
   içerik anlaşılabiliyorsa kabul et. OCR sonradan yapılacak.

3. Dil Türkçe veya İngilizce olabilir. İkisi de kabul edilir.

4. Red kararı için güçlü gerekçe lazım:
   - Tamamen alakasız içerik (reklam, kişisel fotoğraf, boş sayfa)
   - Başka üniversiteye ait ve hiç transfer değeri olmayan materyal
   - Teknik olarak okunamaz düzeyde bozuk görüntü

5. Emin olamıyorsan REVIEW seç. Hatalı red, hatalı kabulden daha kötüdür.

SADECE JSON döndür. Hiçbir açıklama ekleme.
```

### User Prompt (metin modu)

```python
user_prompt = f"""
Dosya Bilgisi:
- Orijinal adı: {profile['filename_original']}
- Boyut: {profile['size_kb']:.0f} KB
- Sayfa sayısı: {profile.get('page_count', 'bilinmiyor')}
- Format: {profile['extension']}

İlk 2 Sayfanın İçeriği:
{content['content']}

Lütfen şunları belirle ve SADECE JSON döndür:

{{
  "material_type": "ders_notu | lms_sunumu | sinav_sorusu | sinav_cozumu | laboratuvar_foyu | ozet | video_ders | diger",
  "course_name": "Ders adı (Türkçe, klasördeki gibi)",
  "semester_guess": "EEM-1 | EEM-2 | EEM-3 | belirsiz",
  "topics": ["konu1", "konu2"],
  "year_guess": "2022 veya null",
  "has_solutions": true/false,
  "language": "tr | en | mixed",
  "needs_ocr": true/false,
  "decision": "ACCEPTED | REJECTED | REVIEW",
  "decision_reason": "Kararın 1-2 cümle Türkçe gerekçesi",
  "confidence": 0.0-1.0,
  "suggested_filename_hint": "kısa ve açıklayıcı dosya adı ipucu"
}}
"""
```

### User Prompt (vision modu — metin katmanı olmayan dosyalar)

```python
# Vision modunda görüntüler messages array'ine eklenir
messages = [
    {
        "role": "user",
        "content": [
            # Her sayfa görüntüsü için
            *[{
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_b64
                }
            } for img_b64 in content["images"]],
            {
                "type": "text",
                "text": f"""
Bu görüntüler bir ders materyalinin ilk sayfalarıdır (metin katmanı yok,
taranmış veya fotoğraflanmış).

Dosya bilgisi:
- Orijinal adı: {profile['filename_original']}
- Boyut: {profile['size_kb']:.0f} KB
- Toplam sayfa: {profile.get('page_count', 'bilinmiyor')}

Görüntüye bakarak şunları belirle ve SADECE JSON döndür:

{{
  "material_type": "ders_notu | lms_sunumu | sinav_sorusu | sinav_cozumu | laboratuvar_foyu | ozet | video_ders | diger",
  "course_name": "Ders adı",
  "semester_guess": "EEM-1 | EEM-2 | belirsiz",
  "topics": ["konu1", "konu2"],
  "year_guess": "2022 veya null",
  "has_solutions": true/false,
  "language": "tr | en | mixed",
  "needs_ocr": true,
  "legibility": "good | medium | poor",
  "decision": "ACCEPTED | REJECTED | REVIEW",
  "decision_reason": "Gerekçe",
  "confidence": 0.0-1.0,
  "suggested_filename_hint": "dosya adı ipucu"
}}
"""
            }
        ]
    }
]
```

### API Çağrısı

```python
def call_llm(profile: dict, content: dict) -> dict:
    client = anthropic.Anthropic()

    if content["mode"] == "text":
        response = client.messages.create(
            model="claude-sonnet-4-5",   # Vision + metin her ikisi de destekler
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_text_prompt(profile, content)}]
        )
    elif content["mode"] == "vision":
        response = client.messages.create(
            model="claude-sonnet-4-5",   # Vision için Sonnet yeterli
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=build_vision_messages(profile, content)
        )
    elif content["mode"] == "metadata_only":
        # Video dosyaları için minimal çağrı
        response = client.messages.create(
            model="claude-haiku-4-5",    # Video için sadece metadata → Haiku yeterli
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_video_prompt(profile)}]
        )

    # JSON parse
    raw = response.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    result = json.loads(raw)
    result["_tokens_used"] = {
        "input": response.usage.input_tokens,
        "output": response.usage.output_tokens
    }
    return result
```

### LLM Kararlarının Yorumlanması

```python
def interpret_llm_decision(llm_result: dict) -> str:
    decision = llm_result.get("decision", "REVIEW")
    confidence = llm_result.get("confidence", 0.5)

    # LLM REVIEW dedi ama yüksek güvenle → yine de REVIEW (admin baksın)
    # LLM ACCEPTED dedi ama düşük güvenle → REVIEW'a düşür
    if decision == "ACCEPTED" and confidence < 0.6:
        return "REVIEW"

    # LLM RED dedi ama düşük güvenle → REVIEW'a yükselt (hatalı red önleme)
    if decision == "REJECTED" and confidence < 0.75:
        return "REVIEW"

    return decision
```

> **Neden hatalı RED → REVIEW'a alıyoruz?**
> Hatalı kabul: Depoya gereksiz bir dosya girer → az zararlı
> Hatalı red: Değerli bir materyal kaybolur → çok zararlı
> Bu yüzden şüpheli durumlarda her zaman REVIEW seç.

---

## BÖLÜM 6 — ADIM 4: DUPLICATE TESPİTİ

LLM ACCEPTED derse vektör veritabanında aynı veya çok benzer bir
materyalin zaten mevcut olup olmadığını kontrol et.

### Embedding Stratejisi

```python
def get_content_for_embedding(file_path: str, profile: dict) -> str:
    """
    Embedding için içerik hazırla.
    Tüm belgeyi değil, temsili bir bölümü embed et.
    """
    if profile.get("has_text_layer") and profile["extension"] == ".pdf":
        reader = PdfReader(file_path)
        # İlk 3 sayfanın metni duplicate tespiti için yeterli
        text = ""
        for page in reader.pages[:3]:
            text += page.extract_text() or ""
        return text[:2000]

    elif not profile.get("has_text_layer"):
        # Metin yok — dosya adı + LLM analiz sonucunu embed et
        # (bu durumda duplicate tespiti daha zayıf olacak, kabul edilebilir)
        return f"{profile['filename_original']} {profile.get('llm_topics', '')}"

    return profile["filename_original"]
```

### Vektör Arama

```python
def check_duplicate(
    file_path: str,
    profile: dict,
    llm_result: dict,
    qdrant_client
) -> dict:

    content = get_content_for_embedding(file_path, profile)
    if not content.strip():
        return {"status": "unknown", "reason": "Embedding için içerik yok"}

    # Lokal model ile embed et
    embedding = embedding_model.encode(content).tolist()

    semester = llm_result.get("semester_guess", "belirsiz")
    course   = llm_result.get("course_name", "")

    # Filtreli arama — sadece aynı dönem ve ders içinde
    filters = []
    if semester != "belirsiz":
        filters.append(FieldCondition(key="semester", match=MatchValue(value=semester)))
    if course:
        filters.append(FieldCondition(key="course", match=MatchValue(value=course)))

    results = qdrant_client.search(
        collection_name="ktundepo_materials",
        query_vector=embedding,
        query_filter=Filter(must=filters) if filters else None,
        limit=3,
        score_threshold=0.70
    )

    if not results:
        return {"status": "unique", "similar": []}

    top = results[0]

    if top.score > 0.93:
        return {
            "status": "duplicate",
            "similar": [{"file": top.payload.get("filename"), "score": round(top.score, 3)}],
            "recommendation": "REJECTED"
        }
    elif top.score > 0.78:
        return {
            "status": "similar",
            "similar": [{"file": top.payload.get("filename"), "score": round(top.score, 3)}],
            "recommendation": "REVIEW"
        }
    else:
        return {"status": "unique", "similar": []}
```

### Duplicate Kararları

| Similarity | Durum | Karar |
|---|---|---|
| > 0.93 | Kesin duplicate | RED — aynı materyal zaten depoda |
| 0.78 – 0.93 | Muhtemelen benzer | REVIEW — admin baksın, belki farklı yıl |
| < 0.78 | Özgün | KABUL et (pipeline devam) |

> **Neden 0.93 eşiği?** 0.90'da farklı yılların aynı sınav soruları
> birbirine benzer çıkabilir. 0.93 daha güvenli bir eşiktir.
> Benzer ama farklı yıl materyalleri depoda değerlidir.

---

## BÖLÜM 7 — ADIM 5: DOSYA ADI OLUŞTURMA

LLM analizinden gelen bilgilerle standart bir dosya adı üret.

### Format

```
{tür}_{konu_slug}_{yıl}_v{n}.{ext}

Örnekler:
sinav_vektorler-moment_2022_v1.pdf
lms_kinematik_2023_v1.pdf
not_diferansiyel-denklemler_2021_v1.pdf
cozum_devre-analizi_2020_v1.pdf
lab_rc-devresi_2023_v1.pdf
ozet_lineer-cebir_2022_v1.pdf
```

### Üretim Kodu

```python
TYPE_PREFIX = {
    "ders_notu":        "not",
    "lms_sunumu":       "lms",
    "sinav_sorusu":     "sinav",
    "sinav_cozumu":     "cozum",
    "laboratuvar_foyu": "lab",
    "ozet":             "ozet",
    "video_ders":       "video",
    "diger":            "materyal"
}

TURKISH_CHARS = str.maketrans("ıİğĞşŞçÇöÖüÜ", "iiggssccoouuu")

def slugify(text: str) -> str:
    text = text.lower().translate(TURKISH_CHARS)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:40]  # Çok uzun olmasın

def generate_filename(llm_result: dict, extension: str, target_dir: str) -> str:
    prefix   = TYPE_PREFIX.get(llm_result.get("material_type", "diger"), "materyal")
    topics   = llm_result.get("topics", [])
    hint     = llm_result.get("suggested_filename_hint", "")
    year     = llm_result.get("year_guess") or "tarihsiz"

    # Konu slug'ı: LLM'in önerdiği hint varsa onu kullan, yoksa topics'ten üret
    if hint:
        topic_slug = slugify(hint)[:30]
    elif topics:
        topic_slug = slugify("-".join(topics[:2]))
    else:
        topic_slug = "genel"

    base = f"{prefix}_{topic_slug}_{year}"

    # Versiyon çakışması kontrolü
    version = 1
    while True:
        candidate = f"{base}_v{version}{extension}"
        if not os.path.exists(os.path.join(target_dir, candidate)):
            return candidate
        version += 1
```

---

## BÖLÜM 8 — ADIM 6: HEDEF YOL TESPİTİ

```python
def resolve_target_path(
    repo_root: str,
    llm_result: dict,
    intake_folder: str,
    new_filename: str
) -> str:

    # 1. Dönem tespiti — önce intake klasörü adından, sonra LLM tahmininden
    semester = extract_semester_from_intake_path(intake_folder)
    if not semester:
        semester = llm_result.get("semester_guess", "")
    if not semester or semester == "belirsiz":
        raise SemesterUnknownError("Dönem tespit edilemedi → REVIEW'a al")

    # 2. Ders adı — LLM'den, fuzzy match ile doğrula
    course_guess = llm_result.get("course_name", "")
    available    = list_available_courses(repo_root, semester)
    course       = fuzzy_match_course(course_guess, available)

    # 3. Alt klasör — LMS sunumları LMS/ altına, diğerleri direkt ders klasörüne
    material_type = llm_result.get("material_type", "diger")
    if material_type == "lms_sunumu":
        target_dir = os.path.join(repo_root, semester, course, "LMS")
    else:
        target_dir = os.path.join(repo_root, semester, course)

    os.makedirs(target_dir, exist_ok=True)

    target_path = os.path.join(target_dir, new_filename)

    # 4. Üzerine yazma koruması
    if os.path.exists(target_path):
        raise FileExistsError(f"Hedef zaten var: {target_path}")

    return target_path


def fuzzy_match_course(guess: str, available: list) -> str:
    from rapidfuzz import process
    if not available:
        raise NoCourseFoundError("Bu dönemde hiç ders klasörü yok")

    match, score, _ = process.extractOne(guess, available)
    if score >= 75:
        return match
    else:
        raise CourseMatchError(
            f"'{guess}' eşleştirilemedi (en yakın: '{match}', skor: {score}) → REVIEW'a al"
        )
```

---

## BÖLÜM 9 — ADIM 7: RAPOR YAZIMI

Her dosya için kapsamlı bir JSON raporu oluştur ve `_reports/{run_id}/` klasörüne kaydet.

```json
{
  "run_id": "intake_run_20240115_143022",
  "file": {
    "original_name": "WhatsApp Image 2022-06-14.jpg",
    "new_name": "sinav_vektorler-moment_2022_v1.pdf",
    "original_path": "_intake/Fizik I/WhatsApp Image 2022-06-14.jpg",
    "final_path": "EEM-1/Fizik/Fizik I/sinav_vektorler-moment_2022_v1.pdf",
    "size_kb": 312,
    "page_count": 1,
    "has_text_layer": false,
    "analysis_mode": "vision"
  },
  "llm_analysis": {
    "material_type": "sinav_sorusu",
    "course_name": "Fizik I",
    "semester_guess": "EEM-1",
    "topics": ["Vektörler", "Moment"],
    "year_guess": "2022",
    "has_solutions": false,
    "language": "tr",
    "needs_ocr": true,
    "legibility": "good",
    "decision": "ACCEPTED",
    "decision_reason": "2022 yılına ait Fizik I vize sınavı soruları. El yazısıyla yazılmış, tek sayfa ama net okunuyor. Bu konudan depoda sınav sorusu yok.",
    "confidence": 0.88
  },
  "duplicate_check": {
    "status": "unique",
    "similar": []
  },
  "final_decision": "ACCEPTED",
  "token_usage": {
    "input_tokens": 1840,
    "output_tokens": 187,
    "model": "claude-sonnet-4-5"
  },
  "processed_at": "2024-01-15T14:30:22Z",
  "needs_ocr": true
}
```

---

## BÖLÜM 10 — ADIM 8: DOSYAYI TAŞI

```python
def execute_file_move(
    source_path: str,
    final_decision: str,
    target_path: str,
    rejected_base: str,
    review_base: str,
    course: str,
    original_name: str,
    review_note: dict = None
):
    if final_decision == "ACCEPTED":
        # Güvenli taşıma: önce kopyala, sonra kaynağı sil
        shutil.copy2(source_path, target_path)
        if os.path.exists(target_path):  # Kopyalama başarılı mı?
            os.remove(source_path)
        else:
            raise FileMoveError("Kopyalama başarısız, kaynak dosya korunuyor")

    elif final_decision == "REJECTED":
        dest_dir = os.path.join(rejected_base, course)
        os.makedirs(dest_dir, exist_ok=True)
        shutil.move(source_path, os.path.join(dest_dir, original_name))

    elif final_decision == "REVIEW":
        dest_dir = os.path.join(review_base, course)
        os.makedirs(dest_dir, exist_ok=True)
        shutil.move(source_path, os.path.join(dest_dir, original_name))
        # Review notunu yanına kaydet
        if review_note:
            note_path = os.path.join(dest_dir, f"{original_name}_review_note.json")
            with open(note_path, "w", encoding="utf-8") as f:
                json.dump(review_note, f, ensure_ascii=False, indent=2)
```

---

## BÖLÜM 11 — ÖZEL DURUM: _review/ KLASÖRLERİ YÖNETİMİ

`_review/` klasörü zamanla dolabilir. Admin için bir inceleme komutu:

```bash
# Review bekleyen dosyaları listele ve kararını sor
python intake_agent.py --review-pending
```

Bu komut çalıştığında:
1. `_review/` altındaki tüm dosyaları ve yanlarındaki `review_note.json`'ı listeler
2. Her biri için: KABUL / RED / ATLA seçeneği sunar
3. Admin kararına göre dosyaları uygun yere taşır

---

## BÖLÜM 12 — OCR PIPELINE (KABUL EDİLEN AMA METİNSİZ DOSYALAR)

Kabul edilen ve `needs_ocr: true` olan dosyalar ayrı bir kuyrukta bekler.
OCR işlemi alımdan ayrı çalıştırılır çünkü zaman alır ve her alım sonrası
zorunlu değildir.

```json
// _reports/intake_run_{id}/ocr_queue.json
[
  {
    "file": "EEM-1/Fizik/Fizik I/sinav_vektorler_2022_v1.pdf",
    "material_type": "sinav_sorusu",
    "course": "Fizik I",
    "legibility": "good"
  }
]
```

```bash
# OCR kuyruğunu işle
python intake_agent.py --ocr-only --queue "_reports/intake_run_20240115/ocr_queue.json"
```

OCR pipeline adımları:
1. Dosyayı Docling ile işle (tablo + formül desteği)
2. Ham metni çıkar
3. `agent/prompts/markdown_format_prompt.txt` ile Claude'a gönder
4. Sonucu `{dosya_adı}_formatted.md` olarak aynı klasöre kaydet
5. Orijinal PDF'e dokunma — Markdown ek dosya olarak eklenir

---

## BÖLÜM 13 — ANA ORKESTRATÖR

```python
def run_bulk_intake(intake_folder: str, repo_root: str, dry_run: bool = False):
    run_id  = f"intake_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    files   = list_all_files(intake_folder)
    course  = extract_course_from_path(intake_folder)

    os.makedirs(f"_reports/{run_id}", exist_ok=True)

    results   = []
    ocr_queue = []
    token_total = {"input": 0, "output": 0}

    log.info(f"[{run_id}] Başladı. {len(files)} dosya. Dry-run: {dry_run}")

    for i, file_path in enumerate(files):
        log.info(f"[{i+1}/{len(files)}] {os.path.basename(file_path)}")
        result = {"file": os.path.basename(file_path), "decision": None}

        try:
            # ADIM 1 — Teknik tarama
            profile = scan_file(file_path)

        except (UnsupportedFormatError, EmptyFileError, CorruptedFileError) as e:
            log.warning(f"Teknik red: {e}")
            result["decision"] = "REJECTED"
            result["reason"] = str(e)
            if not dry_run:
                move_to_rejected(file_path, course)
            results.append(result)
            continue

        try:
            # ADIM 2 — İçerik hazırlama
            content = prepare_content(file_path, profile)

            # ADIM 3 — LLM analizi
            llm_result   = call_llm(profile, content)
            final_decision = interpret_llm_decision(llm_result)

            token_total["input"]  += llm_result["_tokens_used"]["input"]
            token_total["output"] += llm_result["_tokens_used"]["output"]

            if final_decision in ("REJECTED", "REVIEW"):
                result["decision"] = final_decision
                result["llm"] = llm_result
                if not dry_run:
                    move_file_to_destination(file_path, final_decision, ...)
                results.append(result)
                continue

            # ADIM 4 — Duplicate tespiti
            dup = check_duplicate(file_path, profile, llm_result, qdrant)
            if dup["status"] in ("duplicate", "similar"):
                final_decision = dup["recommendation"]
                result["decision"] = final_decision
                result["duplicate"] = dup
                if not dry_run:
                    move_file_to_destination(file_path, final_decision, ...)
                results.append(result)
                continue

            # ADIM 5 — Dosya adı
            target_dir   = get_temp_target_dir(repo_root, llm_result)
            new_filename = generate_filename(llm_result, profile["extension"], target_dir)

            # ADIM 6 — Hedef yol
            target_path = resolve_target_path(repo_root, llm_result,
                                              intake_folder, new_filename)

            # ADIM 7 — Rapor
            report = build_full_report(run_id, profile, llm_result, dup,
                                       new_filename, target_path, "ACCEPTED")
            save_report(report, run_id)

            # ADIM 8 — Taşı
            if not dry_run:
                execute_file_move(file_path, "ACCEPTED", target_path, ...)
                embed_and_store(file_path, profile, llm_result, qdrant)
                if llm_result.get("needs_ocr"):
                    ocr_queue.append({"file": target_path, **llm_result})

            result["decision"] = "ACCEPTED"
            result["target"]   = target_path
            results.append(result)

        except Exception as e:
            log.error(f"Beklenmeyen hata [{os.path.basename(file_path)}]: {e}")
            result["decision"] = "REVIEW"
            result["error"]    = str(e)
            if not dry_run:
                move_to_review(file_path, course, {"error": str(e)})
            results.append(result)

    # Özet rapor
    summary = build_summary(run_id, results, token_total, ocr_queue)
    save_summary(summary, run_id)
    if ocr_queue and not dry_run:
        save_ocr_queue(ocr_queue, run_id)

    print_final_table(results, token_total, dry_run)
```

---

## BÖLÜM 14 — TOKEN VE MALİYET YÖNETİMİ

### Her Dosya İçin Tahmini Token Maliyeti

| Dosya Türü | Analiz Modu | Input Token | Output Token | Toplam |
|---|---|---|---|---|
| Metin PDF (≥1 sayfa) | text | ~600-900 | ~150-200 | ~800 |
| Taranmış PDF / JPG | vision | ~1500-3000 | ~150-200 | ~1800 |
| Video dosyası | metadata | ~300 | ~100 | ~400 |
| Teknik red (bozuk) | hiç | 0 | 0 | 0 |

**50 dosyalık tipik bir klasör tahmini:** ~50.000 token → ~$0.15 (Sonnet fiyatıyla)

### Model Seçimi Stratejisi

```python
def select_model(content_mode: str, file_size_kb: float) -> str:
    if content_mode == "metadata_only":
        return "claude-haiku-4-5"        # Video → en ucuz model yeterli

    if content_mode == "vision":
        return "claude-sonnet-4-5"       # Vision mutlaka Sonnet

    if content_mode == "text":
        if file_size_kb < 500:
            return "claude-haiku-4-5"    # Küçük metin PDF → Haiku yeterli
        else:
            return "claude-sonnet-4-5"   # Büyük / karmaşık → Sonnet
```

---

## BÖLÜM 15 — CLI KULLANIM ARAYÜZÜ

```bash
# Temel kullanım
python intake_agent.py --intake "_intake/Fizik I" --semester "EEM-1"

# Dry-run — dosya taşımaz, sadece ne olacağını gösterir
python intake_agent.py --intake "_intake/Lineer Cebir" --semester "EEM-1" --dry-run

# Tek dosya testi
python intake_agent.py --test-file "test.pdf" --course "Devre Analizi" --semester "EEM-2"

# Review bekleyen dosyaları işle
python intake_agent.py --review-pending

# OCR kuyruğunu işle
python intake_agent.py --ocr-only --queue "_reports/intake_run_20240115/ocr_queue.json"

# Tüm _intake/ klasörünü tara (birden fazla ders)
python intake_agent.py --intake "_intake/" --auto-detect-courses
```

> **`--dry-run` zorunlu kullanım kuralı:**
> İlk kez çalıştırırken MUTLAKA `--dry-run` kullan.
> Raporu kontrol et, kararların mantıklı olduğunu gör.
> Sonra `--dry-run` olmadan tekrar çalıştır.

---

## BÖLÜM 16 — KURULUM

```bash
pip install \
  anthropic \
  docling \
  pypdf2 \
  pdfplumber \
  pdf2image \
  Pillow \
  qdrant-client \
  sentence-transformers \
  rapidfuzz \
  loguru \
  typer \
  python-dotenv \
  rich               # Terminalde güzel tablo çıktısı için

# pdf2image için sistem bağımlılığı
# Ubuntu/Debian: sudo apt install poppler-utils
# macOS: brew install poppler

# Embedding modeli (ilk çalıştırmada ~1.2GB indirir)
python -c "from sentence_transformers import SentenceTransformer; \
           SentenceTransformer('intfloat/multilingual-e5-large')"
```

**.env:**
```env
ANTHROPIC_API_KEY=sk-ant-...
QDRANT_HOST=localhost
QDRANT_PORT=6333
REPO_ROOT=/path/to/ktunDepo
```

---

## BÖLÜM 17 — BAŞARININ TANIMI

Sistem doğru çalışıyorsa alım sonunda şunu görürsün:

```
┌─────────────────────────────────────────────────────┐
│  intake_run_20240115_143022  │  Fizik I  │  18 dosya │
├──────────────┬───────────────────────────────────────┤
│ KABUL        │ 13 dosya  (%72)                       │
│ RED          │  3 dosya  (%17) — bozuk/alakasız      │
│ REVIEW       │  2 dosya  (%11) — admin baksın        │
│ OCR kuyruğu  │  4 dosya  (kabul edildi, OCR bekliyor)│
├──────────────┴───────────────────────────────────────┤
│ Token: 21.840 input / 3.210 output                   │
│ Süre: 4 dakika 12 saniye                             │
└─────────────────────────────────────────────────────┘
```

Ve depoda:
- `_intake/Fizik I/` → boş
- `_rejected/Fizik I/` → 3 dosya + gerekçeleri
- `_review/Fizik I/` → 2 dosya + neden kararsız kalındığı
- `EEM-1/Fizik/Fizik I/` → 13 yeni dosya, standart isimlendirilmiş
- `_reports/intake_run_.../` → her şeyin kaydı

---

*Bu plan OpenCode üzerinde çalışan yüksek kapasiteli bir LLM'e verilmek üzere hazırlanmıştır.*
*Hiçbir adım atlanmamalı, bölüm sırası korunmalıdır.*
*Versiyon: 2.0 — LLM-first felsefesiyle tamamen yeniden yazılmıştır.*
