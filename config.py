"""
config.py — Configuración central del bot de noticias.
Editá KEYWORDS y RSS_SOURCES según tus intereses.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Credenciales (desde .env) ─────────────────────────────────────────────────
TELEGRAM_TOKEN   = (os.getenv("TELEGRAM_TOKEN") or "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_CHAT_ID    = os.getenv("ADMIN_CHAT_ID")  # opcional: tu chat_id para logs

# ── Comportamiento del scheduler ─────────────────────────────────────────────
CHECK_INTERVAL_MINUTES = 60   # cada cuántos minutos se chequean los feeds
MAX_ARTICLES_PER_RUN   = 10   # límite de artículos enviados por ciclo (evita spam)

# ── Palabras clave ────────────────────────────────────────────────────────────
# Si UN artículo contiene al menos UNA de estas palabras (en título o descripción)
# es seleccionado para resumir y enviar.
KEYWORDS = [
    # Política & geopolítica
    "geopolítica", "geopolitics", "guerra", "war", "conflicto", "conflict",
    "democracia", "democracy", "autoritarismo", "authoritarianism",
    "ultraderecha", "far-right", "extrema derecha", "extrema derecha", "populismo", "populism",
    "Marco Rubio", "JD Vance", "Vivek Ramaswamy", "Donald Trump",
    "elecciones", "elections", "parlamento", "congress", "senate",
    "diplomacia", "diplomacy", "OTAN", "NATO", "Unión Europea", "European Union",

    # Economía & sociedad
    "economía", "economy", "inflación", "inflation", "recesión", "recession",
    "desigualdad", "inequality", "pobreza", "poverty",
    "energía", "energy", "petróleo", "oil", "transición energética",

    # Tecnología & ciencia
    "Palantir", "OpenAI", "Peter Thiel", "Sam Altman", "Alex Karp", "Nvidea",
    "desinformación", "disinformation", "censura", "censorship",

    # América Latina
    "Argentina", "Brasil", "México", "Venezuela", "Colombia", "Chile",
    "América Latina", "Latin America", "Latinoamérica",
]

# ── Fuentes RSS ───────────────────────────────────────────────────────────────
# Formato: "Nombre visible": "URL del feed RSS"
RSS_SOURCES = {
    # ── Análisis y pensamiento ───────────────────────────────────────────────
    "Le Grand Continent (ES)": "https://legrandcontinent.eu/es/feed/",
    "CTXT":                    "https://ctxt.es/es/feed.rss",
    "Project Syndicate":       "https://www.project-syndicate.org/rss",
    "Foreign Affairs":         "https://www.foreignaffairs.com/rss.xml",
    "Foreign Policy":          "https://foreignpolicy.com/feed/",
    "The Atlantic":            "https://www.theatlantic.com/feed/all/",
    "Jacobin (ES)":            "https://jacobinlat.com/feed/",

    # ── Medios internacionales EN ────────────────────────────────────────────
    "Reuters (World)":         "https://feeds.reuters.com/reuters/worldnews",    "The Guardian (World)":    "https://www.theguardian.com/world/rss",
    "BBC World":               "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera English":      "https://www.aljazeera.com/xml/rss/all.xml",

    # ── Medios en español ────────────────────────────────────────────────────
    "BBC Mundo":               "https://feeds.bbci.co.uk/mundo/rss.xml",
    "El País":                 "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "Infobae":                 "https://www.infobae.com/feeds/rss/politica/",
    "La Nación (AR)":          "https://servicios.lanacion.com.ar/herramientas/rss/categoria/id/3",
    "Clarín":                  "https://www.clarin.com/rss/politica/",
    "El Destape":              "https://www.eldestapeweb.com/rss.xml",
}
