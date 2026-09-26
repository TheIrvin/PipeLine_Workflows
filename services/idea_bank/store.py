"""Persistent SQLite idea bank with separate approval and watcher transitions."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .provider import TextAIProvider, is_duplicate, normalize_name

SHEET_STATES = {"PENDIENTE", "APROBADA", "RECHAZADA", "EN_PRODUCCION", "LISTA", "PUBLICADA"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class IdeaBank:
    def __init__(self, db_path: str | Path, provider: TextAIProvider):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.provider = provider
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS ideas (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE,
                    idea TEXT NOT NULL,
                    normalized_idea TEXT NOT NULL UNIQUE,
                    tipo TEXT NOT NULL,
                    resumen TEXT NOT NULL DEFAULT '',
                    duracion_objetivo INTEGER NOT NULL,
                    prioridad INTEGER NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'PENDIENTE',
                    fecha_creacion TEXT NOT NULL,
                    fecha_aprobacion TEXT,
                    job_id TEXT UNIQUE,
                    notas TEXT NOT NULL DEFAULT '',
                    titulo_final TEXT NOT NULL DEFAULT '',
                    fecha_publicacion TEXT
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE NOT NULL,
                    idea_id TEXT UNIQUE NOT NULL REFERENCES ideas(id),
                    estado TEXT NOT NULL,
                    fecha_creacion TEXT NOT NULL
                );
            """)

    def all_ideas(self, state: str | None = None) -> list[dict]:
        with self._connect() as conn:
            if state:
                rows = conn.execute("SELECT * FROM ideas WHERE estado = ? ORDER BY seq", (state.upper(),)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM ideas ORDER BY seq").fetchall()
        return [dict(row) for row in rows]

    def count_pending(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM ideas WHERE estado = 'PENDIENTE'").fetchone()
        return int(row["n"])

    def generate_ideas(self, count: int, categories: Sequence[str]) -> list[dict]:
        existing = self.all_ideas()
        candidates = self.provider.generate_ideas(count, existing, categories)
        created = []
        with self._connect() as conn:
            for candidate in candidates:
                title = str(candidate.get("idea", "")).strip()
                if not title or is_duplicate(title, [str(row["idea"]) for row in existing + created]):
                    continue
                now = utc_now()
                cur = conn.execute("""
                    INSERT OR IGNORE INTO ideas
                    (idea, normalized_idea, tipo, resumen, duracion_objetivo, prioridad, estado, fecha_creacion)
                    VALUES (?, ?, ?, ?, ?, ?, 'PENDIENTE', ?)
                """, (
                    title,
                    normalize_name(title),
                    str(candidate.get("tipo", "Conceptos originales")),
                    str(candidate.get("resumen", "")),
                    max(1, int(candidate.get("duracion_objetivo", 45))),
                    min(10, max(1, int(candidate.get("prioridad", 5)))),
                    now,
                ))
                if cur.rowcount:
                    seq = int(cur.lastrowid)
                    idea_id = f"IDEA-{seq:06d}"
                    conn.execute("UPDATE ideas SET id = ? WHERE seq = ?", (idea_id, seq))
                    created.append({"id": idea_id, **candidate, "estado": "PENDIENTE", "fecha_creacion": now})
        return created

    def get_idea(self, idea_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone()
        return dict(row) if row else None

    def request_approval(self, idea_id: str) -> dict:
        """Record the user's local approval; the n8n watcher creates the job."""
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone()
            if row is None:
                raise KeyError(f"No existe la idea {idea_id}")
            if row["job_id"]:
                return dict(row)
            if row["estado"] == "APROBADA":
                return dict(row)
            if row["estado"] != "PENDIENTE":
                raise ValueError(f"Solo se aprueban ideas PENDIENTE; {idea_id} está {row['estado']}")
            conn.execute("UPDATE ideas SET estado = 'APROBADA', fecha_aprobacion = ? WHERE id = ?", (utc_now(), idea_id))
            return dict(conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone())

    def process_approvals(self) -> list[dict]:
        """Atomically convert approved ideas into one IDEA_APPROVED job each."""
        jobs = []
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute("SELECT * FROM ideas WHERE estado = 'APROBADA' AND job_id IS NULL ORDER BY seq").fetchall()
            next_seq = int(conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 AS n FROM jobs").fetchone()["n"])
            for offset, row in enumerate(rows):
                now = utc_now()
                job_id = f"CONTENT-{next_seq + offset:06d}"
                conn.execute("UPDATE ideas SET estado = 'EN_PRODUCCION', job_id = ? WHERE id = ?", (job_id, row["id"]))
                conn.execute("INSERT INTO jobs(job_id, idea_id, estado, fecha_creacion) VALUES (?, ?, 'IDEA_APPROVED', ?)", (job_id, row["id"], now))
                jobs.append(dict(conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()))
        return jobs

    def get_job_context(self, job_id: str) -> tuple[dict, dict] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT j.job_id, j.idea_id, j.estado, j.fecha_creacion, "
                "i.idea, i.tipo, i.resumen, i.duracion_objetivo, i.prioridad "
                "FROM jobs j JOIN ideas i ON i.id = j.idea_id WHERE j.job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        job = {key: data[key] for key in ("job_id", "idea_id", "estado", "fecha_creacion")}
        idea = {
            "id": data["idea_id"], "idea": data["idea"], "tipo": data["tipo"],
            "resumen": data["resumen"], "duracion_objetivo": data["duracion_objetivo"],
            "prioridad": data["prioridad"],
        }
        return job, idea

    def jobs_by_state(self, state: str, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE estado = ? ORDER BY seq LIMIT ?",
                (state.strip().upper(), max(1, min(100, int(limit)))),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_job_state(self, job_id: str, state: str) -> dict:
        state = state.strip().upper()
        allowed = {"IDEA_APPROVED", "SCRIPT_READY", "MEDIA_QUEUED"}
        if state not in allowed:
            raise ValueError(f"Estado de job no válido: {state}")
        transitions = {
            "IDEA_APPROVED": {"SCRIPT_READY"},
            "SCRIPT_READY": {"MEDIA_QUEUED"},
            "MEDIA_QUEUED": set(),
        }
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(f"No existe el trabajo {job_id}")
            current = row["estado"]
            if current != state and state not in transitions.get(current, set()):
                raise ValueError(f"Transición no permitida: {current} -> {state}")
            if current != state:
                conn.execute("UPDATE jobs SET estado = ? WHERE job_id = ?", (state, job_id))
            return dict(conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone())

    def approve(self, idea_id: str) -> dict:
        """Convenience method for CLI demos: approve, then run watcher once."""
        self.request_approval(idea_id)
        jobs = self.process_approvals()
        current = self.get_idea(idea_id)
        if current and current["job_id"]:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (current["job_id"],)).fetchone()
            return dict(row)
        return jobs[0] if jobs else {}

    def reject(self, idea_id: str) -> dict:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone()
            if row is None:
                raise KeyError(f"No existe la idea {idea_id}")
            if row["estado"] == "RECHAZADA":
                return dict(row)
            if row["estado"] != "PENDIENTE":
                raise ValueError(f"Solo se rechazan ideas PENDIENTE; {idea_id} está {row['estado']}")
            conn.execute("UPDATE ideas SET estado = 'RECHAZADA' WHERE id = ?", (idea_id,))
            return dict(conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone())

    def mark_sheet_state(self, idea_id: str, state: str) -> dict:
        """Compatibility helper for local CLI examples using sheet-like statuses."""
        state = state.strip().upper()
        if state not in SHEET_STATES:
            raise ValueError(f"Estado no válido: {state}")
        if state == "APROBADA":
            return self.request_approval(idea_id)
        if state == "RECHAZADA":
            return self.reject(idea_id)
        with self._connect() as conn:
            conn.execute("UPDATE ideas SET estado = ? WHERE id = ?", (state, idea_id))
            row = conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone()
        if row is None:
            raise KeyError(f"No existe la idea {idea_id}")
        return dict(row)
