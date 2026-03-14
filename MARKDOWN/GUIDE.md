# 📚 ktunDepo Başlanıç Rehberi

Terminal açtınız ve proje klasörüne geldiniz. Şimdi sıradaki adımlar bu rehberde anlatılıyor.

---

## 🚀 Hızlı Başlangıç (3 Dakika)

Eğer soruşturma imkanız yoksa, direkt bu komutları çalıştırın:

```bash
# 1. Bağımlılıkları yükle (ilk çalıştırmada)
pip install -e .

# 2. .env dosyasını oluştur ve doldur
cp .env.example .env
# Dosyayı açıp OPENROUTER_API_KEY ve TELEGRAM_BOT_TOKEN yazınız

# 3. Qdrant başlat (Docker ile)
docker run -d -p 6333:6333 qdrant/qdrant

# 4. Agent'ı başlat
python run_agent.py

# 5. Yeni terminal penceresi açıp bot'u başlat
python run_bot.py
```

Agent ve Bot artık çalışıyor. Telegram'dan `@ktunDepoBot`'a mesaj atın.

---

## 📖 Detaylı Rehber

### 1. RUN_AGENT.PY - Ana İşleme Sistemi

Agent otomatik olarak ders materyallerini işler ve deponuza organize eder.

#### Ne Yapar?
- 🎯 `_incoming/` klasörünü izler (dosya yüklenince hemen çalışır)
- 🔍 Dosya kalitesini kontrol eder
- 🤖 Claude AI ile inceleme yapıştırır
- 📚 Uygun dosyaları EEM-1, EEM-2... klasörlerine taşır
- ❌ Sorunlu dosyaları `_rejected/` klasörüne gönderir
- 💾 Her işlemi Git'e kaydeder

#### Komutlar

**Watchdog Modu** (24/7 İzleme - Tavsiye Edilen)
```bash
python run_agent.py
```
- Anlamı: `_incoming/` klasörünü sürekli izle, yeni dosya gelince hemen işle
- Çıkmak için: `Ctrl+C`
- Kullanım: Terminal açıp bırakın, arka planda çalışsın

**Kuyrukta Bekleyenleri İşle**
```bash
python run_agent.py --process
```
- Anlamı: `_pending/` klasöründeki bekleyen dosyaları işle, sonra kapat
- Kullanım: Agent'ı bir kez çalıştırıp kapat

**Sağlık Kontrolü**
```bash
python run_agent.py --health
```
- Çıktı Örneği:
```
🏥 Sağlık Kontrolü Raporu
=====================
Durum: ✅ SAĞLIKLI
Disk kullanımı: %45.2
Bekleyen dosya: 7
```

**Agent Durumunu Görüntüle**
```bash
python run_agent.py --status
```
- Çıktı Örneği:
```
📊 ktunDepo Agent Durumu
=====================
Mod: ACTIVE
Bugün işlenen: 5
Bugün reddedilen: 3
Token kullanımı: 12,450
Kuyruk: 7 dosya
```

**Tek Bir Dosyayı Hemen İşle**
```bash
python run_agent.py --file /path/to/file.pdf
```
- Anlamı: İlgili dosyayı hemen işler, sonucu gösterir
- Kullanım: Bir dosyayı test etmek için

**Günlük Sayaçları Sıfırla**
```bash
python run_agent.py --reset-daily
```
- Anlamı: Bugünün işlenen/reddedilen sayaçlarını 0'a çevirir

---

### 2. RUN_BOT.PY - Telegram Bot

Öğrenciler Telegram üzerinden dosya yükleyebilir.

#### Kullanmak İçin

1. **Bot'u Başlat**
```bash
python run_bot.py
```

2. **Telegram'dan Komut Gönder**
```
/start              → Hoşgeldin mesajı
/upload             → Dosya yükleme penceresi (tıkla → dosya gönder)
/status             → Agent durumu
/stats              → Depo istatistikleri
/request ders_adı   → Belirli ders materiali talep et
```

