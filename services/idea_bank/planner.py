"""Local deterministic content planner and package validator."""
from __future__ import annotations
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from .store import IdeaBank

def build_package(job: dict[str, Any], idea: dict[str, Any], narration: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    title = str(idea.get("idea") or idea.get("titulo") or "").strip()
    summary = str(idea.get("resumen", "")).strip()
    target = max(15, int(idea.get("duracion_objetivo") or 45))
    narration = narration or {"beats": [{"text": f"¿Qué pasaría si {title}?", "delivery": "curious"},
        {"text": summary or "Veamos qué hace especial esta idea.", "delivery": "narrator"},
        {"text": "¿Qué otro tema te gustaría analizar?", "delivery": "curious"}]}
    beats = narration["beats"]
    visible_beats = [str(beat["text"]).strip() for beat in beats if str(beat.get("text", "")).strip()]
    script_text = " ".join(visible_beats)
    tts_text = "\n\n".join(f"[{beat.get('delivery', 'narrator')}] {str(beat['text']).strip()}" for beat in beats if str(beat.get("text", "")).strip())
    concept = {
        "content_id": job["job_id"], "idea_id": idea["id"], "concept": title,
        "angle": summary or "Explicar la idea con hechos concretos, límites y consecuencias.",
        "hook": visible_beats[0], "result": visible_beats[-2] if len(visible_beats) > 2 else visible_beats[-1],
        "cta": visible_beats[-1],
        "creation_name": "Ecos del destino",
        "ability": "Manipulación táctica de una habilidad de Stand, limitada por alcance y concentración.",
        "weakness": "La habilidad exige concentración y pierde eficacia cuando el usuario queda distraído.",
        "stats": {"poder": "A", "velocidad": "B", "alcance": "C", "durabilidad": "B", "precisión": "A", "potencial": "B"},
    }
    script = {"content_id": job["job_id"], "visible_text": script_text, "tts_text": tts_text,
              "narration_beats": beats, "narration_pattern": narration.get("pattern"),
              "narration_prompt": narration.get("editorial_prompt"),
              "language": "es", "duration_estimated": target,
              "duration_target": target, "special_pronunciations": []}
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

def generate_narration(title: str, summary: str, duration: int = 45, category: str | None = None) -> dict[str, Any]:
    """Write a topic-specific Spanish narration using a local Ollama model."""
    base = os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/")
    model = os.environ.get("NARRATION_MODEL", "qwen3:4b")
    subject = (title + " " + summary).lower()
    category_key = (category or "").casefold()
    if any(term in subject for term in ("evolucionaría", "evolucion", "requiem")) or "evoluciones" in category_key:
        pattern = ("HIPÓTESIS DE EVOLUCIÓN: plantea el cambio como teoría; conserva la mecánica central de la habilidad "
                   "y amplíala solo un paso; muestra dos consecuencias concretas para proteger al personaje de la idea; "
                   "define un límite que mantenga tensión; cierra con una pregunta. No inventes poderes desconectados.")
    elif "fusion" in category_key or any(term in subject for term in ("fusion", "combinar", "mezclar")):
        pattern = ("FUSIÓN: presenta las dos habilidades; explica la sinergia concreta; muestra una jugada paso a paso; "
                   "añade un coste o incompatibilidad; explica cómo cambia el resultado; pregunta final.")
    elif "enfrentamiento" in category_key or any(term in subject for term in (" versus ", "compar", "mejor que", "duelo", "ganaría", "ventaja")):
        pattern = ("DUELO: plantea la condición para ganar; explica la ventaja clave de cada rival; "
                   "muestra una respuesta táctica de cada uno; decide qué factor inclina la balanza; "
                   "da un veredicto condicionado y pregunta final.")
    elif "what if" in category_key or any(term in subject for term in ("qué habría pasado", "qué ocurriría", "what if", "y si ")):
        pattern = ("LÍNEA ALTERNATIVA: abre con el cambio puntual; indica qué sucede distinto primero; "
                   "sigue dos consecuencias en cadena; explica quién gana o pierde con el cambio; "
                   "termina con el efecto más sorprendente y pregunta final.")
    elif any(term in subject for term in ("origen", "historia", "quién es", "por qué")):
        pattern = ("REVELACIÓN/HISTORIA: abre con el dato intrigante; ubica brevemente el contexto; "
                   "avanza causa y efecto; revela el giro importante; explica qué cambia; pregunta final.")
    elif "poderes hipotéticos" in category_key:
        pattern = ("PODER HIPOTÉTICO: define la regla en una línea; demuestra dos usos fuera de lo obvio; "
                   "explica el límite que evita que sea invencible; muestra el mejor contraataque; pregunta final.")
    elif "conceptos originales" in category_key:
        pattern = ("CONCEPTO ORIGINAL: revela primero la regla extraña; muestra un uso ingenioso; "
                   "explica el coste que obliga a pensar; crea un dilema en una escena hipotética; "
                   "cierra con una pregunta sobre cómo lo usaría la audiencia.")
    elif any(term in subject for term in ("stand", "habilidad", "poder", "técnica", "capacidad")):
        pattern = ("EXPLICACIÓN DE MECÁNICA: pregunta gancho; regla central; qué toca o afecta; "
                   "ejemplos concretos; límite confirmado; aplicación táctica; consecuencia; pregunta final.")
    else:
        pattern = ("PATRÓN A MEDIDA: elige el recorrido que más curiosidad genere para esta idea concreta; "
                   "haz una progresión de dato, ejemplo, giro y consecuencia, y termina con una pregunta.")
    if "crazy diamond" in subject and "josuke" in subject:
        pattern += (" DIRECCIÓN ESPECÍFICA: centra esta teoría en que Crazy Diamond pudiera restaurar las heridas "
                    "de Josuke; no inventes escudos, absorción de energía ni poderes mentales. Enfatiza que ayudaría "
                    "a resistir, pero no lo haría invencible.")
    prompt = f"""Eres guionista de videos cortos interesantes y directos en español latinoamericano.
Crea un guion ORIGINAL para esta idea; el ejemplo de referencia solo aporta ritmo corto, claridad y progresión.
Idea: {title}
Contexto disponible: {summary or 'No se proporcionó más contexto.'}
Patrón editorial seleccionado para esta idea: {pattern}
Duración: {duration} segundos; entre 65 y 95 palabras.
Devuelve solo JSON con esta forma:
{{"beats":[{{"text":"frase","delivery":"curious|narrator|emphatic"}}]}}
Condiciones:
- Entre 7 y 10 beats; una idea breve por beat y 65–95 palabras en total.
- Primer beat: gancho específico. Último beat: pregunta corta. No uses signos de pregunta en los beats intermedios.
- Mantén cada beat entre 7 y 14 palabras y evita repetir la misma condición o idea.
- Sigue el patrón seleccionado y crea un recorrido propio para esta idea.
- El título y el contexto son la única base factual. No agregues escenas, lugares, poderes ni consecuencias como si fueran hechos confirmados.
- Si es una evolución/hipótesis, marca una sola vez que es una teoría. Amplía la mecánica original solo un paso.
- No agregues habilidades mentales/espirituales ni energía universal, salvo que la idea lo proponga explícitamente.
- Usa palabras cotidianas y ejemplos visualizables; evita metáforas abstractas como “distancia entre corazones”.
- Cada beat aporta un dato, ejemplo o consecuencia diferente; evita relleno y repetir ideas.
- Sin introducción genérica, frases meta ni llamada “déjalo en comentarios”.
- Tono conversacional, directo, expresivo y claro; no tráiler ni locutor solemne.
- Usa curious en el gancho y narrator para explicar. Reserva emphatic para un giro real.
- Para Qwen 3, responde sin razonamiento interno y entrega solo el JSON.
"""
    schema = {"type": "object", "properties": {"beats": {
        "type": "array", "minItems": 7, "maxItems": 10,
        "items": {"type": "object", "properties": {
            "text": {"type": "string"}, "delivery": {"type": "string",
                "enum": ["curious", "narrator", "emphatic"]}},
            "required": ["text", "delivery"], "additionalProperties": False}}},
        "required": ["beats"], "additionalProperties": False}
    payload = json.dumps({"model": model, "stream": False, "format": schema, "messages": [
        {"role": "system", "content": "Escribe solo el guion pedido, sin explicar tu razonamiento."},
        {"role": "user", "content": prompt + "\n/no_think"}],
        "think": False, "options": {"temperature": 0.68, "top_p": 0.9, "repeat_penalty": 1.16,
                                     "num_ctx": 4096, "num_predict": 420}}).encode()
    request = urllib.request.Request(base + "/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            result = json.loads(response.read().decode())
        narration = json.loads(result["message"]["content"])
    except (OSError, urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"No se pudo generar el guion local con Ollama ({model}): {exc}") from exc
    beats = narration.get("beats")
    if not isinstance(beats, list) or not 7 <= len(beats) <= 10:
        raise ValueError("El escritor local debe producir entre 7 y 10 beats narrativos.")
    words = sum(len(str(beat.get("text", "")).split()) for beat in beats if isinstance(beat, dict))
    if not 60 <= words <= 105 or any(not isinstance(beat, dict) or not str(beat.get("text", "")).strip() for beat in beats):
        raise ValueError(f"Guion local fuera de los límites editoriales ({words} palabras).")
    for beat in beats:
        if beat.get("delivery") not in {"curious", "narrator", "emphatic"}:
            beat["delivery"] = "narrator"
    return {"beats": beats, "pattern": pattern, "editorial_prompt": prompt}


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
        duration = max(15, int(idea.get("duracion_objetivo") or 45))
        narration = generate_narration(str(idea.get("idea") or idea.get("titulo") or ""),
                                       str(idea.get("resumen") or ""), duration,
                                       str(idea.get("tipo") or ""))
        package = build_package(job, idea, narration)
        path = save_package(package, self.output_root, content_id)
        if job["estado"] == "IDEA_APPROVED":
            self.bank.set_job_state(content_id, "SCRIPT_READY")
        if job["estado"] != "MEDIA_QUEUED":
            self.bank.set_job_state(content_id, "MEDIA_QUEUED")
        return {"job_id": content_id, "estado": "MEDIA_QUEUED", "path": str(path), "files": sorted(package)}

    def process_pending(self, limit: int = 20) -> list[dict[str, Any]]:
        jobs = self.bank.jobs_by_state("IDEA_APPROVED", limit=max(1, min(100, limit)))
        return [self.plan_job(job["job_id"]) for job in jobs]
