import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class CommandResult:
    argv: List[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float


class ShellPolicy:
    """
    Minimal güvenlik politikası:
    - Tehlikeli komutları engeller (rm -rf, mkfs, shutdown, reboot)
    - Bazı komutları 'riskli' sayar ve kullanıcı onayı ister
    """

    def __init__(self) -> None:
        self.block_commands = {"mkfs", "shutdown", "reboot"}
        self.risky_commands = {
            "rm",
            "apt",
            "apt-get",
            "dpkg",
            "systemctl",
            "service",
            "iptables",
            "nft",
            "chmod",
            "chown",
            "useradd",
            "usermod",
            "passwd",
            "dd",
            "mount",
            "umount",
            "sqlmap",
            "nmap",
            "hydra",
            "gobuster",
            "ffuf",
            "wfuzz",
            "nikto",
            "wpscan",
            "masscan",
            "rustscan",
            "enum4linux",
            "enum4linux-ng",
            "theHarvester",
            "theharvester",
            "bloodhound-python",
            "responder",
            "evil-winrm",
        }

        # Shell benzeri birleştirmeler bu sürümde desteklenmiyor.
        self.disallowed_tokens = {"|", "||", "&", "&&", ";", ">", ">>", "<", "<<", "$(", "`"}

    def parse(self, command: str) -> List[str]:
        # Kali/Linux için posix=True
        return shlex.split(command, posix=True)

    def assess(self, argv: List[str]) -> Tuple[str, Optional[str]]:
        """
        Returns:
          - "allow" | "confirm" | "block"
          - reason (optional)
        """
        if not argv:
            return "block", "Boş komut"

        for t in argv:
            if t in self.disallowed_tokens:
                return "block", f"Yasaklı ifade '{t}' (pipe/redirect/komut zinciri desteklenmiyor)"

        cmd = argv[0]

        if cmd in self.block_commands:
            return "block", f"'{cmd}' komutu politika gereği engellendi"

        # Özel blok: rm -rf
        if cmd == "rm" and any(a in {"-rf", "-fr", "--no-preserve-root"} for a in argv[1:]):
            return "block", "rm -rf (ve benzeri) politika gereği engellendi"

        if cmd in self.risky_commands:
            return "confirm", f"'{cmd}' komutu riskli kabul ediliyor ve onay gerektiriyor"

        # sudo her zaman onay gerektirsin
        if cmd == "sudo":
            return "confirm", "sudo kullanımı onay gerektiriyor"

        return "allow", None


class ShellTool:
    def __init__(self, policy: ShellPolicy, cwd: Optional[str] = None, timeout_s: int = 30) -> None:
        self.policy = policy
        self.cwd = cwd
        self.timeout_s = timeout_s

    def run_argv(self, argv: List[str]) -> CommandResult:
        start = time.time()
        try:
            proc = subprocess.run(
                argv,
                cwd=self.cwd,
                shell=False,
                text=True,
                capture_output=True,
                timeout=self.timeout_s,
                env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
            )
            dur = time.time() - start
            return CommandResult(argv=argv, exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr, duration_s=dur)
        except FileNotFoundError:
            dur = time.time() - start
            return CommandResult(argv=argv, exit_code=127, stdout="", stderr=f"Komut bulunamadı: {argv[0]}", duration_s=dur)
        except subprocess.TimeoutExpired:
            dur = time.time() - start
            return CommandResult(argv=argv, exit_code=124, stdout="", stderr=f"Zaman aşımı: {self.timeout_s}s", duration_s=dur)

