#!/usr/bin/env python3
import sys

from agent import LinuxAgent
from llm import OllamaLLM
from tools.shell import ShellPolicy, ShellTool
from wizard import tam_interaktif_akis


def main() -> None:
    try:
        user_request, base, model, rapor = tam_interaktif_akis()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    llm = OllamaLLM(base_url=base, model=model)
    policy = ShellPolicy()
    # sqlmap gibi araçlar uzun sürebilir; saniye cinsinden (15 dk).
    shell = ShellTool(policy=policy, timeout_s=900)

    agent = LinuxAgent(llm=llm, shell=shell, report_path=rapor)
    agent.run(user_request)


if __name__ == "__main__":
    main()
