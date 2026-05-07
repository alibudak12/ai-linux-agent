#!/usr/bin/env python3
"""
Ortak interaktif sihirbaz: önce kullanıcı isteği; metinde geçen **kayıtlı** Kali araçları için
sırayla Türkçe parametre sorulur.

Not: Kalideki *tüm* araçlar tek tek eklenemez; bu dosyadaki WIZARD_REGISTRY genişletilebilir.
Yalnızca yasal/izinli pentest ve lab ortamlarında kullanın.
"""

import re
import shlex
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

WizardFn = Callable[[], Tuple[str, List[str]]]


# ---- Genel ----


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


def _ek_argumanlar_satir(prompt: str) -> List[str]:
    ek = _prompt_line(prompt, "")
    if not ek.strip():
        return []
    try:
        return shlex.split(ek, posix=True)
    except ValueError:
        return ek.split()


def komut_metni_quote(argv: List[str]) -> str:
    return " ".join(shlex.quote(x) for x in argv)


def isteginizi_sorun(argv: Optional[List[str]] = None) -> str:
    if argv is None:
        argv = sys.argv
    varsayilan = " ".join(argv[1:]).strip()
    msj = "İsteğiniz nedir?"
    if varsayilan:
        s = input(f"{msj} [{varsayilan}]: ").strip()
        return s if s else varsayilan
    s = input(f"{msj}: ").strip()
    return s


def _blok_metni(etiket: str, ozet_satirlari: List[str], argv: List[str]) -> str:
    body = "\n".join(f"- {s}" for s in ozet_satirlari)
    return (
        f"\n\n[{etiket}] parametreleri toplandı.\n"
        f"{body}\n"
        f"Önerilen komut:\n{komut_metni_quote(argv)}\n"
    )


# ---- Kelime sınırı ile araç algılama ----

_ALGILATICILAR: List[Tuple[str, str]] = [
    ("sqlmap", r"\bsqlmap\b"),
    ("nmap", r"\bnmap\b"),
    ("hydra", r"\bhydra\b"),
    ("gobuster", r"\bgobuster\b"),
    ("ffuf", r"\bffuf\b"),
    ("wfuzz", r"\bwfuzz\b"),
    ("nikto", r"\bnikto\b"),
    ("wpscan", r"\bwpscan\b"),
    ("masscan", r"\bmasscan\b"),
    ("rustscan", r"\brustscan\b"),
    ("enum4linux", r"\benum4linux(?:-ng|-ng-py)?\b"),
    ("theharvester", r"\btheharvester\b"),
    ("bloodhound-python", r"\bbloodhound-python\b"),
    ("responder", r"\bresponder\b"),
    ("evil-winrm", r"\bevil-winrm\b"),
]


def algilanan_araclar(metin: str) -> List[str]:
    low = metin.lower()
    bulunan: List[str] = []
    for arac_id, pattern in _ALGILATICILAR:
        if arac_id in bulunan:
            continue
        if re.search(pattern, low, re.IGNORECASE):
            bulunan.append(arac_id)
    return bulunan


def sqlmap_istedi_mi(metin: str) -> bool:
    return "sqlmap" in algilanan_araclar(metin)


# ---- sqlmap ----


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
    print("\n--- sqlmap parametreleri ---")
    print("Uyarı: Yalnızca izin verilen hedeflerde kullanın.\n")

    url = _prompt_line("1) Hedef tam URL", "")
    while not url:
        url = _prompt_line("1) Hedef tam URL", "")

    metod = _prompt_line("2) HTTP metodu (GET / POST / PUT)", "GET").upper()
    if metod not in {"GET", "POST", "PUT"}:
        metod = "GET"

    post = ""
    if metod in {"POST", "PUT"}:
        post = _prompt_line("3) POST/PUT gövdesi (--data)", "")

    cookie = _prompt_line("4) Cookie (--cookie)", "")
    ua = _prompt_line("5) User-Agent", "")
    ref = _prompt_line("6) Referer", "")
    seviye = _prompt_line("7) --level (1-5)", "1")
    risk = _prompt_line("8) --risk (1-3)", "1")
    teknik = _prompt_line("9) --technique (boş = otomatik)", "")
    threads = _prompt_line("10) --threads", "1")
    proxy = _prompt_line("11) --proxy", "")
    dbms = _prompt_line("12) --dbms", "")

    tor = _prompt_eh("13) --tor?", False)
    ragent = _prompt_eh("14) --random-agent?", False)
    batch = _prompt_eh("15) --batch?", True)
    extra = _ek_argumanlar_satir("16) Ek parametreler (tek satır)", "")

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


