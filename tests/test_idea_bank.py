from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.idea_bank.provider import MockTextAIProvider, is_duplicate, normalize_name
from services.idea_bank.store import IdeaBank

CATEGORIES = ["Fusiones de Stands", "What If"]


class IdeaBankTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.bank = IdeaBank(Path(self.temp.name) / "ideas.sqlite", MockTextAIProvider())

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_normalizes_accents_punctuation_and_case(self) -> None:
        self.assertEqual(normalize_name("¿QUÉ pasaría? — Star Platinum!"), "que pasaria star platinum")
        self.assertTrue(is_duplicate("Que pasaria Star Platinum", ["¿Qué pasaría? Star Platinum!"]))

    def test_generation_is_structured_and_deduplicated_against_history(self) -> None:
        generated = self.bank.generate_ideas(20, CATEGORIES)
        self.assertEqual(len(generated), 10)
        self.assertEqual(self.bank.generate_ideas(20, CATEGORIES), [])
        self.assertEqual(self.bank.count_pending(), 10)
        self.assertTrue(all(item["id"].startswith("IDEA-") for item in generated))
        self.assertTrue(all(item["duracion_objetivo"] > 0 and item["prioridad"] in range(1, 11) for item in generated))

    def test_approval_watcher_creates_one_content_job_idempotently(self) -> None:
        idea = self.bank.generate_ideas(1, CATEGORIES)[0]
        marked = self.bank.mark_sheet_state(idea["id"], "APROBADA")
        self.assertEqual(marked["estado"], "APROBADA")
        self.assertIsNone(marked["job_id"])
        first = self.bank.process_approvals()
        second = self.bank.process_approvals()
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["estado"], "IDEA_APPROVED")
        self.assertEqual(second, [])
        current = self.bank.get_idea(idea["id"])
        self.assertEqual(current["estado"], "EN_PRODUCCION")
        self.assertEqual(current["job_id"], first[0]["job_id"])
    def test_rejection_never_creates_a_job(self) -> None:
        idea = self.bank.generate_ideas(1, CATEGORIES)[0]
        rejected = self.bank.mark_sheet_state(idea["id"], "RECHAZADA")
        self.assertEqual(rejected["estado"], "RECHAZADA")
        with self.assertRaises(ValueError):
            self.bank.approve(idea["id"])

    def test_unknown_idea_is_not_approved(self) -> None:
        with self.assertRaises(KeyError):
            self.bank.approve("IDEA-999999")


if __name__ == "__main__":
    unittest.main()


