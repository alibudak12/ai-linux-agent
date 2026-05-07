import json
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from wizard import istegi_zenginlestir, isteginizi_sorun


def _configure_utf8_io() -> None:
    """
    Konsol/terminal uyumluluğu için mümkünse UTF-8'e zorla.
    Kali Linux'ta genelde gerekmez; Windows terminalinde Türkçe karakterleri iyileştirir.
    """

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


@dataclass
class Step:
    title: str
    rationale: str
    command: List[str]  # argv form, NOT a shell string
    needs_confirmation: bool = False
    risk_reason: Optional[str] = None


@dataclass
class StepResult:
    step: Step
    approved: bool
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0
    skipped_reason: Optional[str] = None


class PlannerLLM:
    """
    Minimal planlayıcı taslağı.
    propose_plan() fonksiyonunu gerçek bir LLM ile (Ollama/API) değiştirebilirsiniz;
    ancak çıktı mutlaka yapılandırılmış kalmalı:
      - Step listesi
      - command alanı bir shell string'i değil argv listesi olmalı
    """

    def propose_plan(self, user_request: str) -> List[Step]:
        req = user_request.lower()
        if "network" in req and ("status" in req or "durum" in req):
            return [
                Step(
                    title="IP adreslerini incele",
                    rationale="Arayüzleri ve atanmış IP adreslerini göstererek bağlantı/IP yapılandırmasını anlamaya yardım eder.",
                    command=["ip", "addr"],
                ),
                Step(
                    title="Dinleyen portları incele",
                    rationale="TCP/UDP üzerinde dinleyen servisleri listeler; hangi servisin hangi porta bağlı olduğunu görmeyi sağlar.",
                    command=["ss", "-tulpn"],
                    needs_confirmation=True,
                    risk_reason="İşlem adlarını/PID bilgilerini gösterebilir; salt-okunur olsa da mahremiyet açısından hassas olabilir.",
                ),
            ]

        return [
            Step(
                title="Sistem bilgisini kontrol et",
                rationale="Herhangi bir işlem yapmadan önce bağlam için çekirdek/OS bilgisini toplar.",
                command=["uname", "-a"],
            ),
            Step(
                title="Mevcut kullanıcıyı kontrol et",
                rationale="Yetki seviyesini (root/non-root) doğrulayarak istenmeyen sistem değişikliklerini önlemeye yardım eder.",
                command=["id"],
            ),
        ]


class CommandPolicy:
    def __init__(self) -> None:
        self.allow_commands = {
            "ip",
            "ss",
            "uname",
            "id",
            "ls",
            "cat",
            "pwd",
            "whoami",
            "date",
            "df",
            "free",
            "ps",
            "top",
            "journalctl",
            "systemctl",
            "apt-cache",
            "dpkg",
            "sqlmap",
        }

        self.hard_block = {"mkfs", "dd"}
        self.confirm_required = {
            "apt",
            "iptables",
            "nft",
            "rm",
            "chmod",
            "chown",
            "useradd",
            "passwd",
            "systemctl",
            "sqlmap",
        }

        self.disallowed_tokens = {"|", "||", "&", "&&", ";", ">", ">>", "<", "<<", "$(", "`"}

    def assess(self, argv: List[str]) -> Tuple[bool, bool, Optional[str]]:
        if not argv:
            return False, False, "Boş komut"

        cmd = argv[0]

        if cmd in {"bash", "sh", "zsh", "fish"}:
            return False, False, "Shell üzerinden çalıştırma engellendi (bash/sh sarmalayıcıları yasak)"

        if cmd in self.hard_block:
            return False, False, f"'{cmd}' komutu yıkıcı olabileceği için politika gereği kesin olarak engellendi"

        if cmd not in self.allow_commands:
            return False, False, f"'{cmd}' komutu izinli liste (allowlist) içinde değil"

        for t in argv:
            if t in self.disallowed_tokens:
                return False, False, f"Yasaklı ifade '{t}' (shell benzeri birleştirmelere izin verilmiyor)"

        if cmd in self.confirm_required:
            return True, True, f"'{cmd}' komutu politika gereği onay istiyor"

        if cmd == "systemctl" and len(argv) >= 2 and argv[1] != "status":
            return True, True, "Düşük riskli kabul edilen tek kullanım 'systemctl status'; diğer eylemler onay gerektirir"

        return True, False, None