def _sihirbaz_sqlmap() -> Tuple[str, List[str]]:
    t = sqlmap_parametreleri_sor()
    argv = sqlmap_argv_olustur(t)
    ozet = [
        f"URL: {t.hedef_url}",
        f"Metod: {t.http_metodu}",
        f"level/risk: {t.seviye}/{t.risk}",
    ]
    return _blok_metni("SQLMAP", ozet, argv), argv


def _sihirbaz_nmap() -> Tuple[str, List[str]]:
    print("\n--- nmap parametreleri ---")
    hedef = _prompt_line("1) Hedef (IP / CIDR / FQDN; birden fazla için boşlukla)", "")
    while not hedef.strip():
        hedef = _prompt_line("1) Hedef", "")
    hedef_argv = shlex.split(hedef, posix=True)

    port = _prompt_line("2) Portlar (-p; boş = nmap varsayılan top portları)", "")
    z = _prompt_line("3) -T zamanlama (0-5)", "4").strip()
    if not z or z not in {"0", "1", "2", "3", "4", "5"}:
        z = "4"

    udp = _prompt_eh("4) UDP taraması (-sU)? Root gerekebilir.", False)
    agresif = _prompt_eh("5) Agresif paket (-A)?", False)
    sv = _prompt_eh("6) Servis/sürüm (-sV)?", True) if not agresif else True

    argv: List[str] = ["nmap", f"-T{z}"]
    if udp:
        argv.append("-sU")
        if sv:
            argv.append("-sV")
    elif agresif:
        argv.append("-A")
    else:
        if sv:
            argv.append("-sV")

    if port.strip():
        argv.extend(["-p", port.strip()])
    argv.extend(hedef_argv)

    ek = _ek_argumanlar_satir("7) Ek nmap argümanları (tek satır)", "")
    argv.extend(ek)

    ozet = [
        "Hedef: " + " ".join(hedef_argv),
        f"-p: {port.strip() or 'varsayılan'}",
        f"-sV/A/U: sv={sv} A={agresif} udp={udp}",
    ]
    return _blok_metni("NMAP", ozet, argv), argv


def _sihirbaz_hydra() -> Tuple[str, List[str]]:
    print("\n--- hydra parametreleri ---")
    print("Sadece yetkili brute-force için kullanın.\n")

    t = _prompt_line("Paralel görev (-t)", "4")
    kullanici = _prompt_line("Tek kullanıcı (-l); boş = dosyadan liste (-L)", "")
    usr_list = ""
    if not kullanici.strip():
        usr_list = _prompt_line("Kullanıcı listesi (-L)", "")
        while not usr_list.strip():
            usr_list = _prompt_line("-L dosya yolu", "")

    sifre_tip = _prompt_line("Şifre: dosya yazın 'liste' veya tek için 'tek'", "liste").lower()
    plist = ""
    tek_sifre = ""
    if sifre_tip.startswith("tek"):
        tek_sifre = _prompt_line("Tek şifre (-p)", "")
        while not tek_sifre:
            tek_sifre = _prompt_line("-p şifre", "")
    else:
        plist = _prompt_line("-P şifre listesi dosyası", "")
        while not plist.strip():
            plist = _prompt_line("-P dosya", "")

    srv = _prompt_line("Servis (örn. ssh, ftp, smb, http-post-form)", "ssh")
    host = _prompt_line("Hedef IP veya hostname", "")
    while not host.strip():
        host = _prompt_line("Hedef", "")

    argv: List[str] = ["hydra", "-t", t.strip()]
    if kullanici.strip():
        argv.extend(["-l", kullanici.strip()])
    else:
        argv.extend(["-L", usr_list.strip()])
    if tek_sifre:
        argv.extend(["-p", tek_sifre])
    else:
        argv.extend(["-P", plist.strip()])

    argv.append(f"{srv.strip()}://{host.strip()}")
    ek = _ek_argumanlar_satir("Ek hydra argümanları", "")
    argv.extend(ek)

    return _blok_metni("HYDRA", [f"Hedef: {srv}://{host}"], argv), argv


