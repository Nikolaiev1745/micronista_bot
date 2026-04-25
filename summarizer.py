"""
summarizer.py — Genera resúmenes de artículos usando Google Gemini (gratis).

Tier gratuito de Gemini 1.5 Flash:
  - 15 requests/minuto
  - 1.500 requests/día
  - 1 millón de tokens de contexto por request

Si el artículo tiene cuerpo extraído, lo usa como contexto completo.
Si no, trabaja solo con el título y la descripción del RSS.
El resultado es texto Markdown listo para enviar por Telegram.
"""

import logging
import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Máximo de caracteres del cuerpo enviados al modelo (~1000 tokens)
# (evita tokens excesivos; ~4000 chars ≈ 1000 tokens)
MAX_BODY_CHARS = 4000

SUMMARY_PROMPT = """\
Eres un editor periodístico experto. A partir de la información del artículo \
que se te proporciona, genera un resumen conciso y claro para una audiencia \
interesada en política, geopolítica, economía y análisis internacional.

El resumen debe seguir ESTRICTAMENTE este formato Markdown para Telegram:

*[TÍTULO DEL ARTÍCULO]*
📰 _[FUENTE]_ · _[AUTOR si hay, o "Redacción"]_ · _[FECHA si hay]_

[2-3 oraciones que expliquen de qué trata el artículo, cuál es su tesis \
central o qué evento describe, y por qué es relevante. Sé directo y sustancioso. \
No uses frases vacías como "En este artículo se analiza..."]

🔗 [Leer artículo completo]({URL})

---
Información del artículo:
Fuente: {source}
Título: {title}
Autor: {author}
Fecha: {published}
Descripción RSS: {description}
Cuerpo del artículo (puede estar truncado):
{body}
"""


class ArticleSummarizer:
    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config=genai.GenerationConfig(
                    max_output_tokens=400,
                    temperature=0.3,
                ),
            )
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY no configurada: se usará formato sin IA.")

    def summarize(self, article: dict) -> str | None:
        """
        Genera un resumen en Markdown para Telegram.
        Retorna None si ocurre un error crítico.
        """
        if not self.model:
            return self._fallback_format(article)

        body = article.get("body", "")[:MAX_BODY_CHARS]

        if not body and not article.get("description"):
            return self._fallback_format(article)

        prompt = SUMMARY_PROMPT.format(
            source=article.get("source", ""),
            title=article.get("title", ""),
            author=article.get("author", "") or "Redacción",
            published=article.get("published", ""),
            description=article.get("description", ""),
            body=body or "(no disponible)",
            URL=article.get("url", ""),
        )

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            logger.info("Resumen generado para: %s", article.get("title", "")[:60])
            return text

        except Exception as exc:
            logger.error("Error en Gemini API: %s", exc)
            return self._fallback_format(article)

    # ── Fallback cuando la API no está disponible ─────────────────────────────

    def _fallback_format(self, article: dict) -> str:
        """Formato mínimo sin IA, solo con los datos del RSS."""
        title  = article.get("title", "Sin título")
        source = article.get("source", "")
        author = article.get("author", "") or "Redacción"
        date   = article.get("published", "")
        desc   = article.get("description", "")
        url    = article.get("url", "")

        meta = f"📰 _{source}_ · _{author}_"
        if date:
            meta += f" · _{date}_"

        parts = [f"*{title}*", meta]
        if desc:
            parts.append(desc)
        parts.append(f"🔗 [Leer artículo completo]({url})")
        parts.append("---")

        return "\n".join(parts)
