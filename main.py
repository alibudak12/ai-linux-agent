#!/usr/bin/env python3
import sys

from agent import LinuxAgent
from llm import OllamaLLM
from tools.shell import ShellPolicy, ShellTool


def _usage_exit() -> None:
    print('Kullanım: ai-agent "isteğiniz"', file=sys.stderr)
    print('İpucu: Parametre vermeden çalıştırırsanız interaktif sorar.', file=sys.stderr)
    sys.exit(2)


def _prompt(prompt: str, default: str) -> str:
    s = input(f"{prompt} [{default}]: ").strip()
    return s if s else default


def main() -> None:
    # Parametre verilmediyse interaktif mod.
    if len(sys.argv) < 2:
        print("Interaktif mod: Parametreleri sırayla cevaplayın.\n")
        user_request = _prompt("1) İstek (ne yapmak istiyorsunuz?)", "sistemi analiz et")
        base_url = _prompt("2) Ollama adresi", "http://localhost:11434")
        model = _prompt("3) Model adı", "llama3")
        report_path = _prompt("4) Rapor yolu", "docs/report.md")
    else:
        user_request = " ".join(sys.argv[1:]).strip()
        if not user_request:
            _usage_exit()
        base_url = "http://localhost:11434"
        model = "llama3"
        report_path = "docs/report.md"

    llm = OllamaLLM(base_url=base_url, model=model)
    policy = ShellPolicy()
    shell = ShellTool(policy=policy)

    agent = LinuxAgent(llm=llm, shell=shell, report_path=report_path)

    # Çalışma sırasında adım adım açıklar, gerekirse onay ister, raporu yazar.
    agent.run(user_request)


if __name__ == "__main__":
    main()

