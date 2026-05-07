import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm import OllamaLLM
from tools.shell import CommandResult, ShellTool


@dataclass
class PlanStep:
    title: str
    explanation_before: str
    command: Optional[str] = None  # None = sadece açıklama/özet adımı


def _extract_json_object(text: str) -> Dict[str, Any]:
    """
    Model bazen etrafına metin ekleyebilir; ilk { ... } bloğunu yakalamaya çalışır.
    """
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if not m:
        raise ValueError(f"Model JSON döndürmedi:\n{text}")
    return json.loads(m.group(0))


class MarkdownReportWriter:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, content: str) -> None:
        self.path.write_text(content, encoding="utf-8")


class LinuxAgent:
    def __init__(self, llm: OllamaLLM, shell: ShellTool, report_path: str = "docs/report.md") -> None:
        self.llm = llm
        self.shell = shell
        self.report = MarkdownReportWriter(report_path)

    def plan(self, user_request: str) -> List[PlanStep]:
        system = (
            "Sen Kali Linux üzerinde çalışan bir AI Linux asistanısın.\n"
            "Görev: Kullanıcının isteğini adım adım bir plana çevir.\n"
            "Kurallar:\n"
            "- SADECE geçerli JSON döndür (başka hiçbir metin yazma).\n"
            "- Her adımda title ve explanation_before alanı olmalı.\n"
            "- Komut gerekiyorsa command alanı tek bir Linux komut satırı string'i olmalı.\n"
            "- Komutları mümkün olduğunca salt-okunur ve güvenli seç.\n"
            "- rm -rf, mkfs, shutdown, reboot gibi yıkıcı komutlar ÖNERME.\n"
            "JSON şeması:\n"
            '{ "steps": [ { "title": "...", "explanation_before": "...", "command": "..." } ] }\n'
        )

        prompt = f"Kullanıcı isteği: {user_request}\nPlanı üret."
        raw = self.llm.generate(prompt, system=system)
        data = _extract_json_object(raw)

        steps_raw = data.get("steps")
        if not isinstance(steps_raw, list) or not steps_raw:
            raise RuntimeError(f"Plan boş veya geçersiz: {raw}")

        steps: List[PlanStep] = []
        for i, s in enumerate(steps_raw, 1):
            if not isinstance(s, dict):
                raise RuntimeError(f"Adım formatı hatalı (#{i}): {s}")
            title = str(s.get("title") or "").strip()
            exp = str(s.get("explanation_before") or "").strip()
            cmd = s.get("command")
            cmd_str = str(cmd).strip() if cmd is not None and str(cmd).strip() else None
            if not title or not exp:
                raise RuntimeError(f"Adım alanları eksik (#{i}): {s}")
            steps.append(PlanStep(title=title, explanation_before=exp, command=cmd_str))

        return steps

    def explain_result(self, user_request: str, step: PlanStep, result: CommandResult) -> str:
        system = (
            "Sen bir Linux öğretmen asistanısın.\n"
            "Kullanıcıya kısa, anlaşılır ve pratik bir açıklama yap.\n"
            "Çıktıyı olduğu gibi tekrar etme; önemli noktaları yorumla.\n"
            "Türkçe yaz.\n"
        )

        prompt = (
            f"Kullanıcı isteği: {user_request}\n"
            f"Adım: {step.title}\n"
            f"Komut: {' '.join(result.argv)}\n"
            f"Çıkış kodu: {result.exit_code}\n"
            f"stdout:\n{result.stdout[:4000]}\n"
            f"stderr:\n{result.stderr[:4000]}\n"
            "Bu adımın sonucunu kullanıcı için yorumla (maks 6 madde)."
        )
        return self.llm.generate(prompt, system=system).strip()

    def _prompt_confirm(self, title: str, reason: str, command: str) -> bool:
        print("\n---")
        print(f"Onay gerekiyor: {title}")
        print(f"Gerekçe: {reason}")
        print(f"Komut: {command}")
        while True:
            ans = input("Çalıştırılsın mı? (e/h): ").strip().lower()
            if ans in {"e", "evet", "y", "yes"}:
                return True
            if ans in {"h", "hayır", "hayir", "n", "no"}:
                return False
            print("Lütfen e/h ile yanıtlayın.")

    def run(self, user_request: str) -> None:
        # 1) Plan
        steps = self.plan(user_request)

        # 2) Uygula + raporla
        started = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        md: List[str] = []
        md.append("# AI Linux Ajan Raporu\n")
        md.append("## Kullanıcı İsteği\n")
        md.append(f"{user_request}\n")
        md.append("## Zaman\n")
        md.append(f"- Başlangıç: {started}\n")
        md.append("## Adımlar\n")

        print("Plan oluşturuldu. Adımlar yürütülmeden önce her adım açıklanacak.\n")

        for idx, step in enumerate(steps, 1):
            md.append(f"### Adım {idx}: {step.title}\n")
            md.append(f"**Çalıştırmadan önce açıklama:** {step.explanation_before}\n")

            print(f"\nAdım {idx}: {step.title}")
            print(step.explanation_before)

            if not step.command:
                md.append("**Komut:** (yok)\n")
                md.append("**Durum:** Sadece açıklama adımı (komut çalıştırılmadı)\n")
                continue

            md.append("**Komut:**\n")
            md.append("```bash")
            md.append(step.command)
            md.append("```\n")

            argv = self.shell.policy.parse(step.command)
            decision, reason = self.shell.policy.assess(argv)

            if decision == "block":
                md.append("**Durum:** Engellendi\n")
                md.append(f"**Gerekçe:** {reason}\n")
                print(f"ENGELLENDİ: {reason}")
                continue

            if decision == "confirm":
                approved = self._prompt_confirm(step.title, reason or "riskli komut", step.command)
                md.append("**Onay:** " + ("Evet" if approved else "Hayır") + "\n")
                if not approved:
                    md.append("**Durum:** Atlandı\n")
                    md.append("**Gerekçe:** Kullanıcı onaylamadı\n")
                    print("Atlandı (kullanıcı onaylamadı).")
                    continue

            # Çalıştır
            result = self.shell.run_argv(argv)

            md.append(f"**Çıkış kodu:** {result.exit_code}\n")
            md.append(f"**Süre:** {result.duration_s:.2f}s\n")

            if result.stdout.strip():
                md.append("**stdout:**\n```")
                md.append(result.stdout.rstrip()[:12000])
                md.append("```\n")
            if result.stderr.strip():
                md.append("**stderr:**\n```")
                md.append(result.stderr.rstrip()[:12000])
                md.append("```\n")

            # 3) Sonuçları açıkla (LLM)
            interpretation = self.explain_result(user_request, step, result)
            md.append("**Açıklama / Yorum:**\n")
            md.append(interpretation + "\n")

            print("\nSonuç özeti:")
            print(interpretation)

        md.append("## Notlar\n")
        md.append("- Bu rapor, her adımın açıklamasını, kullanılan komutları ve çıktıları içerir.\n")
        md.append("- Tehlikeli komutlar politika tarafından engellenir; riskli komutlar için onay istenir.\n")

        self.report.write("\n".join(md))
        print(f"\nRapor yazıldı: {os.path.abspath(str(self.report.path))}")


def _usage_exit() -> None:
    raise SystemExit('Kullanım: python3 main.py "isteğiniz"  (veya)  python3 agent.py "isteğiniz"')


if __name__ == "__main__":
    # Kolaylık: agent.py tek başına da çalıştırılabilsin.
    import sys

    if len(sys.argv) < 2:
        _usage_exit()

    user_request = " ".join(sys.argv[1:]).strip()
    if not user_request:
        _usage_exit()

    llm = OllamaLLM(base_url="http://localhost:11434", model="llama3")
    from tools.shell import ShellPolicy

    shell = ShellTool(policy=ShellPolicy())
    LinuxAgent(llm=llm, shell=shell, report_path="docs/report.md").run(user_request)

