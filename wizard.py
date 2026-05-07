#!/usr/bin/env python3
"""
Ortak interaktif sihirbaz: önce kullanıcı isteği, gerekirse sqlmap parametreleri.
Yalnızca yasal/izinli penetrasyon testi ve eğitim ortamlarında kullanım içindir.
"""

import shlex
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


def _prompt_line(mesaj: str, varsayilan: str = "") -> str:
    if varsayilan:
        s = input(f"{mesaj} [{varsayilan}]: ").strip()
        return s if s else varsayilan
    s = input(f"{mesaj}: ").strip()
    return s


def _prompt_eh(mesaj: str, varsayilan_evet: bool) -> bool:
    d = "e" if varsayilan_evet else "h"
    while True:
        s = input(f"{mesaj} (e/h) [{d}]: ").strip().lower()
        if not s:
            s = d
        if s in {"e", "evet", "y", "yes"}:
            return True
        if s in {"h", "hayır", "hayir", "n", "no"}:
            return False
        print("Lütfen e veya h ile yanıtlayın.")


def isteginizi_sorun(argv: Optional[List[str]] = None) -> str:
    """
    İlk soru: ne yapmak istiyorsunuz?
    CLI'dan ek argüman varsa bunu köşeli parantezde varsayılan gösterir.
    """
    if argv is None:
        argv = sys.argv
    varsayilan = " ".join(argv[1:]).strip()
    msj = "İsteğiniz nedir?"
    if varsayilan:
        s = input(f"{msj} [{varsayilan}]: ").strip()
        return s if s else varsayilan
    s = input(f"{msj}: ").strip()
    return s


def sqlmap_istedi_mi(metin: str) -> bool:
    return "sqlmap" in metin.lower()


@dataclass
class SqlmapAyarlari:
    hedef_url: str
    http_metodu: str = "GET"
    post_verisi: str = ""
    cookie: str = ""
    user_agent: str = ""
    referer: str = ""
    seviye: str = "1"
    risk: str = "1"
    teknikler: str = ""
    threads: str = "1"
    proxy: str = ""
    dbms: str = ""
    batch: bool = True
    tor: bool = False
    random_agent: bool = False
    extra_argv: List[str] = field(default_factory=list)


def sqlmap_parametreleri_sor() -> SqlmapAyarlari:
    print("\n--- sqlmap parametreleri (tek tek) ---")
    print("Uyarı: Yalnızca izniniz olan / yasal test ortamlarında kullanın.\n")

    url = _prompt_line("1) Hedef tam URL (ör. http://site.com/page.php?id=1)", "")
    while not url:
        print("URL zorunludur.")
        url = _prompt_line("1) Hedef tam URL", "")

    metod = _prompt_line("2) HTTP metodu (GET / POST / PUT)", "GET").upper()
    if metod not in {"GET", "POST", "PUT"}:
        metod = "GET"

    post = ""
    if metod in {"POST", "PUT"}:
        post = _prompt_line("3) POST/PUT gövdesi (--data, ör. user=1&pass=test)", "")

    cookie = _prompt_line("4) Cookie (--cookie, boş bırakılabilir)", "")
    ua = _prompt_line("5) User-Agent (boş = sqlmap varsayılanı)", "")
    ref = _prompt_line("6) Referer (--referer, boş bırakılabilir)", "")

    seviye = _prompt_line("7) --level (1-5)", "1")
    risk = _prompt_line("8) --risk (1-3)", "1")
    teknik = _prompt_line("9) --technique (ör. BEUSTQ, boş = otomatik)", "")
    threads = _prompt_line("10) --threads", "1")
    proxy = _prompt_line("11) --proxy (ör. http://127.0.0.1:8080, boş bırakılabilir)", "")
    dbms = _prompt_line("12) --dbms (ör. MySQL, boş = otomatik)", "")

    tor = _prompt_eh("13) Tor kullanılsın mı (--tor)?", False)
    ragent = _prompt_eh("14) Rastgele User-Agent (--random-agent)?", False)
    batch = _prompt_eh("15) Onayları otomatik kabul (--batch)?", True)

    ek = _prompt_line(
        "16) Ek parametreler (tek satır; boşlukla ayırın, ör. --eta --fresh-queries)",
        "",
    )
    extra: List[str] = []
    if ek:
        try:
            extra = shlex.split(ek, posix=True)
        except ValueError:
            extra = ek.split()

    return SqlmapAyarlari(
        hedef_url=url,
        http_metodu=metod,
        post_verisi=post,
        cookie=cookie,
        user_agent=ua,
        referer=ref,
        seviye=seviye,
        risk=risk,
        teknikler=teknik,
        threads=threads,
        proxy=proxy,
        dbms=dbms,
        batch=batch,
        tor=tor,
        random_agent=ragent,
        extra_argv=extra,
    )


