"""Command-line development interface for the local mock idea bank."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .provider import MockTextAIProvider
from .planner import LocalPlanner
from .store import IdeaBank

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATEGORIES = [
    "Fusiones de Stands",
    "Evoluciones/Requiem",
    "What If",
    "Enfrentamientos",
    "Poderes hipotéticos",
    "Conceptos originales",
]


def make_bank() -> IdeaBank:
    db = os.environ.get("IDEA_DB_PATH", str(ROOT / "data" / "ideas" / "ideas.db"))
    return IdeaBank(db, MockTextAIProvider())


def main() -> None:
    parser = argparse.ArgumentParser(description="Banco local de ideas con proveedor mock")
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate", help="Genera e inserta ideas mock")
    generate.add_argument("--count", type=int, default=int(os.environ.get("IDEA_BATCH_SIZE", "30")))
    generate.add_argument("--categories", nargs="*", default=DEFAULT_CATEGORIES)
    sub.add_parser("list", help="Lista las ideas locales")
    sub.add_parser("count-pending", help="Cuenta ideas pendientes")
    approve = sub.add_parser("approve", help="Simula la aprobación manual y crea un job")
    approve.add_argument("idea_id")
    reject = sub.add_parser("reject", help="Rechaza una idea pendiente")
    reject.add_argument("idea_id")
    plan = sub.add_parser("plan", help="Genera el paquete local para un CONTENT-ID aprobado")
    plan.add_argument("content_id")
    args = parser.parse_args()
    bank = make_bank()

    if args.command == "generate":
        items = bank.generate_ideas(args.count, args.categories)
        print(json.dumps({"created": len(items), "ideas": items}, ensure_ascii=False, indent=2))
    elif args.command == "list":
        print(json.dumps(bank.all_ideas(), ensure_ascii=False, indent=2))
    elif args.command == "count-pending":
        print(bank.count_pending())
    elif args.command == "approve":
        print(json.dumps(bank.approve(args.idea_id), ensure_ascii=False, indent=2))
    elif args.command == "reject":
        print(json.dumps(bank.reject(args.idea_id), ensure_ascii=False, indent=2))
    elif args.command == "plan":
        output = os.environ.get("IDEA_JOBS_PATH", str(ROOT / "data" / "jobs"))
        print(json.dumps(LocalPlanner(bank, output).plan_job(args.content_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
