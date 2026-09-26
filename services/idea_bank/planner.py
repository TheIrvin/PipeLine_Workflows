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
        "ability": visible_beats[1] if len(visible_beats) > 1 else summary or title,
        "weakness": visible_beats[-2] if len(visible_beats) > 2 else summary or title,
        "stats": {"poder": "A", "velocidad": "B", "alcance": "C", "durabilidad": "B", "precisión": "A", "potencial": "B"},
    }
    script = {"content_id": job["job_id"], "visible_text": script_text, "tts_text": tts_text,
              "narration_beats": beats, "narration_pattern": narration.get("pattern"),
              "narration_prompt": narration.get("editorial_prompt"),
              "language": "es", "duration_estimated": target,
              "duration_target": target, "special_pronunciations": []}
    beat_groups = []
    for index in range(4):
        start = round(index * len(visible_beats) / 4)
        end = round((index + 1) * len(visible_beats) / 4)
        beat_groups.append(" ".join(visible_beats[start:end]))
    descriptions = [
        f"Gancho y premisa: {beat_groups[0]}",
        f"Mecánica y desarrollo: {beat_groups[1]}",
        f"Hipótesis y límite: {beat_groups[2]}",
        f"Consecuencia y pregunta final: {beat_groups[3]}",
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
        "continuity": "Mantener la misma silueta, paleta, ambiente y dirección de luz en todas las escenas.",
    }
    per_scene = []
    for index, scene in enumerate(scene_rows):
        start = round(index * len(visible_beats) / len(scene_rows))
        end = round((index + 1) * len(visible_beats) / len(scene_rows))
        context = " ".join(visible_beats[start:end]) or descriptions[index]
        image_prompt = (f"{continuity['style']}. {continuity['environment']}. {descriptions[index]}. "
                        f"Narration beat to illustrate: {context}. {continuity['character']} "
                        f"{continuity['colors']} {continuity['camera']} Vertical portrait 9:16. "
                        "One clear focal action, readable silhouette, cinematic depth, leave safe space near top and bottom. "
                        "Original character and scene; no text, subtitles, logos, watermark, collage, or UI. "
                        f"Match visual continuity: {continuity['continuity']}")
        video_prompt = (f"Animate this exact reference image for about 8 seconds. {descriptions[index]}. "
                        "Preserve the same character design, clothing, props, background, palette, and lighting. "
                        "Use one restrained cinematic camera move and subtle natural motion that supports the narration; "
                        "keep the subject recognizable and the composition vertical 9:16. No cuts, new characters, "
                        "new objects, text, subtitles, logos, watermark, dialogue, or music.")
        per_scene.append({"scene_id": scene["scene_id"], "clip_target_seconds": min(8, int(scene["duration_target"])),
                          "narration_context": context, "image_prompt": image_prompt,
                          "video_prompt": video_prompt, "suggested_filename": f"{scene['scene_id']}.mp4"})
    full_video_prompt = (f"Create one complete vertical 9:16 video illustrating this narrated short about {title}. "
                         f"Keep a coherent visual progression through these beats, in order: {'; '.join(descriptions)}. "
                         f"Narration context: {script_text}. {continuity['style']} {continuity['colors']} "
                         f"{continuity['environment']} Keep the same original character and visual continuity. "
                         "Use clear visual changes between beats, restrained camera motion, and no text, subtitles, "
                         "logos, watermark, dialogue, or music. Fit the supplied narration's full duration.")
    prompts = {"content_id": job["job_id"], "continuity": continuity, "full_video_prompt": full_video_prompt,
               "manual_scene_prompts": per_scene, "groups": [
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
    prompts = package.get("media_prompts.json", {})
    handoff = [f"# Entrega manual de medios — {content_id}", "",
               "Opción recomendada: entrega un solo MP4 completo. Alternativa: usa los prompts de imagen y animación por escena y entrega un archivo por escena.", "",
               "## Carpeta de entrega", "", f"`Downloads/Pipeline_Workflows/ManualMedia/{content_id}/inbox/`", "",
               "Para un video completo usa el nombre exacto `video_completo.mp4`. Para clips separados, usa los nombres indicados en cada escena. El worker detecta los archivos automáticamente.", "",
               "## Opción: un video completo", "", prompts.get("full_video_prompt", ""), "",
               "Puedes entregar ese video como `video_completo.mp4`. Si prefieres generar clips separados, usa los prompts de cada escena de abajo.", "",
               "## Prompts por escena", ""]
    for item in prompts.get("manual_scene_prompts", []):
        handoff.extend([f"### {item['scene_id']} ({item['clip_target_seconds']} s objetivo)", "",
                        f"Contexto narrado: {item['narration_context']}", "",
                        "**Prompt de imagen de referencia**", "", item["image_prompt"], "",
                        "**Prompt para animar esa imagen**", "", item["video_prompt"], "",
                        f"**Archivo de video:** `{item['suggested_filename']}`", "",
                        f"**Archivo de imagen alternativo:** `{item['scene_id']}.png`", ""])
    (target / "media_prompts.md").write_text("\n".join(handoff), encoding="utf-8")
    return target

def generate_narration(title: str, summary: str, duration: int = 45, category: str | None = None) -> dict[str, Any]:
    """Write a topic-specific Spanish narration using a local Ollama model."""
    base = os.environ.get("OLLAMA_URL", "http://ollama:11434").rstrip("/")
    model = os.environ.get("NARRATION_MODEL", "qwen3:4b")
    subject = (title + " " + summary).lower()
    category_key = (category or "").casefold()
    if any(term in subject for term in ("evolucionaría", "evolucion", "requiem")) or "evoluciones" in category_key:
        pattern = "HIPÓTESIS DE EVOLUCIÓN"
        hook_guide = ("Abre con la consecuencia más inquietante o potente de esa evolución, o con la regla actual "
                      "que cambiaría; identifica enseguida que se trata de una teoría. No uses una pregunta genérica.")
        story_guide = ("Conserva la mecánica canónica; propón una sola ampliación plausible. Orden: regla actual, "
                       "cambio hipotético, dos consecuencias visibles, coste o límite que mantenga tensión.")
        ending_guide = ("Pregunta qué consecuencia de la teoría sí encaja con las reglas conocidas o qué límite "
                        "la volvería demasiado poderosa; invita a justificarlo con una mecánica concreta.")
    elif "fusion" in category_key or any(term in subject for term in ("fusion", "combinar", "mezclar")):
        pattern = "FUSIÓN DE HABILIDADES"
        hook_guide = ("Presenta la combinación como una jugada inesperada o como un problema que ninguna habilidad "
                      "resolvería por sí sola; menciona ambas habilidades con claridad.")
        story_guide = ("Explica qué aporta cada habilidad, cómo se encadenan en una situación concreta y qué "
                       "incompatibilidad, alcance o coste puede frustrar la combinación.")
        ending_guide = ("Pregunta cuál sería el uso más peligroso o qué incompatibilidad decidiría el resultado; "
                        "pide una razón basada en las reglas de ambas habilidades.")
    elif "enfrentamiento" in category_key or any(term in subject for term in (" versus ", "compar", "mejor que", "duelo", "ganaría", "ventaja")):
        pattern = "ENFRENTAMIENTO CON VEREDICTO CONDICIONAL"
        hook_guide = ("Abre con la condición concreta que podría decidir el duelo o con una ventaja que parece "
                      "definitiva pero tiene respuesta; nombra a los dos rivales pronto.")
        story_guide = ("Compara una ventaja real de cada rival, muestra cómo respondería el otro y aterriza el "
                       "análisis en un escenario o condición de victoria; evita declarar un ganador absoluto sin base.")
        ending_guide = ("Pregunta qué condición cambiaría el ganador o qué respuesta táctica pesa más; permite "
                        "defender cualquiera de las posturas con argumentos del enfrentamiento.")
    elif "what if" in category_key or any(term in subject for term in ("qué habría pasado", "qué ocurriría", "what if", "y si ")):
        pattern = "LÍNEA TEMPORAL ALTERNATIVA"
        hook_guide = ("Nombra la decisión o evento que cambia y revela de inmediato qué resultado conocido "
                      "quedaría en riesgo; no empieces con una introducción de contexto.")
        story_guide = ("Sigue una cadena causal de dos o tres pasos: cambio inicial, reacción directa y "
                       "consecuencia posterior. No presentes como canon lo que solo es una posibilidad.")
        ending_guide = ("Pregunta cuál consecuencia de la cadena creen más probable o qué evento posterior "
                        "cambiaría por completo; busca hipótesis rivales que puedan debatirse.")
    elif any(term in subject for term in ("origen", "historia", "quién es", "por qué")):
        pattern = "REVELACIÓN E HISTORIA"
        hook_guide = ("Empieza por una pista, contradicción o detalle cuyo significado cambie al conocer "
                      "la historia; promete una explicación que el contenido sí pueda entregar.")
        story_guide = ("Da solo el contexto necesario, conecta los hechos por causa y efecto y reserva el "
                       "dato que reinterpreta la pista para el tramo medio o final; no inventes canon.")
        ending_guide = ("Pregunta qué pista cambia más la interpretación o qué explicación alternativa "
                        "encaja mejor con los datos narrados; no pidas opiniones vacías.")
    elif "poderes hipotéticos" in category_key:
        pattern = "PODER HIPOTÉTICO Y CONTRAJUEGO"
        hook_guide = ("Abre con una aplicación inesperada que se desprenda de la regla o con el contraataque "
                      "que impediría que el poder fuera invencible.")
        story_guide = ("Define la regla sin rodeos, ilustra dos aplicaciones concretas, establece su límite y "
                       "muestra cómo alguien podría explotarlo o contrarrestarlo.")
        ending_guide = ("Pregunta qué uso o contraataque sería más efectivo, y por qué; la respuesta debe "
                        "depender de la regla y el límite explicados.")
    elif "conceptos originales" in category_key:
        pattern = "CONCEPTO ORIGINAL CON DILEMA"
        hook_guide = ("Lanza una regla rara con una consecuencia clara o plantea el dilema que esa regla "
                      "obligaría a resolver; evita describir primero el concepto de forma enciclopédica.")
        story_guide = ("Explica la regla, demuestra un uso ingenioso, deja claro el coste y construye un dilema "
                       "breve donde usar el poder también traiga una consecuencia.")
        ending_guide = ("Pregunta qué decisión tomarían ante ese dilema o qué uso alternativo encontraron; "
                        "la pregunta debe apoyarse en el coste descrito.")
    elif any(term in subject for term in ("stand", "habilidad", "poder", "técnica", "capacidad")):
        pattern = "MECÁNICA, APLICACIÓN Y LÍMITE"
        hook_guide = ("Abre con una consecuencia concreta, un límite que sorprenda o una aplicación táctica "
                      "que el público pueda imaginar. Evita '¿Qué pasaría si...?' como plantilla automática.")
        story_guide = ("Explica la regla central, qué afecta, da ejemplos visuales distintos, aclara el límite "
                       "conocido y termina el desarrollo con una aplicación o consecuencia táctica.")
        ending_guide = ("Pregunta qué aplicación sería más fuerte o qué límite ofrece el mejor contraataque; "
                        "usa un detalle de la habilidad para provocar argumentos concretos.")
    else:
        pattern = "NARRATIVA A MEDIDA"
        hook_guide = ("Encuentra el dato, contradicción, apuesta o consecuencia más concreta de la idea y "
                      "empieza ahí; evita una pregunta intercambiable con cualquier tema.")
        story_guide = ("Haz una progresión propia: contexto mínimo, mecanismo o causa, ejemplo, giro y "
                       "consecuencia. Cada beat debe añadir información nueva.")
        ending_guide = ("Formula una pregunta sobre la consecuencia o explicación central que admita "
                        "hipótesis distintas y argumentos apoyados por el guion.")
    if "crazy diamond" in subject and "josuke" in subject:
        hook_guide = ("Presenta como teoría que la evolución podría proteger a Josuke reparando sus propias heridas; "
                      "la sorpresa es que le permitiría resistir, no que lo volvería invencible.")
        story_guide = ("Desarrolla solo esta hipótesis: Crazy Diamond podría restaurar las heridas de Josuke y "
                       "ayudarlo a resistir durante una pelea. Distingue recuperarse de ganar el combate y explica "
                       "que eso no lo haría invencible. No inventes efectos visuales, proceso de curación, cifras, "
                       "tiempos, límites ni habilidades nuevas; no afirmes que esto sea canon.")
        ending_guide = ("Pregunta qué límite haría plausible esta teoría sin volver invencible a Josuke; "
                        "invita a discutir la regla de restauración, no a dar una opinión genérica.")
    prompt = f"""Eres guionista de videos cortos interesantes y directos en español latinoamericano.
Crea un guion ORIGINAL para esta idea; el ejemplo de referencia solo aporta ritmo corto, claridad y progresión.
Idea: {title}
Contexto disponible: {summary or 'No se proporcionó más contexto.'}
Patrón editorial seleccionado para esta idea: {pattern}
Guía del gancho (primer beat): {hook_guide}
Recorrido del desarrollo: {story_guide}
Guía del cierre (último beat): {ending_guide}
Duración: {duration} segundos; apunta a unas 80 palabras.
Devuelve solo JSON con esta forma:
{{"beats":[{{"text":"frase","delivery":"curious|narrator|emphatic"}}]}}
Condiciones:
- Escribe exactamente 8 beats, con 8–13 palabras cada uno (72–96 palabras en total). Busca unas 80 palabras para que el guion sostenga la duración; no acortes omitiendo los pasos del patrón.
- El primer beat debe funcionar en los primeros 3–5 segundos: ve al hecho, rareza, riesgo, contradicción o resultado que hace única esta idea. Entrega enseguida la promesa del título; nada de saludos, contexto largo ni frases como “hoy vamos a hablar de”.
- Usa el ángulo indicado como guía, no copies una fórmula literal. Varía el tipo de gancho entre ideas; no empieces todos los guiones con “¿Qué pasaría si...?”, “¿Sabías que...?” ni con el título reformulado.
- El último beat debe ser una pregunta breve y específica que abra una hipótesis, objeción, condición o contraataque relevante. Debe dar motivos para responderse entre espectadores; no uses “¿Qué opinas?”, “¿Estás de acuerdo?” ni “déjalo en comentarios”. Sigue la guía de cierre de este patrón.
- No uses signos de pregunta en los beats intermedios.
- Mantén cada beat entre 8 y 13 palabras y evita repetir la misma condición o idea.
- Sigue la guía propia de este patrón; cada idea debe tener gancho, progresión y pregunta final nacidos de su mecánica y detalles, sin reutilizar un molde intercambiable.
- El título y el contexto son la única base factual. No agregues escenas, lugares, poderes ni consecuencias como si fueran hechos confirmados.
- Si es una evolución/hipótesis, marca una sola vez que es teoría. Presenta sus efectos en condicional y amplía la mecánica original solo un paso.
- No inventes cifras, duraciones, escenas ni límites específicos ausentes del contexto; una posibilidad no se afirma como hecho canónico.
- No agregues habilidades mentales/espirituales ni energía universal, salvo que la idea lo proponga explícitamente.
- Usa palabras cotidianas y ejemplos visualizables; evita metáforas abstractas como “distancia entre corazones”.
- Cada beat aporta un dato, ejemplo o consecuencia diferente; evita relleno y repetir ideas.
- Sin introducción genérica, frases meta ni llamada “déjalo en comentarios”.
- Tono conversacional, directo, expresivo y claro; no tráiler ni locutor solemne.
- Usa curious en el gancho y narrator para explicar. Reserva emphatic para un giro real.
- Para Qwen 3, responde sin razonamiento interno y entrega solo el JSON.
"""
    schema = {"type": "object", "properties": {"beats": {
        "type": "array", "minItems": 8, "maxItems": 8,
        "items": {"type": "object", "properties": {
            "text": {"type": "string"}, "delivery": {"type": "string",
                "enum": ["curious", "narrator", "emphatic"]}},
            "required": ["text", "delivery"], "additionalProperties": False}}},
        "required": ["beats"], "additionalProperties": False}
    narration = None
    last_issue = ""
    for attempt in range(2):
        if attempt == 0:
            user_prompt = prompt
        else:
            user_prompt = (prompt + "\nCORRIGE ESTE BORRADOR: cumple exactamente 8 beats, 8–13 palabras por beat "
                           "(72–96 palabras total), conserva el patrón, elimina preguntas antes del último beat, "
                           "no inventes cifras o hechos y termina con una pregunta específica. Reescribe, no expliques. "
                           f"Problema detectado: {last_issue}\nBorrador anterior: "
                           + json.dumps(narration, ensure_ascii=False))
        payload = json.dumps({"model": model, "stream": False, "format": schema, "messages": [
            {"role": "system", "content": "Escribe solo el guion pedido, sin explicar tu razonamiento."},
            {"role": "user", "content": user_prompt + "\n/no_think"}],
            "think": False, "keep_alive": 0, "options": {"temperature": 0.55, "top_p": 0.9, "repeat_penalty": 1.16,
                                         "num_ctx": 4096, "num_predict": 520}}).encode()
        request = urllib.request.Request(base + "/api/chat", data=payload,
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                result = json.loads(response.read().decode())
            narration = json.loads(result["message"]["content"])
        except (OSError, urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            if attempt == 0:
                last_issue = f"respuesta no válida ({exc})"
                continue
            raise RuntimeError(f"No se pudo generar el guion local con Ollama ({model}): {exc}") from exc
        beats = narration.get("beats") if isinstance(narration, dict) else None
        if not isinstance(beats, list) or len(beats) != 8:
            last_issue = "el borrador no contiene exactamente 8 beats"
            continue
        if any(not isinstance(beat, dict) or not str(beat.get("text", "")).strip() for beat in beats):
            last_issue = "hay beats vacíos"
            continue
        if "¿" not in str(beats[-1]["text"]) or "?" not in str(beats[-1]["text"]):
            closing_questions = {
                "HIPÓTESIS DE EVOLUCIÓN": ("¿Qué límite evitaría que reparar heridas volviera invencible a Josuke?"
                    if "crazy diamond" in subject and "josuke" in subject else "¿Qué límite impediría que esta evolución rompiera las reglas conocidas?"),
                "FUSIÓN DE HABILIDADES": "¿Qué incompatibilidad frenaría más esta fusión y qué habilidad ganaría?",
                "ENFRENTAMIENTO CON VEREDICTO CONDICIONAL": "¿Qué condición cambiaría el resultado de este duelo y por qué?",
                "LÍNEA TEMPORAL ALTERNATIVA": "¿Qué consecuencia de este cambio creen más probable y por qué?",
                "REVELACIÓN E HISTORIA": "¿Qué pista respalda mejor esta interpretación de la historia?",
                "PODER HIPOTÉTICO Y CONTRAJUEGO": "¿Qué contraataque sería más efectivo contra este poder y por qué?",
                "CONCEPTO ORIGINAL CON DILEMA": "¿Qué decisión tomarías sabiendo que usarlo también tiene un coste?",
                "MECÁNICA, APLICACIÓN Y LÍMITE": "¿Qué aplicación sería más fuerte sin romper este límite?",
                "NARRATIVA A MEDIDA": "¿Qué explicación alternativa encaja mejor con los datos narrados?",
            }
            beats[-1]["text"] = closing_questions[pattern]
        words = sum(len(str(beat["text"]).split()) for beat in beats)
        if not 72 <= words <= 96:
            last_issue = f"el total es de {words} palabras en lugar de 72–96"
            continue
        break
    else:
        raise ValueError(f"El borrador local no cumplió los límites editoriales tras dos intentos: {last_issue}")
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
