#!/usr/bin/env python3
import sys

from agent import LinuxAgent
from llm import OllamaLLM
from tools.shell import ShellPolicy, ShellTool


def _usage_exit() -> None:
    print('Kullanım: ai-agent "isteğiniz"', file=sys.stderr)
    sys.exit(2)


def main() -> None:
    if len(sys.argv) < 2:
        _usage_exit()

    user_request = " ".join(sys.argv[1:]).strip()
    if not user_request:
        _usage_exit()

    llm = OllamaLLM(base_url="http://localhost:11434", model="llama3")
    policy = ShellPolicy()
    shell = ShellTool(policy=policy)

    agent = LinuxAgent(llm=llm, shell=shell, report_path="docs/report.md")

    # Çalışma sırasında adım adım açıklar, gerekirse onay ister, raporu yazar.
    agent.run(user_request)


if __name__ == "__main__":
    main()

