"""Local-only HTTP API and lightweight approval dashboard."""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .provider import MockTextAIProvider
from .planner import LocalPlanner
from .store import IdeaBank

ROOT = Path(__file__).resolve().parents[2]
PORT = int(os.environ.get("IDEA_API_PORT", "8090"))
MIN_PENDING = int(os.environ.get("IDEA_MIN_PENDING", "30"))
BATCH_SIZE = int(os.environ.get("IDEA_BATCH_SIZE", "30"))
CATEGORIES = [
    "Fusiones de Stands", "Evoluciones/Requiem", "What If",
    "Enfrentamientos", "Poderes hipotéticos", "Conceptos originales",
]
BANK = IdeaBank(os.environ.get("IDEA_DB_PATH", str(ROOT / "data/ideas/ideas.db")), MockTextAIProvider())
PLANNER = LocalPlanner(BANK, os.environ.get("IDEA_JOBS_PATH", str(ROOT / "data/jobs")))


class Handler(BaseHTTPRequestHandler):
    server_version = "PipelineIdeaBank/1.0"

    def _send(self, status: int, payload: object, content_type: str = "application/json; charset=utf-8") -> None:
        if content_type.startswith("application/json"):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        else:
            body = str(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = min(int(self.headers.get("Content-Length", "0")), 65536)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._send(200, {"status": "ok"})
        elif parsed.path == "/":
            ui = Path(__file__).with_name("ui.html").read_text(encoding="utf-8")
            self._send(200, ui, "text/html; charset=utf-8")
        elif parsed.path == "/api/ideas":
            state = parse_qs(parsed.query).get("state", [None])[0]
            self._send(200, {"ideas": BANK.all_ideas(state)})
        elif parsed.path == "/api/ideas/pending-count":
            self._send(200, {"count": BANK.count_pending(), "minimum": MIN_PENDING})
        elif re.fullmatch(r"/api/jobs/CONTENT-[0-9]{6}", parsed.path):
            content_id = parsed.path.rsplit("/", 1)[-1]
            context = BANK.get_job_context(content_id)
            if context is None:
                self._send(404, {"error": f"No existe el trabajo {content_id}"})
            else:
                job, idea = context
                self._send(200, {"job": job, "idea": idea})
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            body = self._body()
            if parsed.path == "/api/ideas/generate":
                count = min(100, max(1, int(body.get("count", BATCH_SIZE))))
                created = BANK.generate_ideas(count, body.get("categories", CATEGORIES))
                self._send(201, {"created": len(created), "ideas": created})
            elif parsed.path == "/api/ideas/replenish":
                pending = BANK.count_pending()
                if pending >= MIN_PENDING:
                    self._send(200, {"created": 0, "pending": pending, "minimum": MIN_PENDING, "reason": "threshold_met"})
                    return
                created = BANK.generate_ideas(BATCH_SIZE, CATEGORIES)
                self._send(200, {"created": len(created), "pending": BANK.count_pending(), "minimum": MIN_PENDING, "ideas": created})
            elif parsed.path == "/api/approvals/process":
                jobs = BANK.process_approvals()
                self._send(200, {"processed": len(jobs), "jobs": jobs})
            elif parsed.path == "/api/planner/process":
                results = PLANNER.process_pending(int(body.get("limit", 20)))
                self._send(200, {"processed": len(results), "jobs": results})
            elif re.fullmatch(r"/api/jobs/CONTENT-[0-9]{6}/plan", parsed.path):
                content_id = parsed.path.split("/")[-2]
                result = PLANNER.plan_job(content_id)
                self._send(200, result)
            else:
                match = re.fullmatch(r"/api/ideas/(IDEA-[0-9]{6})/(approve|reject)", parsed.path)
                if not match:
                    self._send(404, {"error": "not_found"})
                    return
                idea_id, action = match.groups()
                result = BANK.request_approval(idea_id) if action == "approve" else BANK.reject(idea_id)
                self._send(200, result)
        except KeyError as exc:
            self._send(404, {"error": str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:
            self.log_error("request failed: %s", exc)
            self._send(500, {"error": "internal_error"})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Idea bank API listening on port {PORT}; host exposure is controlled by Docker Compose.")
    server.serve_forever()


if __name__ == "__main__":
    main()