def _sihirbaz_gobuster() -> Tuple[str, List[str]]:
    print("\n--- gobuster parametreleri ---")
    mod = _prompt_line("Mod (dir / dns / vhost / fuzz)", "dir").lower()
    if mod not in {"dir", "dns", "vhost", "fuzz"}:
        mod = "dir"
    url = _prompt_line("Tam URL (-u)", "")
    while not url.strip():
        url = _prompt_line("-u", "")
    wl = _prompt_line("-w kelime dosyası (Kali ör. .../common.txt)", "")
    while not wl.strip():
        wl = _prompt_line("-w", "")
    th = _prompt_line("--threads", "20")

    argv: List[str] = ["gobuster", mod, "-u", url.strip(), "-w", wl.strip(), "--threads", th.strip()]
    if mod == "dir":
        xt = _prompt_line("-x uzantılar (ör. php,html; boş bırak)", "")
        if xt.strip():
            argv.extend(["-x", xt.replace(" ", "")])
    ek = _ek_argumanlar_satir("Ek gobuster", "")
    argv.extend(ek)

    return _blok_metni("GOBUSTER", [url, wl], argv), argv


def _sihirbaz_ffuf() -> Tuple[str, List[str]]:
    print("\n--- ffuf parametreleri ---")
    u = _prompt_line("URL (içinde FUZZ olmalı, ör. https://site/FUZZ)", "")
    while "FUZZ" not in u.upper():
        u = _prompt_line("URL içinde FUZZ şart:", "")
    w = _prompt_line("-w kelime dosyası", "")
    while not w.strip():
        w = _prompt_line("-w", "")
    xf = _prompt_line("-X metod", "GET")
    fc = _prompt_line('-fc çıkış kod filtresi (ör. "404"; boş bırak)', "")

    argv = ["ffuf", "-u", u.strip(), "-w", w.strip(), "-X", xf.strip().upper()]
    if fc.strip():
        argv.extend(["-fc", fc.strip()])
    argv.extend(_ek_argumanlar_satir("Ek ffuf", ""))
    return _blok_metni("FFUF", [u, w], argv), argv


def _sihirbaz_wfuzz() -> Tuple[str, List[str]]:
    print("\n--- wfuzz parametreleri ---")
    wl_path = _prompt_line("Kelime listesi tam yolu (ör. /usr/share/wordlists/dirb/common.txt)", "")
    while not wl_path.strip():
        wl_path = _prompt_line("Kelime dosyası", "")
    url = _prompt_line("-u URL (FUZZ veya klasik)", "")
    while not url.strip():
        url = _prompt_line("-u", "")

    argv = ["wfuzz", "-c", "-z", f"file,{wl_path.strip()}", "-u", url.strip()]
    hc = _prompt_line("--hc gizlenecek kod (ör. 404; boş)", "")
    if hc.strip():
        argv.extend(["--hc", hc.strip()])
    argv.extend(_ek_argumanlar_satir("Ek wfuzz", ""))
    return _blok_metni("WFUZZ", [wl_path, url], argv), argv


def _sihirbaz_nikto() -> Tuple[str, List[str]]:
    print("\n--- nikto parametreleri ---")
    h = _prompt_line("-h tam URL http(s)://", "")
    while not (h.startswith("http://") or h.startswith("https://")):
        h = _prompt_line("-h (http/https ile)", "")
    tg = _prompt_line("-T tuning (ör. xall; boş)", "")
    argv = ["nikto", "-h", h.strip()]
    if tg.strip():
        argv.extend(["-T", tg.strip()])
    argv.extend(_ek_argumanlar_satir("Ek nikto", ""))
    return _blok_metni("NIKTO", [h], argv), argv


def _sihirbaz_wpscan() -> Tuple[str, List[str]]:
    print("\n--- wpscan parametreleri ---")
    url = _prompt_line("--url", "")
    while not url.strip():
        url = _prompt_line("--url", "")
    api = _prompt_line("--api-token (boş bırakılabilir)", "")
    argv = ["wpscan", "--url", url.strip()]
    if api.strip():
        argv.extend(["--api-token", api.strip()])
    argv.extend(_ek_argumanlar_satir("Ek wpscan", ""))
    return _blok_metni("WPSCAN", [url], argv), argv


