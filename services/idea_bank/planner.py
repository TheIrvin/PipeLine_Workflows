"""Local deterministic content planner and package validator."""
from __future__ import annotations
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from .store import IdeaBank

def build_package(job: dict[str, Any], idea: dict[str, Any]) -> dict[str, dict[str, Any]]:
    title = str(idea.get("idea") or idea.get("titulo") or "").strip()
    summary = str(idea.get("resumen", "")).strip()
    target = max(15, int(idea.get("duracion_objetivo") or 45))
    concept = {
        "content_id": job["job_id"], "idea_id": idea["id"], "concept": title,
        "angle": summary or "Analizar la habilidad, sus límites y una aplicación creativa.",
        "hook": f"¿Y si descubrimos que {title[0].lower() + title[1:] if title else 'este poder'} tiene un límite inesperado?",
        "result": "Una conclusión clara sobre sus ventajas y el coste de usar la habilidad.",
        "cta": "¿Qué otra habilidad de JoJo te gustaría analizar? Déjala en comentarios.",
        "creation_name": "Ecos del destino",
        "ability": "Manipulación táctica de una habilidad de Stand, limitada por alcance y concentración.",
        "weakness": "La habilidad exige concentración y pierde eficacia cuando el usuario queda distraído.",
        "stats": {"poder": "A", "velocidad": "B", "alcance": "C", "durabilidad": "B", "precisión": "A", "potencial": "B"},
    }
    narration = [
        concept["hook"], f"Partimos de esta idea: {title}. {concept['angle']}",
        f"La ventaja principal está en la creatividad, pero no sería ilimitada: {concept['weakness']}",
        f"En una pelea, el resultado dependería de preparar el terreno y elegir el momento. {concept['result']}",
        concept["cta"],
    ]
    script_text = " ".join(narration)
    script = {"content_id": job["job_id"], "visible_text": script_text, "tts_text": script_text,
              "language": "es", "duration_estimated": target, "duration_target": target, "special_pronunciations": []}
    descriptions = [
        f"Presentación visual del dilema: {title}",
        f"Mostrar el concepto y el enfoque: {concept['angle']}",
        f"Visualizar el coste y la debilidad: {concept['weakness']}",
        f"Cierre con el resultado y llamada a la acción: {concept['cta']}",
    ]
    base, remainder = divmod(target, len(descriptions))
    scene_rows = [{"scene_id": f"{job['job_id']}-SCENE-{i+1:02d}", "order": i+1,
                   "duration_target": base + (1 if i < remainder else 0), "type": "image",
                   "description": desc, "required": True, "status": "QUEUED"}
                  for i, desc in enumerate(descriptions)]
    scenes = {"content_id": job["job_id"], "duration_target": target, "scenes": scene_rows}
    continuity = {
        "character": "Silueta original inspirada en manga de acción; sin copiar fotogramas ni diseños protegidos.",
        "colors": "Violeta oscuro, dorado tenue y acentos magenta, constantes en todas las escenas.",
        "environment": "Espacio urbano nocturno estilizado con partículas y contraste dramático.",
        "camera": "Composición vertical, plano medio y contrapicado suave; cambios de encuadre entre escenas.",
        "style": "Ilustración anime original, alto contraste, líneas dinámicas y acabado cinematográfico.",
        "aspect_ratio": "9:16",
        "continuity": "Mantener la misma silueta, paleta, ambiente y dirección de luz en las tres entregas.",
    }
    prompts = {"content_id": job["job_id"], "continuity": continuity, "groups": [
        {"prompt_id": "PROMPT_A", "scene_ids": [scene_rows[0]["scene_id"], scene_rows[1]["scene_id"]],
         "prompt": f"{continuity['style']} {continuity['environment']} {descriptions[0]}. Transición visual a: {descriptions[1]}. Vertical 9:16. {continuity['continuity']}"},
        {"prompt_id": "PROMPT_B", "scene_ids": [scene_rows[2]["scene_id"]],
         "prompt": f"{continuity['style']} {continuity['environment']} {descriptions[2]}. Vertical 9:16. {continuity['continuity']}"},
        {"prompt_id": "PROMPT_C", "scene_ids": [scene_rows[3]["scene_id"]],
         "prompt": f"{continuity['style']} {continuity['environment']} {descriptions[3]}. Vertical 9:16. {continuity['continuity']}"},
    ]}
    package = {"plan.json": concept, "script.json": script, "scenes.json": scenes, "media_prompts.json": prompts}
    validate_package(package)
    return package

