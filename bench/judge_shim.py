"""OpenAI-compatible /v1/chat/completions endpoint backed by headless Claude Code.

Lets Code Review Bench's judge run on a Claude subscription instead of an API key.
Model "anthropic/claude-opus-4-5-20251101" maps to `claude -p --model claude-opus-4-5-20251101`
with the benchmark's own system prompt, no tools, no user settings, hooks or MCP servers.
Responses are cached on disk by (model, messages) so re-runs are reproducible.

Differences from calling the API directly: temperature can't be set (the API default of
1.0 applies instead of 0.0), and structured-output response_format is ignored.

Usage: python judge_shim.py [--port 8787] [--concurrency 8]
"""
import argparse, hashlib, json, os, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CACHE = Path(__file__).resolve().parent / "judge_cache"
ENV = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE_") and k != "CLAUDECODE"}
sem: threading.Semaphore


def complete(model: str, system: str, user: str) -> str:
    key = hashlib.sha256(json.dumps([model, system, user]).encode()).hexdigest()
    hit = CACHE / key[:2] / f"{key}.json"
    if hit.exists():
        return json.loads(hit.read_text())["content"]
    cmd = ["claude", "-p", "--model", model.split("/")[-1], "--system-prompt", system,
           "--tools", "", "--setting-sources", "", "--strict-mcp-config",
           "--no-session-persistence", "--output-format", "json", "--", user]
    p = None
    with sem:
        for attempt in range(4):
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=ENV, cwd="/tmp")
            try:
                res = next(e for e in json.loads(p.stdout) if e.get("type") == "result")
                if not res.get("is_error"):
                    content = res["result"]
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(5 * 2**attempt)
        else:
            raise RuntimeError(f"claude -p failed: {(p.stderr[-500:] or p.stdout[-500:]) if p else ''}")
    hit.parent.mkdir(parents=True, exist_ok=True)
    hit.write_text(json.dumps({"model": model, "content": content}))
    return content


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        msgs = req["messages"]
        system = "\n\n".join(m["content"] for m in msgs if m["role"] == "system")
        user = "\n\n".join(m["content"] for m in msgs if m["role"] != "system")
        try:
            content = complete(req["model"], system, user)
            body = {"id": "shim", "object": "chat.completion", "model": req["model"],
                    "choices": [{"index": 0, "finish_reason": "stop",
                                 "message": {"role": "assistant", "content": content}}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}
            code = 200
        except Exception as e:  # noqa: BLE001
            body, code = {"error": {"message": str(e)}}, 500
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):  # noqa: A002
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--concurrency", type=int, default=8)
    a = ap.parse_args()
    sem = threading.Semaphore(a.concurrency)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
