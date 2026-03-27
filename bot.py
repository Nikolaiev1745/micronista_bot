"""
bot.py — Bot de Telegram con sistema de suscripción y scheduler.

Comandos disponibles:
  /start   — Suscribirse al bot
  /stop    — Darse de baja
  /fuentes — Ver las fuentes monitoreadas
  /temas   — Ver las palabras clave activas
  /estado  — Info del bot (solo admin)
"""

import logging
import asyncio
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TELEGRAM_TOKEN, CHECK_INTERVAL_MINUTES, RSS_SOURCES, KEYWORDS, ADMIN_CHAT_ID
from database import Database
from scraper import FeedScraper
from summarizer import ArticleSummarizer

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("newsbot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Instancias globales ───────────────────────────────────────────────────────
db         = Database()
scraper    = FeedScraper(db=db)
summarizer = ArticleSummarizer()


# ── Handlers de comandos ──────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id  = update.effective_chat.id
    username = update.effective_user.username or update.effective_user.first_name

    is_new = db.subscribe(chat_id, username)

    if is_new:
        msg = (
            "✅ *¡Suscripción activada!*\n\n"
            f"Hola {username}, vas a recibir alertas con resúmenes de artículos "
            "de medios internacionales cuando haya novedades relevantes.\n\n"
            "Comandos disponibles:\n"
            "• /fuentes — Ver medios monitoreados\n"
            "• /temas — Ver palabras clave activas\n"
            "• /stop — Cancelar suscripción"
        )
    else:
        msg = (
            "ℹ️ Ya estás suscripto/a. "
            "Te avisaremos cuando haya artículos nuevos.\n"
            "Usá /stop para cancelar la suscripción."
        )

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    was_subscribed = db.unsubscribe(chat_id)

    if was_subscribed:
        msg = "❌ *Suscripción cancelada.* Ya no recibirás más alertas.\nPodés volver a suscribirte con /start."
    else:
        msg = "No estabas suscripto/a. Usá /start para suscribirte."

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_fuentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["📡 *Fuentes monitoreadas:*\n"]
    for name, url in RSS_SOURCES.items():
        lines.append(f"• [{name}]({url})")
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def cmd_temas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kws = ", ".join(f"`{k}`" for k in KEYWORDS)
    msg = f"🔍 *Palabras clave activas:*\n\n{kws}"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def cmd_ahora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fuerza un chequeo inmediato de feeds."""
    if ADMIN_CHAT_ID and str(update.effective_chat.id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔ Comando reservado para el administrador.")
        return
    await update.message.reply_text("🔄 Chequeando feeds ahora...")
    await job_check_and_send(context.application)

async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando solo para el admin: muestra estadísticas del bot."""
    if ADMIN_CHAT_ID and str(update.effective_chat.id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔ Comando reservado para el administrador.")
        return

    count = db.subscriber_count()
    msg = (
        f"🤖 *Estado del bot*\n\n"
        f"👥 Suscriptores activos: *{count}*\n"
        f"📡 Fuentes monitoreadas: *{len(RSS_SOURCES)}*\n"
        f"🔍 Palabras clave: *{len(KEYWORDS)}*\n"
        f"⏱ Intervalo de chequeo: *{CHECK_INTERVAL_MINUTES} min*"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


# ── Job del scheduler ─────────────────────────────────────────────────────────

async def job_check_and_send(app: Application):
    """
    Tarea periódica: busca artículos nuevos y los envía a todos los suscriptores.
    """
    logger.info("⏰ Iniciando ciclo de chequeo de feeds...")

    try:
        articles = scraper.fetch_new_articles()
    except Exception as exc:
        logger.error("Error al scrapear feeds: %s", exc)
        return

    if not articles:
        logger.info("Sin artículos nuevos en este ciclo.")
        return

    subscribers = db.get_subscribers()
    if not subscribers:
        logger.info("No hay suscriptores, descartando %d artículo(s).", len(articles))
        return

    logger.info(
        "Enviando %d artículo(s) a %d suscriptor(es).",
        len(articles), len(subscribers)
    )

    for article in articles:
        message = summarizer.summarize(article)
        if not message:
            continue

        for chat_id in subscribers:
            try:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=False,
                )
            except Exception as exc:
                logger.warning("Error enviando a chat_id %s: %s", chat_id, exc)

        # Pequeña pausa entre artículos para no saturar
        await asyncio.sleep(1.5)

    # Limpieza mensual de artículos viejos
    db.cleanup_old_articles(days=30)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("Falta TELEGRAM_TOKEN en el archivo .env")
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY no configurada: se usará formato sin IA.")

    # Construir la aplicación de Telegram
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    # Registrar comandos
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("stop",    cmd_stop))
    app.add_handler(CommandHandler("fuentes", cmd_fuentes))
    app.add_handler(CommandHandler("temas",   cmd_temas))
    app.add_handler(CommandHandler("estado",  cmd_estado))
    app.add_handler(CommandHandler("ahora", cmd_ahora))

    # Configurar comandos visibles en el menú de Telegram
    async def set_commands(app):
        await app.bot.set_my_commands([
            BotCommand("start",   "Suscribirse a las alertas"),
            BotCommand("stop",    "Cancelar suscripción"),
            BotCommand("fuentes", "Ver fuentes monitoreadas"),
            BotCommand("temas",   "Ver palabras clave activas"),
            BotCommand("ahora", "Forzar chequeo inmediato (admin)"),
        ])

    app.post_init = set_commands

    # Configurar scheduler asíncrono
    scheduler = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")
    scheduler.add_job(
        job_check_and_send,
        trigger="interval",
        minutes=CHECK_INTERVAL_MINUTES,
        args=[app],
        id="check_feeds",
        replace_existing=True,
        max_instances=1,           # evita solapamiento si tarda más de lo previsto
    )
    scheduler.start()
    logger.info(
        "✅ Scheduler iniciado. Chequeo cada %d minutos.", CHECK_INTERVAL_MINUTES
    )

    # Arrancar el bot (bloquea hasta Ctrl+C)
    logger.info("🤖 Bot iniciado. Esperando mensajes...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    from config import GEMINI_API_KEY  # re-import para el warning
    main()
