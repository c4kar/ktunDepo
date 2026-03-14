# ktunDepo — KTÜN Ders Materyali Deposu

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[**ktünot'un**](https://ktun.not.tr) *backend'i* — KTÜN EEM Ders Kaynak Arşivi

Bu depo, KTÜN Elektrik-Elektronik Mühendisliği Fakültesi öğrencileri için merkezi ders materyali deposudur. Öğrencilerin ders notlarını, sınav sorularını ve diğer materyalleri paylaşmasını sağlayan **event-driven bir AI agent sistemi** tarafından yönetilmektedir.

## 🎯 Özellikler

- **Otomatik Kalite Kontrolü**: Yüklenen materyaller AI tarafından değerlendirilir
- **Duplicate Tespiti**: Vektör veritabanı ile tekrar eden materyaller engellenir
- **OCR Desteği**: Taranmış dökümanlar otomatik olarak işlenir
- **Telegram Entegrasyonu**: Bot üzerinden materyal yükleme
- **Event-Driven Mimari**: Sadece gerektiğinde çalışır, kaynak tasarrufu sağlar

## 📁 Depo Yapısı

```
ktunDepo/
├── EEM-1/                    # 1. Dönem dersleri
│   ├── Matematik/
│   ├── Fizik/
│   ├── Lineer Cebir/
│   └── ...
├── EEM-2/                    # 2. Dönem dersleri
│   ├── Devre Analizi/
│   ├── Elektronik/
│   └── ...
├── agent/                    # AI Agent sistemi
│   ├── config.yaml          # Yapılandırma
│   ├── state.json           # Agent durumu
│   ├── prompts/             # LLM promptları
│   └── logs/                # Log dosyaları
├── bot/                      # Telegram bot
├── scripts/                  # Yardımcı scriptler
├── _incoming/               # Gelen materyal tamponu
└── vector_db/               # Qdrant vektör veritabanı
```

## 🚀 Kurulum

### Gereksinimler

- Python 3.10+
- Git
- Qdrant (vektör veritabanı)

### Adımlar

1. **Depoyu klonla:**
```bash
git clone https://github.com/c4kar/ktunDepo.git
cd ktunDepo
```

2. **Virtual environment oluştur:**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Bağımlılıkları yükle (uv ile):**
```bash
uv pip install -r pyproject.toml
```

4. **Ortam değişkenlerini ayarla:**
```bash
cp .env.example .env
# .env dosyasını düzenle
```

5. **Qdrant başlat (Docker ile):**
```bash
docker run -p 6333:6333 qdrant/qdrant
```

6. **Agent'ı başlat:**
```bash
python run_agent.py
```

7. **Bot'u başlat (ayrı terminalde):**
```bash
python run_bot.py
```

## 📱 Telegram Bot Komutları

| Komut | Açıklama |
|-------|----------|
| `/start` | Hoşgeldin mesajı |
| `/upload` | Materyal yükleme |
| `/status` | Agent durumu |
| `/stats` | Depo istatistikleri |
| `/request <ders>` | Materyal talebi |
| `/resume` | Bakım modundan çık (admin) |

## 🤖 Agent Modları

| Mod | Açıklama |
|-----|----------|
| `SLEEPING` | Varsayılan — kaynak tüketimi sıfır |
| `ACTIVE` | Materyal işleniyor |
| `MAINTENANCE` | Kritik hata — admin müdahalesi gerekli |

## ⚙️ Yapılandırma

`agent/config.yaml` dosyasından ayarları düzenleyebilirsiniz:

```yaml
quality:
  reject_threshold: 30    # Bu skorun altı reddedilir
  llm_threshold: 60       # Bu skorun altı LLM'e gider
  min_pages: 2            # Minimum sayfa sayısı

duplicate_detection:
  reject_similarity: 0.92 # Bu benzerlik üzeri duplicate
  warn_similarity: 0.75   # Bu aralık LLM'e sorulur
```

## 🔧 Geliştirme

### Agent'ı test et:
```bash
python run_agent.py --health    # Sağlık kontrolü
python run_agent.py --status    # Durum bilgisi
python run_agent.py --file <dosya>  # Tek dosya işle
```

### Loglara bak:
```bash
tail -f agent/logs/agent_*.log
```

## 📂 Harici Depoda Saklanan Dosyalar

Bu depoda boyut sınırlamaları nedeniyle saklanamayan büyük dosyalar harici depolarda saklanmaktadır:

- **Makine Klasörü**: [Google Drive Link](https://drive.google.com/drive/u/0/folders/1BR6jvwOUWVHJorOL7TDKO1c8UhJ3hXmP)

## 📊 Katkıda Bulunma

1. Bu depoyu fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/yenilik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik eklendi'`)
4. Branch'i push edin (`git push origin feature/yenilik`)
5. Pull Request açın

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🙏 Teşekkürler

- KTÜN EEM öğrencilerine katkıları için
- [OpenRouter](https://openrouter.ai) - Açık AI API
- [Qdrant](https://qdrant.tech) - Vektör veritabanı
- [Docling](https://github.com/DS4SD/docling) - PDF işleme

---

**Web:** [ktun.not.tr](https://ktun.not.tr)