def validate_package(package: dict[str, dict[str, Any]]) -> None:
    required = {"plan.json", "script.json", "scenes.json", "media_prompts.json"}
    if set(package) != required:
        raise ValueError("El paquete debe contener exactamente los cuatro JSON V3.")
    plan, script, scenes, prompts = (package[name] for name in ("plan.json", "script.json", "scenes.json", "media_prompts.json"))
    if not script.get("visible_text", "").strip() or not script.get("tts_text", "").strip():
        raise ValueError("El guion y el texto TTS no pueden estar vacíos.")
    if not plan.get("cta") or plan["cta"] not in script["tts_text"]:
        raise ValueError("El concepto debe incluir una CTA presente en el guion.")
    rows = scenes.get("scenes", [])
    if not rows or sum(int(row.get("duration_target", 0)) for row in rows) < int(script.get("duration_target", 0)):
        raise ValueError("Las escenas no cubren la duración objetivo.")
    if not prompts.get("groups") or any(not str(group.get("prompt", "")).strip() for group in prompts["groups"]):
        raise ValueError("Todos los grupos multimedia necesitan un prompt.")
    scene_ids = {row["scene_id"] for row in rows}
    prompt_ids = [item for group in prompts["groups"] for item in group.get("scene_ids", [])]
    if set(prompt_ids) != scene_ids or len(prompt_ids) != len(scene_ids):
        raise ValueError("Cada escena debe pertenecer una sola vez a un grupo de prompts.")
    consistency = prompts.get("continuity", {})
    if consistency.get("aspect_ratio") != "9:16" or not all(consistency.get(k) for k in ("character", "colors", "environment", "camera", "style", "continuity")):
        raise ValueError("Falta información consistente de continuidad visual.")

def save_package(package: dict[str, dict[str, Any]], output_root: str | Path, content_id: str) -> Path:
    if not re.fullmatch(r"CONTENT-[0-9]{6}", content_id):
        raise ValueError("CONTENT-ID no válido.")
    target = Path(output_root) / content_id
    target.mkdir(parents=True, exist_ok=True)
    for filename, document in package.items():
        fd, temporary = tempfile.mkstemp(prefix=f".{filename}.", dir=target)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(document, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temporary, target / filename)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return target

class LocalPlanner:
    def __init__(self, bank: IdeaBank, output_root: str | Path):
        self.bank = bank
        self.output_root = Path(output_root)

    def plan_job(self, content_id: str) -> dict[str, Any]:
        context = self.bank.get_job_context(content_id)
        if context is None:
            raise KeyError(f"No existe el trabajo {content_id}")
        job, idea = context
        if job["estado"] not in {"IDEA_APPROVED", "SCRIPT_READY", "MEDIA_QUEUED"}:
            raise ValueError(f"El trabajo {content_id} no está listo para planificar: {job['estado']}")
        package = build_package(job, idea)
        path = save_package(package, self.output_root, content_id)
        if job["estado"] == "IDEA_APPROVED":
            self.bank.set_job_state(content_id, "SCRIPT_READY")
        if job["estado"] != "MEDIA_QUEUED":
            self.bank.set_job_state(content_id, "MEDIA_QUEUED")
        return {"job_id": content_id, "estado": "MEDIA_QUEUED", "path": str(path), "files": sorted(package)}

    def process_pending(self, limit: int = 20) -> list[dict[str, Any]]:
        jobs = self.bank.jobs_by_state("IDEA_APPROVED", limit=max(1, min(100, limit)))
        return [self.plan_job(job["job_id"]) for job in jobs]
