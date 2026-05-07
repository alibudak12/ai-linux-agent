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

- İlk soru: **İsteğiniz nedir?** (Komut satırına ek yazdığınız metin `[varsayılan]` olarak gösterilir; Enter yaparsanız o metin seçilir.)
- İsteğinizde **sqlmap** geçiyorsa, hedef URL ve diğer seçenekler **Türkçe, tek tek** sorulur; ardından Ollama adresi / model / rapor dosyası sorulur.
- `python3 main.py sistem analizi` gibi parametre kullanırsanız yine **önce İsteğiniz** çıkar; CLI metni varsayılan olur.

Yol (Ollama’lı tam ajan) raporu `docs/report.md` dosyasına yazar:

```bash
ollama serve
ollama pull llama3
```

Eski/demo betik (**Ollama yok**, iç planlayıcı):

```bash
python3 local_ai_agent.py
```

Program adım adım planı gösterir; riskli komutlar (ör. `sqlmap`) için `e/h` onayı ister ve `./agent_report.md` üretir.

## Üretilen Dosyalar

- `agent_report.md`: Adım adım, açıklamalı rapor
- `agent_logs/events.jsonl`: Her adımın olay kaydı

## Notlar

- Bu prototipte planlayıcı (LLM) kısmı örnek/stub şeklindedir. İsterseniz yerel LLM (Ollama) veya API tabanlı bir LLM ile değiştirilebilir; komutlar her zaman politika tarafından doğrulanmalıdır.