def sqlmap_argv_olustur(t: SqlmapAyarlari) -> List[str]:
    argv = ["sqlmap", "-u", t.hedef_url]

    if t.http_metodu != "GET":
        argv.extend(["--method", t.http_metodu])

    if t.post_verisi:
        argv.extend(["--data", t.post_verisi])

    if t.cookie:
        argv.extend(["--cookie", t.cookie])

    if t.user_agent:
        argv.extend(["--user-agent", t.user_agent])

    if t.referer:
        argv.extend(["--referer", t.referer])

    argv.extend(["--level", str(t.seviye), "--risk", str(t.risk)])

    if t.teknikler:
        argv.extend(["--technique", t.teknikler])

    argv.extend(["--threads", str(t.threads)])

    if t.proxy:
        argv.extend(["--proxy", t.proxy])

    if t.dbms:
        argv.extend(["--dbms", t.dbms])

    if t.batch:
        argv.append("--batch")

    if t.tor:
        argv.append("--tor")

    if t.random_agent:
        argv.append("--random-agent")

    argv.extend(t.extra_argv)
    return argv


def sqlmap_komut_metni(argv: List[str]) -> str:
    return " ".join(shlex.quote(x) for x in argv)


def istegi_zenginlestir(istek: str) -> Tuple[str, Optional[List[str]]]:
    """
    İstek metnini LLM / rapor için genişletir.
    sqlmap ise argv döner; değilse argv None.
    """
    if not sqlmap_istedi_mi(istek):
        return istek, None

    t = sqlmap_parametreleri_sor()
    argv = sqlmap_argv_olustur(t)
    komut = sqlmap_komut_metni(argv)

    blok = (
        f"\n\n[Kullanıcı sqlmap kullanmak istedi. Toplanan bilgiler]\n"
        f"- URL: {t.hedef_url}\n"
        f"- Metod: {t.http_metodu}\n"
        f"- POST/PUT gövdesi: {t.post_verisi or '(yok)'}\n"
        f"- Cookie: {t.cookie or '(yok)'}\n"
        f"- Seviye/Risk: {t.seviye}/{t.risk}\n"
        f"- Teknikler: {t.teknikler or '(otomatik)'}\n"
        f"- Threads: {t.threads}\n"
        f"- Proxy: {t.proxy or '(yok)'}\n"
        f"- DBMS: {t.dbms or '(otomatik)'}\n"
        f"- Tor: {'evet' if t.tor else 'hayır'}\n"
        f"- --batch: {'evet' if t.batch else 'hayır'}\n"
        f"- Önerilen komut:\n{komut}\n"
        f"\nLütfen yalnızca bu parametreleri kullanarak güvenli adımları planlayın "
        f"ve komutu doğrudan kopyalayın; gereksiz başka araç eklemeyin."
    )

    return istek + blok, argv


def ollama_ayarlarini_sor_interaktif(default_base: str, default_model: str, default_rapor: str) -> Tuple[str, str, str]:
    base = _prompt_line("Ollama sunucu adresi", default_base)
    model = _prompt_line("Model adı", default_model)
    rapor = _prompt_line("Rapor dosya yolu (Markdown)", default_rapor)
    return base, model, rapor


def tam_interaktif_akis() -> Tuple[str, str, str, str]:
    """
    Tüm terminal akışı: istek → (sqlmap ise parametreler) → Ollama/rapor ayarları.
    Dönüş: (llm_istek_metni, ollama_base, model, rapor_yolu)
    """
    istek = isteginizi_sorun()
    if not istek.strip():
        raise ValueError("İstek boş olamaz.")

    user_request, sqlmap_argv = istegi_zenginlestir(istek)
    if sqlmap_argv:
        print("\nÖnerilen sqlmap komutu (LLM ve rapora da eklenecek):\n")
        print(sqlmap_komut_metni(sqlmap_argv))
        print()

    base, model, rapor = ollama_ayarlarini_sor_interaktif(
        "http://localhost:11434", "llama3", "docs/report.md"
    )
    return user_request, base, model, rapor
