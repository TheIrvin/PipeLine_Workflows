"""Replaceable local/mock providers for media, TTS, subtitles and publishing."""
from __future__ import annotations
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class MockMediaProvider:
    """Creates deterministic local PPM placeholders without network or quota."""
    def generate(self, content_id: str, scenes: dict, output_dir: Path) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        colors = [(31, 21, 66), (69, 26, 83), (36, 35, 91), (82, 31, 70)]
        created = []
        for index, scene in enumerate(scenes["scenes"]):
            path = output_dir / f"{scene['scene_id']}.ppm"
            if not path.exists():
                red, green, blue = colors[index % len(colors)]
                with path.open("wb") as stream:
                    stream.write(b"P6\n540 960\n255\n")
                    row = bytes([red, green, blue]) * 540
                    for _ in range(960):
                        stream.write(row)
            created.append({"scene_id": scene["scene_id"], "path": str(path), "provider": "mock", "status": "READY"})
        manifest = {"content_id": content_id, "provider": "mock", "status": "MEDIA_READY", "assets": created}
        (output_dir / "media_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return manifest


class EspeakTTSProvider:
    """Offline CPU TTS provider. Kokoro can be added behind the same interface."""
    def synthesize(self, text: str, language: str, voice: str, speed: int, output: Path) -> dict:
        if not text.strip():
            raise ValueError("El texto TTS está vacío.")
        output.parent.mkdir(parents=True, exist_ok=True)
        selected_voice = voice or ("es-la" if language.startswith("es") else "en")
        result = subprocess.run(["espeak-ng", "-v", selected_voice, "-s", str(max(80, min(260, speed))),
                                 "-w", str(output), text], capture_output=True, text=True, timeout=180)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "espeak-ng falló.")
        if not output.exists() or output.stat().st_size < 44:
            raise RuntimeError("TTS no produjo un WAV válido.")
        return {"path": str(output), "voice": selected_voice, "provider": "espeak-ng", "size": output.stat().st_size}


class FishAudioTTSProvider:
    """Fish Audio API using the selected voice; never falls back to robotic offline TTS."""
    endpoint = "https://api.fish.audio/v1/tts"

    def __init__(self, api_key: str, reference_id: str, model: str = "s2.1-pro-free"):
        self.api_key = api_key.strip()
        self.reference_id = reference_id.strip()
        self.model = model.strip() or "s2.1-pro-free"

    def synthesize(self, text: str, language: str, voice: str, speed: int, output: Path) -> dict:
        if not self.api_key:
            raise RuntimeError("Falta FISH_AUDIO_API_KEY en el .env local.")
        if not self.reference_id:
            raise RuntimeError("Falta FISH_AUDIO_REFERENCE_ID.")
        spoken = text.strip()
        if not spoken:
            raise ValueError("El texto TTS está vacío.")
        payload = json.dumps({
            "text": spoken,
            "reference_id": self.reference_id,
            "format": "wav",
            "temperature": 0.75,
            "top_p": 0.85,
            "chunk_length": 300,
            "condition_on_previous_chunks": True,
            "prosody": {"speed": 1.0, "volume": 0, "normalize_loudness": True},
            "normalize": True,
        }, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.endpoint, data=payload, headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "model": self.model,
        }, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                audio = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", errors="replace")
            raise RuntimeError(f"Fish Audio rechazó la solicitud (HTTP {exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"No se pudo conectar con Fish Audio: {exc.reason}") from exc
        if len(audio) < 44 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
            raise RuntimeError("Fish Audio no devolvió un WAV válido.")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(audio)
        return {"path": str(output), "voice": self.reference_id, "provider": "fish-audio",
                "model": self.model, "size": len(audio)}


class LocalSubtitleWorker:
    """Exact-text local subtitle timing; ASR never replaces the approved script."""
    def render(self, video: Path, script: dict[str, Any], subtitle_dir: Path, output: Path) -> dict:
        text = str(script.get("visible_text", "")).strip()
        if not text:
            raise ValueError("El guion visible está vacío.")
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        duration = float(script.get("duration_target") or 45)
        words = text.split()
        chunks = [" ".join(words[i:i + 5]) for i in range(0, len(words), 5)]
        span = duration / max(1, len(chunks))
        def timestamp(seconds: float) -> str:
            milliseconds = round(seconds * 1000)
            hours, milliseconds = divmod(milliseconds, 3_600_000)
            minutes, milliseconds = divmod(milliseconds, 60_000)
            secs, milliseconds = divmod(milliseconds, 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
        lines = []
        for index, chunk in enumerate(chunks):
            start, end = index * span, min(duration, (index + 1) * span)
            lines.extend([str(index + 1), f"{timestamp(start)} --> {timestamp(end)}", chunk, ""])
        srt = subtitle_dir / "captions.es.srt"
        srt.write_text("\n".join(lines), encoding="utf-8")
        subtitle_filter = str(srt).replace("\\", "/").replace(":", r"\:")
        result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
                                 "-vf", f"subtitles='{subtitle_filter}'", "-c:v", "libx264", "-preset", "ultrafast",
                                 "-crf", "24", "-c:a", "copy", "-movflags", "+faststart", str(output)],
                               capture_output=True, text=True, timeout=600)
        if result.returncode:
            raise RuntimeError(result.stderr[-2000:] or "FFmpeg no pudo quemar los subtítulos.")
        return {"subtitle_path": str(srt), "video_path": str(output), "blocks": len(chunks), "provider": "local-exact-script"}


