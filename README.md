# ai-linux-agent

## Yerel AI Ajan (Güvenli Linux Asistanı)

Bu proje, kullanıcı isteklerini adım adım plana çeviren, komutları **güvenlik politikası** ile doğrulayan, gerekirse **kullanıcı onayı** isteyen ve her şeyi **eğitici bir Markdown raporu** olarak üreten yerel bir ajan prototipidir.

## Özellikler

- Plan üretimi: İsteği adımlara böler (şimdilik basit planlayıcı taslağı).
- Güvenli çalıştırma: Komutlar shell olmadan çalıştırılır (`shell=False`).
- Politika: Allowlist/denylist + “onay gerektirir” kuralları.
- Kayıt: Append-only JSONL olay günlüğü (`agent_logs/events.jsonl`).
- Rapor: Markdown çıktı (`agent_report.md`).

## Çalıştırma

Kali Linux'ta tam akış (**her zaman ilk soru: isteğiniz**):

```bash
python3 main.py
# veya
python3 agent.py
```

- İlk soru: **İsteğiniz nedir?** (Komut satırına ek yazdığınız metin `[varsayılan]` olarak gösterilir.)
- Metinde **bilinen bir araç adı** geçiyorsa (ör. `nmap`, `sqlmap`, `hydra`, `gobuster`, … — tam liste `wizard.py` içinde), o araç(lar) için **Türkçe parametre sihirbazı** sırayla çalışır; sonra Ollama / model / rapor yolu sorulur.

### Kayıtlı sihirbaz araçları (genişletilebilir)

Tüm Kalideki araçların tamamı değil — `wizard.py` içindeki `WIZARD_REGISTRY` güncellenerek yeni araç eklenebilir. Şu an örnek: `sqlmap`, `nmap`, `hydra`, `gobuster`, `ffuf`, `wfuzz`, `nikto`, `wpscan`, `masscan`, `rustscan`, `enum4linux-ng` / `enum4linux`, `theHarvester`, `bloodhound-python`, `Responder`, `evil-winrm`.

Yol (Ollama’lı tam ajan) raporu `docs/report.md` dosyasına yazar:

```bash
ollama serve
ollama pull llama3
```

Eski/demo betik (**Ollama yok**, iç planlayıcı):

```bash
python3 local_ai_agent.py
```

Program adım adım planı gösterir; wizard komutları (örn. **nmap/sqlmap**) için `e/h` onayı ister ve `./agent_report.md` üretir.

## Üretilen Dosyalar

- `agent_report.md`: Adım adım, açıklamalı rapor
- `agent_logs/events.jsonl`: Her adımın olay kaydı

## Notlar

- Bu prototipte planlayıcı (LLM) kısmı örnek/stub şeklindedir. İsterseniz yerel LLM (Ollama) veya API tabanlı bir LLM ile değiştirilebilir; komutlar her zaman politika tarafından doğrulanmalıdır.

