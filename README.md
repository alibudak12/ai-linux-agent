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

Kali Linux'ta:

```bash
python3 main.py "analyze system"
```

İsterseniz parametre vererek çalıştırabilirsiniz. Parametre vermezseniz program **interaktif olarak** şu parametreleri Türkçe sorar:

- İstek
- Ollama adresi
- Model adı
- Rapor yolu

Program adım adım planı gösterir, gerekiyorsa riskli adımlar için `e/h` onayı ister ve raporu `docs/report.md` dosyasına yazar.

## Üretilen Dosyalar

- `agent_report.md`: Adım adım, açıklamalı rapor
- `agent_logs/events.jsonl`: Her adımın olay kaydı

## Notlar

- Bu prototipte planlayıcı (LLM) kısmı örnek/stub şeklindedir. İsterseniz yerel LLM (Ollama) veya API tabanlı bir LLM ile değiştirilebilir; komutlar her zaman politika tarafından doğrulanmalıdır.

