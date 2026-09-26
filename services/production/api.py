"""Loopback-bound HTTP API for the local production worker."""
from __future__ import annotations
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from services.idea_bank.provider import MockTextAIProvider
from services.idea_bank.store import IdeaBank
from .pipeline import ProductionPipeline

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("PIPELINE_DATA_PATH", str(ROOT / "data")))
BANK = IdeaBank(os.environ.get("IDEA_DB_PATH", str(DATA / "ideas" / "ideas.db")), MockTextAIProvider())
PIPELINE = ProductionPipeline(BANK, DATA)
PORT = int(os.environ.get("PIPELINE_API_PORT", "8091"))

class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, data: object) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
    def _body(self) -> dict:
        length = min(int(self.headers.get("Content-Length", "0")), 65536)
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
    def do_GET(self) -> None:
        if self.path == "/healthz":
            subtitle_provider = "existing-subtitle-backend" if os.environ.get("SUBTITLE_WORKER_URL", "").strip() else "local-exact-script"
            self._send(200, {"status": "ok", "providers": {
                "media": PIPELINE.media.provider_name if hasattr(PIPELINE.media, "provider_name") else "mock", "tts": os.environ.get("TTS_PROVIDER", "qwen3-tts-local"),
                "qwen_tts_reference_configured": (
                    Path(os.environ.get("QWEN_TTS_REFERENCE_AUDIO", "/app/data/models/voice-reference/Audio_Ejemplo.mp3")).is_file()
                    and Path(os.environ.get("QWEN_TTS_REFERENCE_TEXT_FILE", "/app/data/models/voice-reference/Audio_Ejemplo.txt")).is_file()),
                "fish_audio_key_configured": bool(os.environ.get("FISH_AUDIO_API_KEY", "").strip()),
                "narration_writer": "ollama-local",
                "narration_model": os.environ.get("NARRATION_MODEL", "qwen3:4b"),
                "subtitles": subtitle_provider}})
            return
        match = re.fullmatch(r"/api/jobs/(CONTENT-[0-9]{6})", self.path)
        if match:
            job_id = match.group(1)
            context = BANK.get_job_context(job_id)
            if context is None: self._send(404, {"error": "job_not_found"})
            else: self._send(200, {"job": context[0], "idea": context[1], "events": BANK.job_events(job_id)})
            return
        self._send(404, {"error": "not_found"})
    def do_POST(self) -> None:
        try:
            body = self._body()
            if self.path == "/api/production/process":
                jobs = PIPELINE.process_pending(int(body.get("limit", 1)))
                self._send(200, {"processed": len(jobs), "jobs": jobs})
                return
            match = re.fullmatch(r"/api/jobs/(CONTENT-[0-9]{6})/(resume|publish-dry-run|rebuild-narration)", self.path)
            if match:
                job_id, action = match.groups()
                context = BANK.get_job_context(job_id)
                if context is None:
                    self._send(404, {"error": "job_not_found"})
                    return
                if action == "resume":
                    if context[0]["estado"] in {"WAITING_PROVIDER", "WAITING_MANUAL_ACTION"}:
                        BANK.set_job_retry(job_id, context[0].get("resume_state") or "MEDIA_QUEUED")
                    self._send(200, PIPELINE.process_job(job_id))
                elif action == "rebuild-narration":
                    self._send(200, PIPELINE.rebuild_narration(job_id))
                else:
                    self._send(200, {"dry_run": True, "platforms": PIPELINE.dry_run_publish(job_id)})
                return
            self._send(404, {"error": "not_found"})
        except KeyError as exc:
            self._send(404, {"error": str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:
            self.log_error("pipeline request failed: %s", exc)
            self._send(500, {"error": "pipeline_error", "detail": str(exc)})
    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}")

def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Production worker listening on {PORT}; exposure is controlled by Compose.")
    server.serve_forever()

if __name__ == "__main__":
    main()