3. **Admin Komutları** (Sadece admin'e açık)
```
/pending_list       → Beklemede olan dosyaları listele
/approve dosya_id   → Dosyayı onayla
/reject dosya_id    → Dosyayı reddet
/resume             → Bakım modundan çık
```

#### Kurulum

Bot çalışması için `.env` dosyasında şunlar gerekli:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABC...   # @BotFather'dan aldığınız token
ADMIN_CHAT_ID=123456789                # Kendi Telegram ID'niz
```

---

### 3. İLK KURULUM ADIMLARI

#### Adım 1: Proje Klasörü

Eğer henüz klonlamadıysanız:
```bash
git clone https://github.com/c4kar/ktunDepo.git
cd ktunDepo
```

Zaten klasörü açtıysanız:
```bash
cd /home/c4kar/Code/ktunDepo
```

#### Adım 2: Python Bağımlılıkları

Seçenek A: pip ile (basit)
```bash
pip install -e .
```

Seçenek B: uv ile (daha hızlı - önerilen)
```bash
pip install uv
uv pip install -e .
```

Kontrol edin:
```bash
python -c "import langgraph; import qdrant_client; print('✓ OK')"
```

#### Adım 3: .env Dosyası

Eğer yok ise oluşturun:
```bash
cp .env.example .env
```

Açıp gerekli değerleri yazın:
```bash
vim .env
# Veya VS Code ile
code .env
```

Yazılması gereken değerler:

```env
# LLM API (ZORUNLU - AI incelemesi için)
OPENROUTER_API_KEY=sk-or-v1-xxx...
# Ya da
ANTHROPIC_API_KEY=sk-ant-xxx...

# Telegram Bot (ZORUNLU - Bot çalışması için)
TELEGRAM_BOT_TOKEN=1234567890:ABCD...
ADMIN_CHAT_ID=123456789

# Qdrant (lokal kullanıyorsanız boş bırakılabilir)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# GitHub (otomatik push için - opsiyonel)
GITHUB_TOKEN=ghp_xxx...

# Loglama
LOG_LEVEL=INFO
```

#### Adım 4: Qdrant Başlat

Qdrant, dosyaların duplicate'lerini tespit etmek için kullanılır.

```bash
# Docker ile (tavsiye edilen)
docker run -d -p 6333:6333 qdrant/qdrant

# Kontrol edin
curl http://localhost:6333/health
```

Çıktı: `{"title":"qdrant - vector search engine","version":"...","status":"ok"}`

#### Adım 5: Sağlık Kontrolü

```bash
python run_agent.py --health
```

Her şey OK ise:
```
🏥 Sağlık Kontrolü Raporu
Durum: ✅ SAĞLIKLI
```

#### Adım 6: Agent'ı Başlat

```bash
# Terminal 1
python run_agent.py
```

Çıktı:
```
🚀 ktunDepo Agent başladı (watchdog mode)
📁 Monitoring: /home/c4kar/Code/ktunDepo/_incoming
```

#### Adım 7: Bot'u Başlat (Ayrı Terminal)

```bash
# Terminal 2 (yeni)
python run_bot.py
```

Çıktı:
```
✅ Bot started. Listening for messages...
```

---

### 4. KLASÖR YAPISI VE AMAÇLARI

Proje klasöründe şu klasörler var:

```
ktunDepo/
│
├── 📥 _INCOMING/       ← Yeni dosyalar buraya yüklenir
│                         Agent bunu izler ve işler
│
├── ⏳ _PENDING/        ← İşleme başladı ama henüz tamamlanmadı
│                         (OCR, LLM kontrol, vb)
│
├── ✅ _REVIEW/         ← Manuel inceleme gereken dosyalar
│                         Admin gözden geçirir
│
├── ❌ _REJECTED/       ← Reddedilen dosyalar
│                         (kopya, kötü kalite, vs)
│
├── 🗂️ _ARCHIVED/       ← Arşivlenmiş dosyalar
│
├── 📚 EEM-1/           ← 1. DÖNEM DERSLERI
│   ├── Matematik/
│   ├── Fizik/
│   └── ...
│
├── 📚 EEM-2/           ← 2. DÖNEM DERSLERI
│   ├── Devre Analizi/
│   ├── Elektronik/
│   └── ...
│
├── 📚 EEM-3/ ... EEM-8/  ← DİĞER DÖNEMLER
│
├── 🤖 agent/           ← AI AGENT KODU
│   ├── config.yaml     ← Agent ayarları
│   ├── logs/           ← Log dosyaları
│   └── ...
│
├── 💬 bot/             ← TELEGRAM BOT KODU
│   └── ...
│
├── 🔢 vector_db/       ← Qdrant vektörleri (duplicate tespiti)
│
├── 📝 .env             ← API keys (gizli dosya - GIT'e commit'leme!)
├── 📄 pyproject.toml   ← Python bağımlılıkları
└── 📄 README.md        ← Dokümantasyon
```

---

### 5. DOSYA YÜKLEME İŞLEMİ

#### Dosyaları Nasıl Yüklerim?

**Yöntem 1: Telegram Bot ile (Tavsiye Edilen)**

```
1. Telegram'da @ktunDepoBot'u bul
2. /start yazıp başlat
3. /upload yazıp dosya yüklemeyi aç
4. Dosyayı seç ve gönder
5. Ders türünü seç (dropdown'dan)
6. ✅ Gönder
```

Bot otomatik olarak dosyayı `_incoming/` klasörüne koyar ve Agent işlemeye başlar.

**Yöntem 2: Manuel Upload (Test için)**

```bash
# Dosyayı _incoming/ klasörüne kopyala
cp ~/Desktop/my_notes.pdf _incoming/

# Eğer watchdog açıksa otomatik işlenir
# Açık değilse manual çalıştırın:
python run_agent.py --process
```

#### Dosya İşleme Akışı

```
1. Dosya _incoming/ klasörüne konuyor
                ↓
2. Agent detects (watchdog) → _pending/ taşır
                ↓
3. Teknik kontrol
   ✓ Dosya formatu OK? (.pdf, .pptx, vb)
   ✓ Dosya boyutu OK? (50KB - 200MB)
   ✓ PDF sayfa sayısı ≥ 2?
   ✗ Başarısız → _rejected/ (reason.txt ile)
                ↓
4. Duplicate kontrol (Qdrant)
   ✓ Kopya değil → devam
   ✗ Kesin kopya (%92+ benzer) → _rejected/
   ? Belki kopya (%75-92%) → AI'ya sor
                ↓
5. Kalite puanı hesapla
   ✓ Çok iyiyse → Devam
   ✗ Kötüyse → _rejected/
   ? Orta iyiyse → AI'ya sor
                ↓
6. Claude AI ile inceleme
   ✓ "Bu ders materyali mi?"
   ✓ "KTÜN öğrencileri için faydalı mı?"
   → Karar: ACCEPT / REJECT
                ↓ ACCEPTED
7. OCR (eğer taranmış PDF ise)
   Resim → Metin'e çevir
                ↓
8. Ders eşleştir
   "Devre Analizi II" → EEM-2/Devre Analizi/
                ↓
9. Final output
   ✓ ACCEPTED → _review/ veya direkt EEM-X/Ders/
   ✗ REJECTED → _rejected/ (log ile)
                ↓
10. Git commit + push
    "Added: Math notes for EEM-1"
```

---

### 6. SORUNLAR VE ÇÖZÜMLERI

| Sorun | Çözüm |
|-------|-------|
| ❌ `ModuleNotFoundError: langgraph` | `pip install -e .` çalıştırın |
| ❌ `Qdrant connection refused` | `docker run -p 6333:6333 qdrant/qdrant` |
| ❌ `TELEGRAM_BOT_TOKEN not found` | `.env` dosyasını kontrol edin |
| ❌ `.env dosyası bulunamadı` | `cp .env.example .env` sonra düzenleyin |
| ⚠️ `Error code: 400` LLM hatası | Dosya çok büyük veya bozuk olabilir |
| 🐢 Agent çok yavaş çalışıyor | `tail -f agent/logs/agent_*.log` ile loglara bakın |
| 🔴 Bot offline | `python run_bot.py`'nin çalışıp çalışmadığını kontrol edin |

---

### 7. LOGLARA BAKMAK

Agent ve Bot'un çalışıp çalışmadığını anlamak için loglara bakabilirsiniz:

```bash
# Agent log'ları
tail -f agent/logs/agent_*.log

# En son hataları göster
grep ERROR agent/logs/agent_*.log | tail -20

# Belirli dosya hakkında bilgi ara
grep "my_notes.pdf" agent/logs/agent_*.log

# Tüm loglarda REJECTED dosyaları ara
grep REJECTED agent/logs/agent_*.log
```

---

### 8. KOMUT ÖZETI

Sık kullanılan komutlar:

| İşlem | Komut |
|-------|-------|
| **Kurulum** | `pip install -e .` |
| **Agent başlat** | `python run_agent.py` |
| **Bot başlat** | `python run_bot.py` |
| **Agent durumu** | `python run_agent.py --status` |
| **Sağlık kontrolü** | `python run_agent.py --health` |
| **Bekleyen dosyaları işle** | `python run_agent.py --process` |
| **Loglara bak** | `tail -f agent/logs/agent_*.log` |
| **Qdrant kontrol** | `curl http://localhost:6333/health` |
| **Qdrant başlat** | `docker run -d -p 6333:6333 qdrant/qdrant` |

---

## ⚡ En Hızlı Başlangıç (Copy-Paste)

Terminale yapıştırın:

```bash
# 1. Buraya gidin
cd /home/c4kar/Code/ktunDepo

# 2. Bağımlılık yükle
pip install -e .

# 3. .env oluştur
cp .env.example .env

# 4. Qdrant başlat
docker run -d -p 6333:6333 qdrant/qdrant

# 5. Agent başlat (backgroundde)
nohup python run_agent.py > agent.log 2>&1 &

# 6. Bot başlat (backgroundde)
nohup python run_bot.py > bot.log 2>&1 &

# 7. Kontrol et
sleep 3
curl http://localhost:6333/health
python run_agent.py --health

# 8. Bitti! Artık telegram'dan @ktunDepoBot'a mesaj atabilirsiniz
```

---

## 📞 Yardım Gerekirse

- Agent loglara bakın: `tail -f agent/logs/agent_*.log`
- Belirli dosyayı test edin: `python run_agent.py --file path/to/file.pdf`
- API keys'i kontrol edin: `cat .env | grep -E "OPENROUTER|ANTHROPIC|TELEGRAM"`
- Qdrant sağlığını kontrol edin: `curl http://localhost:6333/health`

---

**Hepsi bu! Agent şimdi otomatik olarak dosyaları işleyecek. İyi çalışmalar! 🚀**