def _sihirbaz_masscan() -> Tuple[str, List[str]]:
    print("\n--- masscan parametreleri ---")
    print("Uyarı: Ham paket gönderimi; izin/CAP_NET_RAW gerekebilir.\n")
    hedef = _prompt_line("Hedef / CIDR", "")
    while not hedef.strip():
        hedef = _prompt_line("Hedef", "")
    ports = _prompt_line("-p portlar", "1-1024")
    rate = _prompt_line("--rate (pps)", "100")

    argv = ["masscan", hedef.strip(), "-p", ports.strip(), "--rate", rate.strip()]
    argv.extend(_ek_argumanlar_satir("Ek masscan", ""))
    return _blok_metni("MASSCAN", [hedef, ports, rate], argv), argv


def _sihirbaz_rustscan() -> Tuple[str, List[str]]:
    print("\n--- rustscan parametreleri ---")
    addr = _prompt_line("-a veya --addresses ile hedef(ler)", "")
    while not addr.strip():
        addr = _prompt_line("addresses", "")
    ports = _prompt_line("-p portlar (ör. 443,8080)", "")
    nm = _prompt_line("'--' sonrası nmap argları (tek satır, ör. -sV -Pn)", "-sV -Pn")

    argv = ["rustscan", "-a", addr.strip()]
    if ports.strip():
        argv.extend(["-p", ports.strip()])
    argv.append("--")
    parts = shlex.split(nm.strip(), posix=True) if nm.strip() else ["-sV"]
    argv.extend(parts)

    return _blok_metni("RUSTSCAN", [addr, ports or "(varsayılan portlar)"], argv), argv


def _sihirbaz_enum4linux() -> Tuple[str, List[str]]:
    print("\n--- enum4linux-ng / enum4linux parametreleri ---")
    hedef = _prompt_line("Hedef IP/host", "")
    while not hedef.strip():
        hedef = _prompt_line("Hedef", "")

    if _prompt_line("Komut (enum4linux-ng mi klasik mi?) yazın: ng/kls", "ng").strip().lower() == "ng":
        base = ["enum4linux-ng"]
    else:
        base = ["enum4linux"]

    argv = base + [hedef.strip()]
    argv.extend(shlex.split(_prompt_line("[opsiyonel tüm parametreleri tek satırda]", ""), posix=True))
    extra = _ek_argumanlar_satir("Çift tire vb. daha fazla parametre satırı (boş bırakılabilir)", "")
    argv.extend(extra)
    return _blok_metni("ENUM4LINUX", [hedef, " ".join(base)], argv), argv


def _sihirbaz_theharvester() -> Tuple[str, List[str]]:
    print("\n--- theHarvester parametreleri ---")
    dom = _prompt_line("-d domain", "")
    while not dom.strip():
        dom = _prompt_line("-d", "")
    src = _prompt_line("-b kaynaklar (ör. google, bing veya all)", "all")
    lm = _prompt_line("-l limit (sayı)", "200")

    argv = ["theHarvester", "-d", dom.strip(), "-b", src.strip()]
    argv.extend(["-l", lm.strip()])
    argv.extend(_ek_argumanlar_satir("Ek theHarvester (-f çıktı dosyası vb.)", ""))
    return _blok_metni("THEHARVESTER", [dom, src], argv), argv


def _sihirbaz_bloodhound_python() -> Tuple[str, List[str]]:
    print("\n--- bloodhound-python parametreleri ---")
    print("(Sürüm farkları çok olduğu için tüm parametreleri tek satırda vermeniz daha güvenli.)\n")
    parametre_satir = _prompt_line(
        "Komut parametreleri (ör: -u user -p Pass -dc dc01.lab.local -d lab.local --collectionmethod all)",
        "",
    )
    while not parametre_satir.strip():
        parametre_satir = _prompt_line("Parametre satırı (zorunlu)", "")

    parcalar = shlex.split(parametre_satir.strip(), posix=True)
    argv = ["bloodhound-python"] + parcalar
    ozet = [parametre_satir.strip()[:200]]
    return _blok_metni("BLOODHOUND_PYTHON", ozet, argv), argv


def _sihirbaz_responder() -> Tuple[str, List[str]]:
    print("\n--- Responder parametreleri ---")
    iface = _prompt_line("-I arayüz (örn. eth0)", "eth0")

    argv = ["responder", "-I", iface.strip()]
    ek = _ek_argumanlar_satir("Ek responder (ör. -wFbV); dikkat: ağı etkileyebilir", "")
    argv.extend(ek)
    return _blok_metni("RESPONDER", [iface], argv), argv


