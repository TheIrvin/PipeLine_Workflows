"""Checkpointed local media-to-QA pipeline."""
from __future__ import annotations
import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from services.idea_bank.planner import validate_package
from services.idea_bank.store import IdeaBank
from .providers import (EspeakTTSProvider, ExistingSubtitleBackendAdapter, FacebookPublisher,
                        InstagramPublisher, LocalSubtitleWorker, MockMediaProvider, TikTokPublisher, YouTubePublisher)

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

class ProductionPipeline:
    def __init__(self, bank: IdeaBank, data_root: str | Path):
        self.bank = bank
        self.data_root = Path(data_root)
        self.jobs_root = self.data_root / "jobs"
        self.assets_root = self.data_root / "assets"
        self.logs_root = self.data_root / "logs"
        self.media, self.tts = MockMediaProvider(), EspeakTTSProvider()
        subtitle_url = os.environ.get("SUBTITLE_WORKER_URL", "").strip()
        if subtitle_url:
            export_dir = os.environ.get("SUBTITLE_EXPORT_DIR") or r"\\wsl.localhost\Ubuntu\home\irvin\PipeLine_Workflows\data\temp\subtitle-export"
            self.subtitles = ExistingSubtitleBackendAdapter(subtitle_url, export_dir)
        else:
            self.subtitles = LocalSubtitleWorker()
        self.publishers = [TikTokPublisher(), FacebookPublisher(), InstagramPublisher(), YouTubePublisher()]
        self._processing_lock = threading.Lock()

    def _asset(self, content_id: str) -> Path:
        return self.assets_root / content_id
    def _state(self, content_id: str) -> str:
        context = self.bank.get_job_context(content_id)
        if context is None: raise KeyError(f"No existe el trabajo {content_id}")
        return context[0]["estado"]
    def _load_package(self, content_id: str) -> dict:
        root = self.jobs_root / content_id
        package = {name: json.loads((root / name).read_text(encoding="utf-8")) for name in
                   ("plan.json", "script.json", "scenes.json", "media_prompts.json")}
        validate_package(package)
        return package
    def _log(self, content_id: str, module: str, status: str, message: str, error_code: str | None = None) -> None:
        self.logs_root.mkdir(parents=True, exist_ok=True)
        item = {"timestamp": now(), "job_id": content_id, "module": module, "status": status,
                "message": message, "error_code": error_code}
        with (self.logs_root / "pipeline.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")
    @staticmethod
    def _atomic_json(path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    def _ffprobe(self, path: Path) -> dict:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                                capture_output=True, text=True, timeout=30)
        if result.returncode: raise ValueError(f"Archivo corrupto o no reproducible: {path.name}")
        return json.loads(result.stdout)

    def process_job(self, content_id: str) -> dict[str, Any]:
        with self._processing_lock:
            return self._process_job_locked(content_id)

    def _process_job_locked(self, content_id: str) -> dict[str, Any]:
        context = self.bank.get_job_context(content_id)
        if context is None: raise KeyError(f"No existe el trabajo {content_id}")
        job = context[0]
        state = job["estado"]
        if state == "READY": return {"job_id": content_id, "state": state, "resumed": True}
        accepted = {"MEDIA_QUEUED", "MEDIA_READY", "TTS_READY", "ASSEMBLING", "SUBTITLING",
                    "METADATA_READY", "QA_PENDING", "RETRY_PENDING", "WAITING_PROVIDER", "WAITING_MANUAL_ACTION"}
        if state not in accepted: raise ValueError(f"El trabajo no puede entrar a producción desde {state}")
        if state in {"RETRY_PENDING", "WAITING_PROVIDER", "WAITING_MANUAL_ACTION"}:
            state = job.get("resume_state") or "MEDIA_QUEUED"
            self.bank.set_job_state(content_id, state)
        asset = self._asset(content_id)
        for folder in ("images", "videos", "audio", "subtitles", "metadata", "masters", "platform_versions"):
            (asset / folder).mkdir(parents=True, exist_ok=True)
        package = self._load_package(content_id)
        try:
            if state == "MEDIA_QUEUED":
                manifest = self.media.generate(content_id, package["scenes.json"], asset / "images")
                self.bank.set_job_state(content_id, "MEDIA_READY")
                self._log(content_id, "media", "ok", f"{len(manifest['assets'])} assets mock listos.")
                state = "MEDIA_READY"
            if state == "MEDIA_READY":
                self.tts.synthesize(self._tts_text(package["script.json"]), package["script.json"]["language"],
                                    os.environ.get("TTS_VOICE", "es-la"), int(os.environ.get("TTS_SPEED", "170")),
                                    asset / "audio" / "narration.wav")
                self.bank.set_job_state(content_id, "TTS_READY")
                self._log(content_id, "tts", "ok", "Narración WAV sintetizada localmente.")
                state = "TTS_READY"
            if state == "TTS_READY":
                self.bank.set_job_state(content_id, "ASSEMBLING")
                state = "ASSEMBLING"
            if state == "ASSEMBLING":
                self._assemble(package, asset)
                self.bank.set_job_state(content_id, "SUBTITLING")
                self._log(content_id, "video", "ok", "Master sin subtítulos creado y validado.")
                state = "SUBTITLING"
            if state == "SUBTITLING":
                final_master = asset / "masters" / "master_final.mp4"
                valid_existing = False
                if final_master.exists():
                    try:
                        probe = self._ffprobe(final_master)
                        valid_existing = any(row.get("codec_type") == "video" and row.get("codec_name") == "h264" for row in probe["streams"])
                    except Exception:
                        pass
                    if not valid_existing:
                        final_master.replace(final_master.with_name(final_master.name + f".corrupt-{int(time.time())}"))
                if not valid_existing:
                    self.subtitles.render(asset / "masters" / "master_sin_subtitulos.mp4", package["script.json"],
                                          asset / "subtitles", final_master)
                self.bank.set_job_state(content_id, "METADATA_READY")
                self._log(content_id, "subtitles", "ok", "Subtítulos aplicados sin cambiar el texto aprobado.")
                state = "METADATA_READY"
            if state == "METADATA_READY":
                self._metadata(package, asset)
                self.bank.set_job_state(content_id, "QA_PENDING")
                self._log(content_id, "metadata", "ok", "Metadatos por plataforma generados.")
                state = "QA_PENDING"
            if state == "QA_PENDING":
                report = self._quality_gate(content_id, asset)
                self._atomic_json(asset / "metadata" / "qa_report.json", report)
                if not report["passed"]: raise ValueError("QA rechazó el contenido: " + "; ".join(report["errors"]))
                self.bank.set_job_state(content_id, "READY")
                self.bank.mark_idea_ready_for_job(content_id, package["plan.json"]["concept"])
                self._update_buffer(content_id, asset, package)
                self._log(content_id, "qa", "ok", "QA aprobado; contenido agregado al buffer local.")
                return {"job_id": content_id, "state": "READY", "assets": str(asset), "qa": report}
            return {"job_id": content_id, "state": self._state(content_id), "assets": str(asset)}
        except Exception as exc:
            self.bank.record_job_event(content_id, "pipeline", "error", str(exc), "PIPELINE_STAGE_FAILED")
            retry = self.bank.set_job_retry(content_id, resume_state=state)
            self._log(content_id, "pipeline", retry["estado"].lower(), str(exc), "PIPELINE_STAGE_FAILED")
            raise

    def _assemble(self, package: dict, asset: Path) -> None:
        output = asset / "masters" / "master_sin_subtitulos.mp4"
        if output.exists():
            try:
                probe = self._ffprobe(output)
                video = next((row for row in probe["streams"] if row.get("codec_type") == "video"), None)
                audio = next((row for row in probe["streams"] if row.get("codec_type") == "audio"), None)
                if video and audio and video.get("codec_name") == "h264" and audio.get("codec_name") == "aac":
                    return
            except Exception:
                pass
            output.replace(output.with_name(output.name + f".corrupt-{int(time.time())}"))
        scenes = package["scenes.json"]["scenes"]
        inputs = []
        for scene in scenes:
            image = asset / "images" / f"{scene['scene_id']}.ppm"
            inputs += ["-loop", "1", "-framerate", "30", "-t", str(scene["duration_target"]), "-i", str(image)]
        audio_index = len(scenes)
        inputs += ["-i", str(asset / "audio" / "narration.wav")]
        filters = [f"[{i}:v]scale=540:960:force_original_aspect_ratio=increase,crop=540:960,fps=30,setsar=1[v{i}]"
                   for i in range(len(scenes))]
        filters.append("".join(f"[v{i}]" for i in range(len(scenes))) + f"concat=n={len(scenes)}:v=1:a=0[v]")
        duration = sum(int(scene["duration_target"]) for scene in scenes)
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
                   "-filter_complex", ";".join(filters), "-map", "[v]", "-map", f"{audio_index}:a:0",
                   "-af", "apad", "-t", str(duration), "-c:v", "libx264", "-preset", "ultrafast",
                   "-crf", "25", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
        if result.returncode: raise RuntimeError(result.stderr[-2500:] or "FFmpeg no pudo ensamblar el master.")
        probe = self._ffprobe(output)
        video = next((row for row in probe["streams"] if row.get("codec_type") == "video"), None)
        if not video or int(video["width"]) != 540 or int(video["height"]) != 960:
            raise ValueError("El master no quedó en formato vertical 9:16.")

    def _tts_text(self, script: dict) -> str:
        text = str(script.get("tts_text", ""))
        dictionary_path = Path(__file__).with_name("pronunciation_dictionary.json")
        if dictionary_path.is_file():
            dictionary = json.loads(dictionary_path.read_text(encoding="utf-8"))
            for original, spoken in dictionary.items():
                text = re.sub(r"(?<!\w)" + re.escape(original) + r"(?!\w)", str(spoken), text, flags=re.IGNORECASE)
        for entry in script.get("special_pronunciations", []):
            if isinstance(entry, dict) and entry.get("text") and entry.get("pronunciation"):
                text = text.replace(str(entry["text"]), str(entry["pronunciation"]))
        return text

    def _metadata(self, package: dict, asset: Path) -> None:
        plan = package["plan.json"]
        title, summary, cta = plan["concept"].strip(), plan["angle"].strip(), plan["cta"].strip()
        tags = ["#JoJo", "#Anime", "#Shorts"]
        docs = {
            "tiktok.json": {"caption": f"{title}\n\n{summary}", "cta": cta, "hashtags": tags},
            "facebook.json": {"text": f"{title}\n\n{summary}", "cta": cta, "hashtags": tags},
            "youtube_shorts.json": {"title": title[:100], "description": f"{summary}\n\n{cta}", "tags": ["JoJo", "anime", "shorts"], "cta": cta},
            "instagram.json": {"caption": f"{title}\n\n{summary}", "cta": cta, "hashtags": tags}}
        for name, doc in docs.items():
            path = asset / "metadata" / name
            if not path.exists(): self._atomic_json(path, doc)

    def _quality_gate(self, content_id: str, asset: Path) -> dict:
        errors = []
        paths = {"clean_master": asset / "masters" / "master_sin_subtitulos.mp4",
                 "final_master": asset / "masters" / "master_final.mp4",
                 "audio": asset / "audio" / "narration.wav", "subtitles": asset / "subtitles" / "captions.es.srt"}
        for key, path in paths.items():
            if not path.is_file() or path.stat().st_size < (100 if key == "subtitles" else 1024):
                errors.append(f"Falta o es inválido: {key}")
        duration = 0.0
        try:
            probe = self._ffprobe(paths["final_master"])
            video = next(row for row in probe["streams"] if row.get("codec_type") == "video")
            audio = next(row for row in probe["streams"] if row.get("codec_type") == "audio")
            duration = float(probe["format"]["duration"])
            if (int(video.get("width", 0)), int(video.get("height", 0))) != (540, 960): errors.append("El master final no es 9:16.")
            if video.get("codec_name") != "h264" or audio.get("codec_name") != "aac": errors.append("El master final requiere H.264 y AAC.")
            if not 1 <= duration <= 180: errors.append("La duración está fuera del rango permitido.")
        except Exception: errors.append("No se pudo leer el master final con ffprobe.")
        required = ("tiktok.json", "facebook.json", "youtube_shorts.json", "instagram.json")
        if any(not (asset / "metadata" / name).is_file() for name in required): errors.append("Falta metadata para alguna plataforma.")
        return {"job_id": content_id, "checked_at": now(), "passed": not errors, "errors": errors,
                "duration_seconds": duration, "aspect_ratio": "9:16", "codecs": {"video": "h264", "audio": "aac"},
                "files": {key: str(path) for key, path in paths.items()}}

    def _update_buffer(self, content_id: str, asset: Path, package: dict) -> None:
        path = self.data_root / "buffer" / "manifest.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"minimum": 7, "target": 14, "items": []}
        if content_id not in {item["job_id"] for item in data["items"]}:
            data["items"].append({"job_id": content_id, "title": package["plan.json"]["concept"], "status": "READY",
                                  "ready_at": now(), "video": str(asset / "masters" / "master_final.mp4")})
        data["minimum"] = int(os.environ.get("CONTENT_BUFFER_MIN", "7"))
        data["target"] = int(os.environ.get("CONTENT_BUFFER_TARGET", "14"))
        data["ready_count"] = len([item for item in data["items"] if item.get("status") == "READY"])
        data["minimum_reached"] = data["ready_count"] >= data["minimum"]
        self._atomic_json(path, data)

    def dry_run_publish(self, content_id: str) -> list[dict]:
        if self._state(content_id) != "READY": raise ValueError("Solo se simulan publicaciones de jobs READY.")
        asset, video = self._asset(content_id), self._asset(content_id) / "masters" / "master_final.mp4"
        results = []
        for publisher in self.publishers:
            name = "youtube_shorts.json" if publisher.platform == "youtube" else f"{publisher.platform}.json"
            metadata = json.loads((asset / "metadata" / name).read_text(encoding="utf-8"))
            results.append(publisher.publish(video, metadata, dry_run=True))
        self._atomic_json(asset / "metadata" / "publish_dry_run.json",
                          {"dry_run": True, "completed_at": now(), "platforms": results})
        return results

    @staticmethod
    def _atomic_json(path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)

    def process_pending(self, limit: int = 1) -> list[dict]:
        states = ["RETRY_PENDING", "WAITING_PROVIDER", "WAITING_MANUAL_ACTION", "ASSEMBLING", "SUBTITLING",
                  "METADATA_READY", "QA_PENDING", "TTS_READY", "MEDIA_READY", "MEDIA_QUEUED", "MEDIA_PARTIAL"]
        jobs = []
        for state in states:
            candidates = self.bank.jobs_by_state(state, 100)
            if state == "RETRY_PENDING":
                candidates = [job for job in candidates if not job.get("next_retry_at") or job["next_retry_at"] <= now()]
            jobs.extend(candidates)
            if len(jobs) >= limit: break
        jobs.sort(key=lambda row: row["seq"])
        result = []
        for job in jobs[:max(1, min(10, limit))]:
            try: result.append(self.process_job(job["job_id"]))
            except Exception as exc: result.append({"job_id": job["job_id"], "state": self._state(job["job_id"]), "error": str(exc)})
        return result
