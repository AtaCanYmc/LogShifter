# Logshift SDK

Logshift, Supabase gibi veri kaynaklarından belirli zamanlarda (cron) log verilerini çekip, bunları aynı anda veya seçmeli olarak farklı depolama ve bildirim servislerine (GitHub, Telegram, Google Sheets) güvenli şekilde aktaran ve arşivleyen çoklu hedefli, modüler bir Python SDK'sıdır.

## 🚀 Temel Özellikler

- **Strategy Pattern:** Her taşıma yöntemi (`TransportAdapter`) için tamamen bağımsız, genişletilebilir ve modüler sınıflar.
- **Open/Closed Prensibi:** Mevcut kütüphane koduna dokunmadan yeni taşıma adaptörleri ekleyebilme.
- **Modern Python:** Tamamen `async/await` desteği, güçlü tip belirteçleri (type hints) ve temiz mimari.
- **Modüler Yapı:** `core`, `adapters` ve `utils` paket ayrımı.
- **Güvenli Konfigürasyon:** `.env` yapısı ile hassas API anahtarlarının ve ayarların yönetimi.
- **Genişletilebilirlik:** Gelecekte MCP (Model Context Protocol) sunucusu olarak çalışabilecek altyapıya uygun tasarım.

---

## 📁 Dosya Dizin Yapısı

```text
logshift/
├── __init__.py         # Paket dışa aktarımları
├── core/
│   ├── __init__.py
│   ├── adapter.py      # Soyut TransportAdapter Sınıfı
│   ├── manager.py      # Çoklu hedef yönetimi yapan LogManager
│   └── exceptions.py   # Özel Hata Sınıfları
├── adapters/
│   ├── __init__.py
│   └── github.py       # GitHub Contents API Adaptörü
└── utils/
    ├── __init__.py
    └── config.py       # .env ve Konfigürasyon Yönetimi
```

---

## 🛠️ Kurulum ve Çalıştırma

### 1. Sanal Ortam Kurulumu
Proje klasöründe bir sanal ortam oluşturun ve aktif edin:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Konfigürasyon Tanımlama
`.env.example` dosyasını `.env` olarak kopyalayın ve gerekli kimlik bilgilerini doldurun:
```bash
cp .env.example .env
```

`.env` içeriği örneği:
```env
LOGSHIFT_GITHUB_TOKEN=ghp_yourPersonalAccessTokenHere
```

---

## 💻 Kullanım Örneği

```python
import asyncio
from logshift import LogManager, GitHubAdapter, load_env

async def main():
    # 1. Konfigürasyonu yükle
    env = load_env()
    
    # 2. LogManager ve Adaptörleri Oluştur
    manager = LogManager()
    
    github_adapter = GitHubAdapter(
        name="github",
        config={"LOGSHIFT_GITHUB_TOKEN": env.get("LOGSHIFT_GITHUB_TOKEN")}
    )
    
    # Adaptörü kaydet
    manager.register_adapter(github_adapter)
    
    # 3. Log Verisi Hazırla
    logs = [
        {"timestamp": "2026-07-19T19:00:00Z", "level": "INFO", "message": "Logshift initialized."},
        {"timestamp": "2026-07-19T19:05:00Z", "level": "ERROR", "message": "Connection lost to Supabase."}
    ]
    
    # 4. Seçmeli veya Çoklu Gönderim Yap
    targets = {
        "github": "username/my-logs-repo"
    }
    
    report = await manager.ship(
        logs=logs,
        targets=targets,
        path="archives/2026-07-19_log.json",
        message="chore: auto-archive logs via logshift"
    )
    
    print("Taşıma Raporu:", report)

if __name__ == "__main__":
    asyncio.run(main())
```
