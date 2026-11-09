import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCAL_DIR = ROOT / ".local-model"
SERVER_EXE = LOCAL_DIR / "runtime" / "bin" / "llama-server.exe"
MODELS = {
    "1.7b": LOCAL_DIR / "weights" / "Qwen3-1.7B-Q8_0.gguf",
    "8b": LOCAL_DIR / "weights" / "Qwen3-8B-Q4_K_M.gguf",
}
PORT = 18999
THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


class ChatClient:
    def __init__(self, base_url, model, api_key=None, timeout=900):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, messages, max_tokens=450, temperature=0.2):
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        seconds = time.perf_counter() - started
        message = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        return {
            "text": THINK_BLOCK.sub("", message).strip(),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "seconds": round(seconds, 1),
        }

    def start(self):
        return None

    def stop(self):
        return None


class LocalLlamaServer(ChatClient):
    def __init__(self, model="1.7b", port=PORT, context=4096, threads=6):
        self.model_path = MODELS[model]
        self.port = port
        self.context = context
        self.threads = threads
        self.process = None
        super().__init__(f"http://127.0.0.1:{port}/v1", self.model_path.stem)

    def healthy(self):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=3) as response:
                return response.status == 200
        except (urllib.error.URLError, OSError):
            return False

    def start(self, wait_seconds=240):
        if self.healthy():
            return
        log_dir = ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        log = (log_dir / "server.log").open("wb")
        command = [
            str(SERVER_EXE), "-m", str(self.model_path), "--host", "127.0.0.1",
            "--port", str(self.port), "-c", str(self.context), "-t", str(self.threads),
            "--parallel", "1",
        ]
        self.process = subprocess.Popen(
            command, stdout=log, stderr=log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("llama-server exited, see logs/server.log")
            if self.healthy():
                return
            time.sleep(1)
        raise TimeoutError("llama-server did not become ready")

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None


def make_llm(model="1.7b"):
    if os.environ.get("RAG_LLM", "local") == "openai":
        return ChatClient(
            os.environ["LLM_BASE_URL"], os.environ["LLM_MODEL"], os.environ.get("LLM_API_KEY")
        )
    return LocalLlamaServer(model)