def _sihirbaz_evil_winrm() -> Tuple[str, List[str]]:
    print("\n--- evil-winrm parametreleri ---")
    kul = _prompt_line(r"-u kullanıcı (örn. .\Administrator veya DOMAIN\user)", "Administrator")
    parola = _prompt_line("-p şifre (boş olabilir; hash kullanırsanız kendi parametrenizi yazın)", "")
    mod = _prompt_line("Bağlantı türü: IP için `i`, FQDN/hostname için `r` yazın", "i").strip().lower()[:1] or "i"
    host = _prompt_line("IP (mod i) veya FQDN (mod r)", "")
    while not host.strip():
        host = _prompt_line("IP veya host", "")

    argv = ["evil-winrm", "-u", kul.strip()]
    if parola.strip():
        argv.extend(["-p", parola.strip()])
    if mod == "r":
        argv.extend(["-r", host.strip()])
    else:
        argv.extend(["-i", host.strip()])
    argv.extend(_ek_argumanlar_satir("Ek evil-winrm parametreleri (tek satır)", ""))
    ozet_list = ["Hedef tipi:" + (" r " if mod == "r" else " i "), host]
    return _blok_metni("EVIL_WINRM", ozet_list, argv), argv


# Araç adı → sihirbaz (sıra _ALGILATICILAR ile aynı kalmalı)
WIZARD_REGISTRY: Dict[str, WizardFn] = {
    "sqlmap": _sihirbaz_sqlmap,
    "nmap": _sihirbaz_nmap,
    "hydra": _sihirbaz_hydra,
    "gobuster": _sihirbaz_gobuster,
    "ffuf": _sihirbaz_ffuf,
    "wfuzz": _sihirbaz_wfuzz,
    "nikto": _sihirbaz_nikto,
    "wpscan": _sihirbaz_wpscan,
    "masscan": _sihirbaz_masscan,
    "rustscan": _sihirbaz_rustscan,
    "enum4linux": _sihirbaz_enum4linux,
    "theharvester": _sihirbaz_theharvester,
    "bloodhound-python": _sihirbaz_bloodhound_python,
    "responder": _sihirbaz_responder,
    "evil-winrm": _sihirbaz_evil_winrm,
}


def istegi_zenginlestir(istek: str) -> Tuple[str, List[List[str]]]:
    """
    İstekte geçen her kayıtlı araç için sihirbazı çalıştırır.
    Dönüş: (birleştirilmiş metin LLM'e, çıkarılan komut argv listesi listesi).
    """
    araclar = algilanan_araclar(istek)
    if not araclar:
        return istek, []

    print(f"\nAlgılanan araçlar: {', '.join(araclar)}")
    print("(Her biri için Türkçe parametreleri sırayla soruyorum)\n")

    bloklar: List[str] = []
    tum_argv: List[List[str]] = []
    ek_not = (
        "\n[Lütfen yalnızca yukarıdaki araç parametreleriyle plan yapın "
        "(yalnızca izniniz olan ve kapsamdaki / lab hedefler).]\n"
    )

    for arac_id in araclar:
        fn = WIZARD_REGISTRY.get(arac_id)
        if fn is None:
            continue
        blok_i, argv_i = fn()
        bloklar.append(blok_i)
        tum_argv.append(argv_i)

    return istek + "".join(bloklar) + ek_not, tum_argv


def ollama_ayarlarini_sor_interaktif(default_base: str, default_model: str, default_rapor: str) -> Tuple[str, str, str]:
    base = _prompt_line("Ollama sunucu adresi", default_base)
    model = _prompt_line("Model adı", default_model)
    rapor = _prompt_line("Rapor dosya yolu (Markdown)", default_rapor)
    return base, model, rapor


def tam_interaktif_akis() -> Tuple[str, str, str, str]:
    istek = isteginizi_sorun()
    if not istek.strip():
        raise ValueError("İstek boş olamaz.")

    user_request, argv_listesi = istegi_zenginlestir(istek)
    for i, av in enumerate(argv_listesi, 1):
        print(f"\n--- Özet komut {i}/{len(argv_listesi)} ---\n{komut_metni_quote(av)}\n")

    base, model, rapor = ollama_ayarlarini_sor_interaktif(
        "http://localhost:11434", "llama3", "docs/report.md"
    )
    return user_request, base, model, rapor