class SafeCommandRunner:
    def __init__(self, policy: CommandPolicy, cwd: Optional[Path] = None, timeout_s: int = 20) -> None:
        self.policy = policy
        self.cwd = str(cwd or Path.home())
        self.timeout_s = timeout_s

    def run(self, argv: List[str]) -> Tuple[int, str, str, float]:
        start = time.time()
        try:
            proc = subprocess.run(
                argv,
                cwd=self.cwd,
                shell=False,
                text=True,
                capture_output=True,
                timeout=self.timeout_s,
                env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"},
            )
            dur = time.time() - start
            return proc.returncode, proc.stdout, proc.stderr, dur
        except FileNotFoundError:
            dur = time.time() - start
            cmd = argv[0] if argv else "<empty>"
            return 127, "", f"Komut bulunamadı: {cmd}", dur


class JsonlLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: Dict[str, Any]) -> None:
        event = dict(event)
        event["ts"] = time.time()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


class MarkdownReport:
    def render(self, user_request: str, results: List[StepResult]) -> str:
        lines: List[str] = []
        lines.append("# Yerel AI Ajan Çalıştırma Raporu\n")
        lines.append("## Kullanıcı İsteği\n")
        lines.append(f"{user_request}\n")
        lines.append("## Uygulanan Adımlar\n")

        for i, r in enumerate(results, 1):
            s = r.step
            lines.append(f"### Adım {i}: {s.title}\n")
            lines.append(f"**Bu adım neden var?** {s.rationale}\n")
            if s.needs_confirmation or s.risk_reason:
                rr = s.risk_reason or "Politika gereği onay gerektirir."
                lines.append(f"**Risk notu:** {rr}\n")

            lines.append("**Komut (argv):**\n")
            lines.append("```bash")
            lines.append(" ".join(shlex.quote(x) for x in s.command))
            lines.append("```\n")

            if not r.approved:
                lines.append("**Durum:** Atlandı\n")
                lines.append(f"**Gerekçe:** {r.skipped_reason}\n")
                continue

            lines.append(f"**Çıkış kodu:** {r.exit_code}\n")
            lines.append(f"**Süre:** {r.duration_s:.2f}s\n")

            if r.stdout.strip():
                lines.append("**stdout:**\n```")
                lines.append(r.stdout.rstrip())
                lines.append("```\n")
            if r.stderr.strip():
                lines.append("**stderr:**\n```")
                lines.append(r.stderr.rstrip())
                lines.append("```\n")

            lines.append("**Yorum:**\n")
            lines.append("- Önemli satırları ve kullanıcının hedefi açısından ne anlama geldiklerini özetle.\n")

        lines.append("## Güvenlik Notları\n")
        lines.append("- Komutlar shell olmadan çalıştırıldı (`shell=False`).\n")
        lines.append("- İzinli liste (allowlist) dışındaki araçlar engellendi.\n")
        lines.append("- Politika tarafından riskli işaretlenen komutlar için kullanıcı onayı istendi.\n")
        lines.append("- Her adım olay günlüğüne yazıldı (append-only JSONL).\n")

        return "\n".join(lines)


