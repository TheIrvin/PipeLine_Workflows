from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from services.production.pipeline import ProductionPipeline
from services.production.providers import ManualMediaProvider


class ManualMediaFolderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.scenes = {"scenes": [
            {"scene_id": "CONTENT-000001-SCENE-01", "order": 1},
            {"scene_id": "CONTENT-000001-SCENE-02", "order": 2},
        ]}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_ready_when_numbered_clips_are_in_animation_folder(self) -> None:
        animation_dir = self.root / "subir" / "CONTENT-000001" / "animar_imagenes"
        animation_dir.mkdir(parents=True)
        for number in (1, 2):
            (animation_dir / f"clip_{number:02d}.mp4").write_bytes(b"x" * 2048)

        readiness = ManualMediaProvider().readiness(
            self.scenes, self.root / "subir" / "CONTENT-000001")

        self.assertTrue(readiness["complete"])
        self.assertEqual(readiness["input_mode"], "scene_assets")
        self.assertEqual([Path(row["path"]).name for row in readiness["present"]],
                         ["clip_01.mp4", "clip_02.mp4"])

    def test_complete_video_takes_precedence_over_separate_clips(self) -> None:
        job_dir = self.root / "subir" / "CONTENT-000001"
        animation_dir = job_dir / "animar_imagenes"
        animation_dir.mkdir(parents=True)
        (job_dir / "video_completo.mp4").write_bytes(b"x" * 2048)
        for number in (1, 2):
            (animation_dir / f"clip_{number:02d}.mp4").write_bytes(b"x" * 2048)

        readiness = ManualMediaProvider().readiness(self.scenes, job_dir)

        self.assertTrue(readiness["complete"])
        self.assertEqual(readiness["input_mode"], "full_video")
        self.assertEqual(Path(readiness["present"][0]["path"]).name, "video_completo.mp4")

    def test_final_video_is_copied_to_finished_folder(self) -> None:
        asset = self.root / "data" / "assets" / "CONTENT-000001"
        master = asset / "masters" / "master_final.mp4"
        master.parent.mkdir(parents=True)
        master.write_bytes(b"finished-video")
        worker = ProductionPipeline.__new__(ProductionPipeline)
        worker.manual_finished_root = self.root / "videos" / "terminado"

        result = worker._export_finished_video("CONTENT-000001", asset)

        self.assertEqual(result, self.root / "videos" / "terminado" / "CONTENT-000001.mp4")
        self.assertEqual(result.read_bytes(), master.read_bytes())
        self.assertTrue(master.is_file())


if __name__ == "__main__":
    unittest.main()