class ExistingSubtitleBackendAdapter:
    """Adapter for the user's FastAPI subtitle project; enabled by SUBTITLE_WORKER_URL."""
    def __init__(self, base_url: str, export_dir: str):
        self.base_url, self.export_dir = base_url.rstrip("/"), export_dir
    def _request(self, path: str, data: bytes | None = None, content_type: str | None = None, method: str | None = None) -> bytes:
        headers = {"Content-Type": content_type} if content_type else {}
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=900) as response:
            return response.read()
    def render(self, video: Path, script: dict[str, Any], subtitle_dir: Path, output: Path) -> dict:
        boundary = "----PipelineUploadBoundary"
        head = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"master_sin_subtitulos.mp4\"\r\n"
                "Content-Type: video/mp4\r\n\r\n").encode()
        body = head + video.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        project = json.loads(self._request("/api/upload", body, f"multipart/form-data; boundary={boundary}"))
        project_id = project["project_id"]
        manual = json.dumps({"text_es": script["visible_text"], "text_en": ""}, ensure_ascii=False).encode()
        manual_result = json.loads(self._request(f"/api/manual-subtitles/{project_id}", manual, "application/json", "POST"))
        export = json.dumps({"name": video.stem, "quality": "baja", "output_dir": self.export_dir}).encode()
        self._request(f"/api/export/{project_id}", export, "application/json", "POST")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(self._request(f"/api/download/{project_id}"))
        if output.stat().st_size < 1024:
            raise RuntimeError("El backend de subtítulos no devolvió un MP4 válido.")

        # Keep a local SRT sidecar for pipeline QA and downstream review.
        def timestamp(seconds: float) -> str:
            milliseconds = max(0, round(float(seconds) * 1000))
            hours, milliseconds = divmod(milliseconds, 3_600_000)
            minutes, milliseconds = divmod(milliseconds, 60_000)
            secs, milliseconds = divmod(milliseconds, 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        lines = []
        for index, block in enumerate(manual_result.get("blocks", []), 1):
            text = str(block.get("text_es", "")).strip()
            if not text:
                continue
            lines.extend([str(index), f"{timestamp(block.get('start', 0))} --> {timestamp(block.get('end', 0))}", text, ""])
        if not lines:
            raise RuntimeError("El backend no devolvió bloques de subtítulos para QA.")
        srt = subtitle_dir / "captions.es.srt"
        srt.write_text(chr(10).join(lines), encoding="utf-8")
        return {"subtitle_path": str(srt), "video_path": str(output), "provider": "existing-subtitle-backend", "project_id": project_id}


class MockPlatformPublisher:
    platform = "generic"
    def publish(self, video: Path, metadata: dict, dry_run: bool = True) -> dict:
        if not dry_run:
            raise RuntimeError("La publicación real requiere configuración y autorización manual.")
        if not video.is_file() or video.stat().st_size < 1024:
            raise ValueError("El video para dry-run no es válido.")
        return {"platform": self.platform, "status": "SIMULATED", "post_id": f"DRY-{self.platform.upper()}-{video.stem}",
                "url": None, "dry_run": True, "metadata": metadata}


class TikTokPublisher(MockPlatformPublisher):
    platform = "tiktok"
class FacebookPublisher(MockPlatformPublisher):
    platform = "facebook"
class InstagramPublisher(MockPlatformPublisher):
    platform = "instagram"
class YouTubePublisher(MockPlatformPublisher):
    platform = "youtube"