class Agent:
    def __init__(self, planner: PlannerLLM, policy: CommandPolicy, runner: SafeCommandRunner, logger: JsonlLogger):
        self.planner = planner
        self.policy = policy
        self.runner = runner
        self.logger = logger
        self.reporter = MarkdownReport()

    def handle(self, user_request: str, approvals: Dict[int, bool]) -> str:
        plan = self.planner.propose_plan(user_request)

        self.logger.log({"type": "user_request", "user_request": user_request})
        self.logger.log({"type": "plan", "plan": [asdict(s) for s in plan]})

        results: List[StepResult] = []

        for idx, step in enumerate(plan, 1):
            allowed, needs_ok, reason = self.policy.assess(step.command)

            if not allowed:
                r = StepResult(step=step, approved=False, skipped_reason=reason)
                results.append(r)
                self.logger.log({"type": "step_blocked", "step_index": idx, "reason": reason, "step": asdict(step)})
                continue

            approved = approvals.get(idx, not needs_ok)
            if not approved:
                r = StepResult(step=step, approved=False, skipped_reason="User did not approve this step")
                results.append(r)
                self.logger.log({"type": "step_skipped", "step_index": idx, "reason": r.skipped_reason, "step": asdict(step)})
                continue

            self.logger.log({"type": "step_execute", "step_index": idx, "argv": step.command})

            try:
                code, out, err, dur = self.runner.run(step.command)
                r = StepResult(step=step, approved=True, exit_code=code, stdout=out, stderr=err, duration_s=dur)
                results.append(r)
                self.logger.log({"type": "step_result", "step_index": idx, "exit_code": code, "duration_s": dur})
            except subprocess.TimeoutExpired:
                r = StepResult(
                    step=step,
                    approved=True,
                    exit_code=124,
                    stderr=f"Zaman aşımı: {self.runner.timeout_s}s",
                    duration_s=float(self.runner.timeout_s),
                )
                results.append(r)
                self.logger.log({"type": "step_timeout", "step_index": idx, "timeout_s": self.runner.timeout_s})

        md = self.reporter.render(user_request, results)
        self.logger.log({"type": "report_generated", "length": len(md)})
        return md


def _prompt_yes_no(prompt: str) -> bool:
    while True:
        ans = input(prompt).strip().lower()
        if ans in {"y", "yes", "e", "evet"}:
            return True
        if ans in {"n", "no", "h", "hayır", "hayir"}:
            return False
        print("Lütfen evet/hayır olarak yanıtlayın (e/h).")


def main() -> None:
    _configure_utf8_io()
    planner = PlannerLLM()
    policy = CommandPolicy()
    runner = SafeCommandRunner(policy=policy, timeout_s=900)
    logger = JsonlLogger(Path("./agent_logs/events.jsonl"))
    agent = Agent(planner, policy, runner, logger)

    istek_ham = isteginizi_sorun()
    if not istek_ham.strip():
        print("İstek boş olamaz.")
        sys.exit(2)

    user_request_enriched, sqlmap_argv = istegi_zenginlestir(istek_ham)

    if sqlmap_argv is not None:
        plan = [
            Step(
                title="sqlmap ile test",
                rationale=(
                    "Kullanıcının girdiği hedef URL ve parametrelere göre SQL enjeksiyon kontrolüdür. "
                    "Yalnızca izin verilen sistemler veya lab ortamlarında kullanın."
                ),
                command=sqlmap_argv,
                needs_confirmation=True,
                risk_reason=(
                    "sqlmap hedefe istek gönderir ve ağ/sunucu yükü oluşturabilir; "
                    "yalnızca yetkilendirilmiş testlerde çalıştırın."
                ),
            ),
        ]
    else:
        plan = planner.propose_plan(user_request_enriched)

    user_request = user_request_enriched

    print("\nÖnerilen plan (henüz hiçbir şey çalıştırılmadı):")
    approvals: Dict[int, bool] = {}

    for idx, step in enumerate(plan, 1):
        allowed, needs_ok, reason = policy.assess(step.command)
        cmd_str = " ".join(shlex.quote(x) for x in step.command)

        print(f"\nAdım {idx}: {step.title}")
        print(f"  Neden: {step.rationale}")
        print(f"  Komut: {cmd_str}")

        if not allowed:
            print(f"  ENGELLENDİ: {reason}")
            approvals[idx] = False
            continue

        if needs_ok or step.needs_confirmation:
            print(f"  Onay gerekiyor: {reason or step.risk_reason or 'politika'}")
            approvals[idx] = _prompt_yes_no(f"Adım {idx} onaylansın mı? (e/h): ")
        else:
            approvals[idx] = True

    report = agent.handle(user_request, approvals)
    Path("./agent_report.md").write_text(report, encoding="utf-8")
    print("\nTamamlandı. `./agent_report.md` ve `./agent_logs/events.jsonl` oluşturuldu.")


if __name__ == "__main__":
    main()

