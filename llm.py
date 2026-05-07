import json
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class OllamaLLM:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3", timeout_s: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def generate(self, prompt: str, *, system: Optional[str] = None) -> str:
        """
        Ollama /api/generate kullanır. stream=False ile tek parça yanıt alır.
        """
        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {"model": self.model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
            raise RuntimeError(f"Ollama HTTP hatası: {e.code} {e.reason}\n{msg}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama erişilemedi ({url}): {e}") from e

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Ollama JSON döndürmedi:\n{raw}") from e

        return (data.get("response") or "").strip()

