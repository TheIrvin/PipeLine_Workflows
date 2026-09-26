"""Text AI provider interface and deterministic mock implementation."""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Protocol, Sequence


class TextAIProvider(Protocol):
    def generate_ideas(
        self,
        count: int,
        existing_ideas: Sequence[dict],
        categories: Sequence[str],
    ) -> list[dict]:
        """Return structured, novel idea records."""


def normalize_name(value: str) -> str:
    """Normalize an idea title for accent- and punctuation-insensitive matching."""
    ascii_text = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(char for char in ascii_text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def is_duplicate(candidate: str, existing: Sequence[str], threshold: float = 0.93) -> bool:
    normalized = normalize_name(candidate)
    if not normalized:
        return True
    for value in existing:
        other = normalize_name(value)
        if normalized == other or SequenceMatcher(None, normalized, other).ratio() >= threshold:
            return True
    return False


class MockTextAIProvider:
    """Deterministic provider for development without network calls or API keys."""

    _catalog = [
        ("Fusiones de Stands", "¿Qué habilidades tendría una fusión entre Star Platinum y Crazy Diamond?", "Explorar cómo se combinarían la precisión de Star Platinum y la restauración de Crazy Diamond."),
        ("Fusiones de Stands", "¿Cómo cambiaría el combate si Killer Queen pudiera detener el tiempo?", "Imaginar límites y consecuencias para una habilidad explosiva durante una pausa temporal."),
        ("Fusiones de Stands", "¿Qué pasaría si Gold Experience pudiera reparar objetos como Crazy Diamond?", "Comparar la creación de vida con la reparación directa en situaciones de combate."),
        ("Fusiones de Stands", "¿Qué estrategia surgiría al combinar King Crimson y The World?", "Contrastar la eliminación de tiempo con la detención temporal."),
        ("Fusiones de Stands", "¿Cómo sería un Stand que mezclara Sticky Fingers y Stone Free?", "Diseñar usos creativos de cierres y fibras para movilidad y defensa."),
        ("Evoluciones/Requiem", "¿Qué habilidad Requiem podría despertar Silver Chariot?", "Proponer una evolución que refleje la determinación y velocidad de Polnareff."),
        ("Evoluciones/Requiem", "¿Cómo evolucionaría Crazy Diamond al proteger a Josuke?", "Explorar una evolución centrada en restaurar algo más que objetos físicos."),
        ("Evoluciones/Requiem", "¿Qué límite tendría Gold Experience Requiem ante una paradoja?", "Plantear un dilema narrativo sobre causa, efecto y voluntad."),
        ("Evoluciones/Requiem", "¿Qué forma final alcanzaría Stone Free en una batalla decisiva?", "Imaginar una evolución coherente con la libertad y creatividad de Jolyne."),
        ("Evoluciones/Requiem", "¿Cómo cambiaría Tusk Act 4 con una nueva habilidad defensiva?", "Diseñar una mejora que complemente la rotación infinita sin volverlo invencible."),
        ("What If", "¿Qué habría pasado si Jotaro llegaba antes al enfrentamiento con Kira?", "Revisar cómo cambiarían las decisiones y el desenlace con otra llegada."),
        ("What If", "¿Y si Bruno Bucciarati hubiera sobrevivido al final de Golden Wind?", "Imaginar el futuro del grupo y de Passione tras la derrota de Diavolo."),
        ("What If", "¿Qué ocurriría si Joseph conociera a Jolyne antes de Stone Ocean?", "Explorar cómo la experiencia de Joseph influiría en el destino de Jolyne."),
        ("What If", "¿Y si Dio hubiera encontrado la flecha antes de conocer a Enya?", "Proponer una ruta alternativa para el origen y los límites de su Stand."),
        ("What If", "¿Qué cambiaría si Josuke viajara con los Crusaders a Egipto?", "Comparar cómo sus habilidades médicas afectarían al viaje contra Dio."),
        ("Enfrentamientos", "¿Quién tendría ventaja: Josuke o Giorno sin GER?", "Comparar alcance, creatividad y condiciones de victoria de ambos Stands."),
        ("Enfrentamientos", "¿Podría Foo Fighters superar a Weather Report en un duelo?", "Analizar ventajas ambientales, alcance y resistencia de los dos combatientes."),
        ("Enfrentamientos", "¿Qué equipo ganaría: los Crusaders o el grupo de Bucciarati?", "Evaluar sinergia, experiencia y habilidades en un enfrentamiento por equipos."),
        ("Enfrentamientos", "¿Puede Mista encontrar una forma de vencer a Risotto Nero?", "Plantear un duelo táctico entre Sex Pistols y Metallica."),
        ("Enfrentamientos", "¿Cómo sería un duelo entre Rohan Kishibe y D'Arby?", "Comparar lectura, engaño y control de las reglas del enfrentamiento."),
        ("Poderes hipotéticos", "¿Qué tres usos no obvios tendría Hermit Purple fuera del combate?", "Mostrar aplicaciones de rastreo y comunicación sin cambiar el poder base."),
        ("Poderes hipotéticos", "¿Cómo podría funcionar un Stand que almacena un segundo de movimiento?", "Definir reglas, costes y usos para un poder original de almacenamiento temporal."),
        ("Poderes hipotéticos", "¿Qué debilidad equilibraría un Stand capaz de copiar sonidos?", "Diseñar una limitación clara que permita contrajuego y tensión narrativa."),
        ("Poderes hipotéticos", "¿Cómo usaría Jolyne un Stand que convierte sombras en hilos?", "Probar aplicaciones defensivas y de movimiento para una habilidad hipotética."),
        ("Poderes hipotéticos", "¿Qué reglas tendría un Stand que intercambia el peso de dos objetos?", "Explorar alcance, duración y consecuencias de una habilidad física original."),
        ("Conceptos originales", "Un Stand que solo puede atacar mientras su usuario dice la verdad", "Crear un concepto con una regla narrativa que obligue al usuario a ser estratégico."),
        ("Conceptos originales", "Un Stand que convierte recuerdos en objetos temporales", "Diseñar un poder visual y sus costes emocionales para una historia corta."),
        ("Conceptos originales", "Un Stand que cambia la dirección de cualquier sonido cercano", "Explorar cómo una habilidad auditiva puede servir para engañar y defenderse."),
        ("Conceptos originales", "Un Stand que dibuja puertas sobre superficies planas", "Definir límites espaciales y usos de infiltración para una habilidad original."),
        ("Conceptos originales", "Un Stand que divide un objeto en versiones de distintos materiales", "Proponer una habilidad creativa con reglas claras y aplicaciones visuales."),
    ]

    def generate_ideas(
        self,
        count: int,
        existing_ideas: Sequence[dict],
        categories: Sequence[str],
    ) -> list[dict]:
        if count <= 0:
            return []
        allowed = {normalize_name(category) for category in categories}
        existing = [str(row.get("idea", "")) for row in existing_ideas]
        candidates = []
        for category, title, summary in self._catalog:
            if allowed and normalize_name(category) not in allowed:
                continue
            if is_duplicate(title, existing + [row["idea"] for row in candidates]):
                continue
            candidates.append({
                "idea": title,
                "tipo": category,
                "resumen": summary,
                "duracion_objetivo": 45,
                "prioridad": 5,
            })
            if len(candidates) >= count:
                break
        return candidates
