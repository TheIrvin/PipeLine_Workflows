from __future__ import annotations
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from services.idea_bank.planner import LocalPlanner
from services.idea_bank.provider import MockTextAIProvider
from services.idea_bank.store import IdeaBank
from services.production.pipeline import ProductionPipeline

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe") and shutil.which("espeak-ng"), "Requiere FFmpeg, ffprobe y espeak-ng")
class ProductionPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bank = IdeaBank(self.root / "ideas.sqlite", MockTextAIProvider())
        idea = self.bank.generate_ideas(1, ["Fusiones de Stands"])[0]
        job = self.bank.approve(idea["id"])
        LocalPlanner(self.bank, self.root / "jobs").plan_job(job["job_id"])
        self.content_id = job["job_id"]
        self.worker = ProductionPipeline(self.bank, self.root)
    def tearDown(self) -> None:
        self.temp.cleanup()
    def test_mock_end_to_end_and_dry_run_publication(self) -> None:
        result = self.worker.process_job(self.content_id)
        self.assertEqual(result["state"], "READY")
        self.assertTrue(result["qa"]["passed"])
        idea = self.bank.get_idea(self.bank.get_job_context(self.content_id)[0]["idea_id"])
        self.assertEqual(idea["estado"], "LISTA")
        self.assertTrue(idea["titulo_final"])
        self.assertTrue(idea["fecha_listo"])
        assets = self.root / "assets" / self.content_id
        for relative in ("images/media_manifest.json", "audio/narration.wav",
                         "masters/master_sin_subtitulos.mp4", "masters/master_final.mp4",
                         "subtitles/captions.es.srt", "metadata/tiktok.json", "metadata/facebook.json",
                         "metadata/instagram.json", "metadata/youtube_shorts.json", "metadata/qa_report.json"):
            self.assertTrue((assets / relative).is_file(), relative)
        report = json.loads((assets / "metadata/qa_report.json").read_text())
        self.assertEqual(report["codecs"], {"video": "h264", "audio": "aac"})
        results = self.worker.dry_run_publish(self.content_id)
        self.assertEqual({row["status"] for row in results}, {"SIMULATED"})
        self.assertEqual(len(results), 4)
    def test_corrupt_master_is_quarantined_and_worker_resumes_from_checkpoint(self) -> None:
        asset = self.root / "assets" / self.content_id / "masters"
        asset.mkdir(parents=True, exist_ok=True)
        corrupt = asset / "master_sin_subtitulos.mp4"
        corrupt.write_bytes(b"corrupt" * 1024)
        original_render = self.worker.subtitles.render
        def fail_once(video, script, subtitle_dir, output):
            raise RuntimeError("SubtitleWorker temporalmente no responde")
        self.worker.subtitles.render = fail_once
        with self.assertRaises(RuntimeError):
            self.worker.process_job(self.content_id)
        job, _ = self.bank.get_job_context(self.content_id)
        self.assertEqual(job["resume_state"], "SUBTITLING")
        self.assertEqual(job["retry_count"], 1)
        quarantined = list(asset.glob("master_sin_subtitulos.mp4.corrupt-*"))
        self.assertEqual(len(quarantined), 1)
        self.worker.subtitles.render = original_render
        resumed = self.worker.process_job(self.content_id)
        self.assertEqual(resumed["state"], "READY")
        self.assertTrue((asset / "master_sin_subtitulos.mp4").is_file())
        self.assertTrue(quarantined[0].is_file())

    def test_retry_uses_backoff_and_stops_after_five_attempts(self) -> None:
        first = self.bank.set_job_retry(self.content_id, "MEDIA_QUEUED")
        self.assertEqual(first["estado"], "RETRY_PENDING")
        self.assertEqual(first["retry_count"], 1)
        self.assertTrue(first["next_retry_at"])
        self.assertEqual(self.worker.process_pending(), [])
        for _ in range(3):
            first = self.bank.set_job_retry(self.content_id, "MEDIA_QUEUED")
        final = self.bank.set_job_retry(self.content_id, "MEDIA_QUEUED")
        self.assertEqual(final["estado"], "FAILED")
        self.assertEqual(final["retry_count"], 5)

    def test_ready_job_is_idempotent_and_does_not_rebuild_master(self) -> None:
        first = self.worker.process_job(self.content_id)
        path = Path(first["assets"]) / "masters/master_final.mp4"
        modified = path.stat().st_mtime_ns
        second = self.worker.process_job(self.content_id)
        self.assertEqual(second["state"], "READY")
        self.assertEqual(path.stat().st_mtime_ns, modified)

if __name__ == "__main__":
    unittest.main()
