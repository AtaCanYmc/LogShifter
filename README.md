# Logshift SDK

Logshift, Supabase gibi veri kaynaklarından belirli zamanlarda (cron) log verilerini çekip, bunları aynı anda veya seçmeli olarak farklı depolama ve bildirim servislerine (GitHub, Google Sheets, Telegram) güvenli şekilde aktaran ve arşivleyen çoklu hedefli, modüler bir Python SDK'sıdır.

## 🚀 Temel Özellikler

- **Multi-Channel Transport:** Logları aynı anda veya seçmeli olarak GitHub, Google Sheets ve Telegram kanallarına aktarabilme.
- **Strategy Pattern & Open/Closed:** Her taşıma kanalı (`TransportAdapter`) için tamamen bağımsız, genişletilebilir soyut mimari.
- **Cursor-Based Pagination:** Supabase'den logları çekerken veritabanı performansını optimize eden, hafıza limitlerini aşmayan ID bazlı cursor sayfalaması.
- **Güvenli Konfigürasyon:** `pydantic-settings` tabanlı, ortam değişkenleri (.env) üzerinden otomatik doğrulanan ve yüklenen güvenli yapılandırma.
- **Hata Toleransı (Fallback & Retry):** Geçici ağ hatalarına karşı log gönderim adımlarında üstel geri çekilme (exponential backoff) destekli otomatik yeniden deneme (retry) mekanizması.
- **Dry-Run Modu:** Veri kaybını önlemek için gerçekte hiçbir kanala işlem yapmadan çalışmayı simüle eden `--dry-run` test sürüşü modu.

---

## 📁 Dosya Dizin Yapısı

```text
LogShifter/
├── src/
│   └── logshift/
│       ├── __init__.py
│       ├── config.py       # Pydantic Settings yapılandırması
│       ├── core.py         # LogManager, LogFetcher ve Taban Adaptör sınıfı
│       └── adapters/
│           ├── __init__.py
│           ├── github.py   # GitPython tabanlı GitHub arşiv adaptörü
│           ├── sheets.py   # gspread tabanlı Google Sheets adaptörü
│           └── telegram.py # httpx tabanlı Telegram bildirim adaptörü
├── tests/                  # Unit testler
├── pyproject.toml          # Paket tanımları, araçlar ve bağımlılıklar
├── requirements.txt        # Geliştirme bağımlılık listesi
└── .env.example            # Örnek konfigürasyon dosyası
```

---

## 🛠️ Kurulum ve Çalıştırma

### 1. Sanal Ortam Kurulumu
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Konfigürasyon
`.env.example` dosyasını `.env` olarak kopyalayın ve gerekli kimlik bilgilerini doldurun:
```bash
cp .env.example .env
```

---

## 💻 CLI Kullanımı

### Tüm Kanallara Dry-Run (Test Sürüşü) Modunda Gönderim
Gerçek veritabanına ve dış kanallara dokunmadan simülasyon çıktısı üretir:
```bash
logshift --dry-run archive --source supabase --dest github,sheets,telegram
```

### Belirli Kanallara Gerçek Zamanlı Arşivleme
```bash
logshift archive --source supabase --dest github,telegram
```

---

## 👨‍💻 Kod Üzerinden Kullanım

```python
import asyncio
from logshift.core import LogManager
from logshift.adapters.github import GitHubAdapter
from logshift.adapters.telegram import TelegramAdapter

async def main():
    # Manager oluştur (Örn: 4 deneme, üstel geri çekilme aktif)
    manager = LogManager(dry_run=False, max_retries=4, initial_delay=1.0)
    
    # Adaptörleri kaydet
    manager.register_adapter(GitHubAdapter(token="your_github_token"))
    manager.register_adapter(TelegramAdapter(bot_token="bot_token", chat_id="chat_id"))
    
    # Logları gönder
    logs = [{"id": 101, "level": "ERROR", "message": "Critical DB connection failure"}]
    targets = {
        "github": "myuser/my-repo",
        "telegram": "chat_id"
    }
    
    report = await manager.ship(logs=logs, targets=targets)
    print("Shipment Report:", report)

if __name__ == "__main__":
    asyncio.run(main())
```
