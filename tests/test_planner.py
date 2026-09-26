from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from services.idea_bank.planner import LocalPlanner, build_package, validate_package
from services.idea_bank.provider import MockTextAIProvider
from services.idea_bank.store import IdeaBank

class PlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bank = IdeaBank(self.root / "ideas.sqlite", MockTextAIProvider())
        idea = self.bank.generate_ideas(1, ["Fusiones de Stands"])[0]
        self.job = self.bank.approve(idea["id"])
        self.content_id = self.job["job_id"]
        self.planner = LocalPlanner(self.bank, self.root / "jobs")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_package_contains_four_valid_artifacts_and_duration_coverage(self) -> None:
        context = self.bank.get_job_context(self.content_id)
        package = build_package(*context)
        validate_package(package)
        self.assertEqual(set(package), {"plan.json", "script.json", "scenes.json", "media_prompts.json"})
        self.assertEqual(sum(row["duration_target"] for row in package["scenes.json"]["scenes"]), 45)
        self.assertIn(package["plan.json"]["cta"], package["script.json"]["tts_text"])

    def test_process_moves_to_media_queue_and_saves_files_once(self) -> None:
        results = self.planner.process_pending()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["estado"], "MEDIA_QUEUED")
        path = Path(results[0]["path"])
        self.assertEqual({item.name for item in path.iterdir()}, {"plan.json", "script.json", "scenes.json", "media_prompts.json"})
        stored = json.loads((path / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["content_id"], self.content_id)
        self.assertEqual(self.planner.process_pending(), [])
        self.assertEqual(self.bank.jobs_by_state("MEDIA_QUEUED")[0]["job_id"], self.content_id)

    def test_reprocessing_is_idempotent(self) -> None:
        first = self.planner.plan_job(self.content_id)
        second = self.planner.plan_job(self.content_id)
        self.assertEqual(first, second)
        self.assertEqual(self.bank.get_job_context(self.content_id)[0]["estado"], "MEDIA_QUEUED")

if __name__ == "__main__":
    unittest.main()
