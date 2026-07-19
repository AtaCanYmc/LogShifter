# Logshift SDK

Logshift, Supabase gibi veri kaynaklarından belirli zamanlarda (cron) log verilerini çekip, bunları aynı anda veya seçmeli olarak farklı depolama ve bildirim servislerine (GitHub, Telegram, Google Sheets) güvenli şekilde aktaran ve arşivleyen çoklu hedefli, modüler bir Python SDK'sıdır.

## 🚀 Temel Özellikler

- **Strategy Pattern:** Her taşıma yöntemi (`TransportAdapter`) için tamamen bağımsız, genişletilebilir ve modüler sınıflar.
- **Open/Closed Prensibi:** Mevcut kütüphane koduna dokunmadan yeni taşıma adaptörleri ekleyebilme.
- **Modern Python:** Tamamen `async/await` desteği, güçlü tip belirteçleri (type hints) ve temiz mimari.
- **Modüler Yapı:** `core` ve `adapters` paket ayrımı.
- **Explicit Parametre Yönetimi:** Dış bağımlılık oluşturabilecek `.env` veya global dosya okuma zorunlulukları yerine, tüm kimlik ve yapılandırma bilgileri doğrudan parametre olarak sınıflara geçilir.
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
└── adapters/
    ├── __init__.py
    └── github.py       # GitHub Contents API Adaptörü
```

---

## 🛠️ Kurulum ve Çalıştırma

### 1. Sanal Ortam Kurulumu
Proje klasöründe bir sanal ortam oluşturun ve aktif edin:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 💻 Kullanım Örneği

```python
import asyncio
from logshift import LogManager, GitHubAdapter

async def main():
    # 1. LogManager ve Adaptörleri Oluştur (Parametreleri açıkça geçiyoruz)
    manager = LogManager()
    
    github_adapter = GitHubAdapter(
        token="ghp_yourPersonalAccessTokenHere",
        name="github"
    )
    
    # Adaptörü kaydet
    manager.register_adapter(github_adapter)
    
    # 2. Log Verisi Hazırla
    logs = [
        {"timestamp": "2026-07-19T19:00:00Z", "level": "INFO", "message": "Logshift initialized."},
        {"timestamp": "2026-07-19T19:05:00Z", "level": "ERROR", "message": "Connection lost to Supabase."}
    ]
    
    # 3. Seçmeli veya Çoklu Gönderim Yap
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
