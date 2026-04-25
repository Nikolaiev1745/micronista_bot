"""
scraper.py — Lectura de feeds RSS y extracción del cuerpo de artículos.

fetch_new_articles() guarda el contenido completo en la DB (cache global).
El filtrado por keywords y fuentes se hace luego, por usuario, en bot.py.
"""

import logging
import requests
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from config import RSS_SOURCES, MAX_ARTICLES_PER_RUN
from database import Database

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
REQUEST_TIMEOUT = 15


class FeedScraper:
    def __init__(self, db: Database = None):
        self.db = db or Database()

    def fetch_new_articles(self) -> list[dict]:
        """
        Descarga todos los feeds globales, extrae el cuerpo de los artículos
        nuevos (no en cache) y los guarda en seen_articles.
        Retorna la lista de artículos recién procesados.
        """
        candidates = []
        for source_name, feed_url in RSS_SOURCES.items():
            try:
                entries = self._parse_feed(feed_url, source_name)
                candidates.extend(entries)
            except Exception as exc:
                logger.warning("Error en feed '%s': %s", source_name, exc)

        new_articles = []
        for article in candidates:
            if len(new_articles) >= MAX_ARTICLES_PER_RUN * 3:  # límite de descarga por ciclo
                break
            if self.db.is_seen(article["url"]):
                continue
            article["body"] = self._extract_body(article["url"])
            self.db.mark_seen(article)
            new_articles.append(article)

        logger.info("%d artículos nuevos descargados y cacheados.", len(new_articles))
        return new_articles

    @staticmethod
    def matches_keywords(article: dict, keywords: list[str]) -> bool:
        """Filtra un artículo contra una lista de keywords (case-insensitive)."""
        text = (article.get("title", "") + " " + article.get("description", "")).lower()
        return any(kw.lower() in text for kw in keywords)

    def _parse_feed(self, feed_url: str, source_name: str) -> list[dict]:
        response = requests.get(feed_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)

        articles = []
        for item in items:
            def get(tag, atom_tag=None, _item=item):
                node = _item.find(tag)
                if node is None and atom_tag:
                    node = _item.find(atom_tag, ns)
                return (node.text or "").strip() if node is not None else ""

            url = get("link")
            if not url:
                link_node = item.find("atom:link", ns)
                if link_node is not None:
                    url = link_node.get("href", "")
            if not url:
                continue

            description = _strip_html(
                get("description") or get("summary", "atom:summary")
            )

            articles.append({
                "source":      source_name,
                "url":         url,
                "title":       get("title", "atom:title") or "Sin título",
                "author":      get("author") or get("dc:creator") or "",
                "published":   get("pubDate") or get("published", "atom:published") or "",
                "description": description[:500],
                "body":        "",
            })

        return articles

    def _extract_body(self, url: str) -> str:
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
            article = soup.find("article") or soup.find(
                class_=["article-body", "post-content", "entry-content", "content"]
            )
            target = article if article else soup.find("body")
            text = target.get_text(separator="\n", strip=True) if target else ""
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            return "\n".join(lines)
        except Exception as exc:
            logger.debug("No se pudo extraer cuerpo de %s: %s", url, exc)
            return ""


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()
