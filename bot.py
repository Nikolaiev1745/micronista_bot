"""
bot.py — Bot de Telegram con personalización por usuario y scheduler.

Comandos generales:
  /start           — Suscribirse al bot
  /stop            — Darse de baja
  /ayuda           — Ver todos los comandos

Personalización:
  /mistemas        — Ver tus palabras clave activas
  /agregartema     — Agregar una palabra clave
  /eliminartema    — Eliminar una palabra clave
  /reseteartemas   — Volver a las palabras clave globales
  /misfuentes      — Ver y gestionar tus fuentes
  /activarfuente   — Activar una fuente por número
  /desactivarfuente— Desactivar una fuente por número
  /resetearfuentes — Volver a usar todas las fuentes
  /mifrecuencia    — Ver tu frecuencia de chequeo
  /cambiafrecuencia— Cambiar la frecuencia (en minutos)
  /miconfig        — Resumen de toda tu configuración

Admin:
  /estado          — Estadísticas del bot
  /ahora           — Forzar chequeo inmediato
"""

import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import (
    TELEGRAM_TOKEN, CHECK_INTERVAL_MINUTES, RSS_SOURCES,
    KEYWORDS, ADMIN_CHAT_ID, MAX_ARTICLES_PER_RUN,
)
from database import Database
from scraper import FeedScraper
from summarizer import ArticleSummarizer

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.getenv("LOG_PATH", "newsbot.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# El scheduler corre cada 15 min como mínimo.
# La frecuencia de cada usuario puede ser mayor (30, 60, 120... minutos).
BASE_TICK_MINUTES = 15
MIN_USER_INTERVAL = 15
MAX_USER_INTERVAL = 1440  # 24 horas

# ── Instancias globales ───────────────────────────────────────────────────────
db         = Database()
scraper    = FeedScraper(db=db)
summarizer = ArticleSummarizer()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_effective_keywords(chat_id: int) -> list[str]:
    """Keywords del usuario, o globales si no configuró las suyas."""
    custom = db.get_user_keywords(chat_id)
    return custom if custom else list(KEYWORDS)

def _get_effective_sources(chat_id: int) -> list[str]:
    """Fuentes habilitadas del usuario, o todas las globales si no configuró."""
    user_src = db.get_user_sources(chat_id)
    if not user_src:
        return list(RSS_SOURCES.keys())
    return [name for name, enabled in user_src.items() if enabled]

def _get_effective_interval(chat_id: int) -> int:
    """Intervalo del usuario, o el global si no lo cambió."""
    return db.get_user_interval(chat_id) or CHECK_INTERVAL_MINUTES

def _is_user_due(chat_id: int) -> bool:
    """¿Ya pasó suficiente tiempo desde el último envío a este usuario?"""
    last = db.get_last_checked(chat_id)
    if not last:
        return True
    elapsed_min = (datetime.utcnow() - datetime.fromisoformat(last)).total_seconds() / 60
    return elapsed_min >= _get_effective_interval(chat_id)

def _source_list_text(chat_id: int) -> str:
    """Genera texto numerado de fuentes con estado ✅/❌."""
    user_src = db.get_user_sources(chat_id)
    lines = []
    for i, (name, url) in enumerate(RSS_SOURCES.items(), 1):
        if user_src:
            enabled = user_src.get(name, True)
        else:
            enabled = True
        icon = "✅" if enabled else "❌"
        lines.append(f"{icon} `{i}.` {name}")
    return "\n".join(lines)


# ── Handlers generales ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id  = update.effective_chat.id
    username = update.effective_user.username or update.effective_user.first_name
    is_new = db.subscribe(chat_id, username)

    if is_new:
        msg = (
            "✅ *¡Suscripción activada!*\n\n"
            f"Hola {username}, vas a recibir alertas con resúmenes de artículos "
            "de medios internacionales cuando haya novedades relevantes.\n\n"
            "Por defecto usás las palabras clave y fuentes globales, "
            "pero podés personalizar todo:\n\n"
            "• /mistemas — Ver y editar tus palabras clave\n"
            "• /misfuentes — Activar/desactivar fuentes\n"
            "• /mifrecuencia — Cambiar frecuencia de alertas\n"
            "• /miconfig — Ver toda tu configuración\n"
            "• /ayuda — Ver todos los comandos\n"
            "• /stop — Cancelar suscripción"
        )
    else:
        msg = (
            "ℹ️ Ya estás suscripto/a.\n"
            "Usá /miconfig para ver tu configuración actual o /stop para darte de baja."
        )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    was_subscribed = db.unsubscribe(chat_id)
    if was_subscribed:
        msg = "❌ *Suscripción cancelada.* Ya no recibirás más alertas.\nPodés volver con /start."
    else:
        msg = "No estabas suscripto/a. Usá /start para suscribirte."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Comandos disponibles*\n\n"
        "*Suscripción*\n"
        "• /start — Suscribirse\n"
        "• /stop — Darse de baja\n\n"
        "*Palabras clave*\n"
        "• /mistemas — Ver tus palabras clave\n"
        "• /agregartema `<palabra>` — Agregar una\n"
        "• /eliminartema `<palabra>` — Eliminar una\n"
        "• /reseteartemas — Volver a las globales\n\n"
        "*Fuentes*\n"
        "• /misfuentes — Ver y gestionar fuentes\n"
        "• /activarfuente `<número>` — Activar fuente\n"
        "• /desactivarfuente `<número>` — Desactivar fuente\n"
        "• /resetearfuentes — Volver a usar todas\n\n"
        "*Frecuencia*\n"
        "• /mifrecuencia — Ver tu frecuencia actual\n"
        "• /cambiafrecuencia `<minutos>` — Cambiarla\n\n"
        "*Mi configuración*\n"
        "• /miconfig — Resumen de todo\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


# ── Palabras clave ────────────────────────────────────────────────────────────

async def cmd_mistemas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    custom = db.get_user_keywords(chat_id)
    if custom:
        kws = "\n".join(f"• `{k}`" for k in sorted(custom))
        msg = f"🔍 *Tus palabras clave personalizadas:*\n\n{kws}\n\nUsá /eliminartema para quitar una o /reseteartemas para volver a las globales."
    else:
        kws = ", ".join(f"`{k}`" for k in KEYWORDS)
        msg = f"🔍 *Estás usando las palabras clave globales:*\n\n{kws}\n\nUsá /agregartema para agregar las tuyas propias."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_agregartema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text(
            "❗ Uso: /agregartema `<palabra>`\nEjemplo: /agregartema Bitcoin",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    keyword = " ".join(context.args).strip()
    if len(keyword) < 2:
        await update.message.reply_text("❗ La palabra clave es muy corta.")
        return
    is_new = db.add_user_keyword(chat_id, keyword)
    if is_new:
        await update.message.reply_text(
            f"✅ `{keyword}` agregada a tus palabras clave.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"ℹ️ `{keyword}` ya estaba en tu lista.",
            parse_mode=ParseMode.MARKDOWN
        )


async def cmd_eliminartema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text(
            "❗ Uso: /eliminartema `<palabra>`\nEjemplo: /eliminartema Bitcoin",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    keyword = " ".join(context.args).strip()
    removed = db.remove_user_keyword(chat_id, keyword)
    if removed:
        custom = db.get_user_keywords(chat_id)
        extra = "\n\nTu lista quedó vacía, estás usando las palabras clave globales." if not custom else ""
        await update.message.reply_text(
            f"🗑 `{keyword}` eliminada de tus palabras clave.{extra}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"❗ `{keyword}` no estaba en tu lista. Usá /mistemas para ver las que tenés.",
            parse_mode=ParseMode.MARKDOWN
        )


async def cmd_reseteartemas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db.reset_user_keywords(chat_id)
    await update.message.reply_text(
        "🔄 Listo. Ahora usás las palabras clave globales del bot.",
        parse_mode=ParseMode.MARKDOWN
    )


# ── Fuentes ───────────────────────────────────────────────────────────────────

async def cmd_misfuentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Inicializar si es la primera vez que consulta
    if not db.get_user_sources(chat_id):
        db.init_user_sources(chat_id, list(RSS_SOURCES.keys()))

    source_text = _source_list_text(chat_id)
    msg = (
        "📡 *Tus fuentes activas:*\n\n"
        f"{source_text}\n\n"
        "Usá /activarfuente `<número>` o /desactivarfuente `<número>` para cambiarlas.\n"
        "Ej: `/desactivarfuente 3`"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_activarfuente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "❗ Uso: /activarfuente `<número>`\nVer números con /misfuentes",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    idx = int(context.args[0]) - 1
    source_names = list(RSS_SOURCES.keys())
    if idx < 0 or idx >= len(source_names):
        await update.message.reply_text("❗ Número inválido. Usá /misfuentes para ver la lista.")
        return

    source_name = source_names[idx]
    if not db.get_user_sources(chat_id):
        db.init_user_sources(chat_id, source_names)

    db.set_user_source_enabled(chat_id, source_name, True)
    await update.message.reply_text(
        f"✅ *{source_name}* activada.",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_desactivarfuente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "❗ Uso: /desactivarfuente `<número>`\nVer números con /misfuentes",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    idx = int(context.args[0]) - 1
    source_names = list(RSS_SOURCES.keys())
    if idx < 0 or idx >= len(source_names):
        await update.message.reply_text("❗ Número inválido. Usá /misfuentes para ver la lista.")
        return

    source_name = source_names[idx]
    if not db.get_user_sources(chat_id):
        db.init_user_sources(chat_id, source_names)

    # Verificar que no desactive TODAS
    user_src = db.get_user_sources(chat_id)
    enabled_count = sum(1 for e in user_src.values() if e)
    if enabled_count <= 1 and user_src.get(source_name, True):
        await update.message.reply_text(
            "❗ No podés desactivar todas las fuentes. Tenés que tener al menos una activa."
        )
        return

    db.set_user_source_enabled(chat_id, source_name, False)
    await update.message.reply_text(
        f"❌ *{source_name}* desactivada.",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_resetearfuentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db.reset_user_sources(chat_id)
    await update.message.reply_text(
        "🔄 Listo. Ahora recibís artículos de todas las fuentes globales.",
    )


# ── Frecuencia ────────────────────────────────────────────────────────────────

async def cmd_mifrecuencia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    interval = db.get_user_interval(chat_id)
    if interval:
        msg = (
            f"⏱ Tu frecuencia de chequeo es cada *{interval} minutos*.\n\n"
            f"Usá /cambiafrecuencia `<minutos>` para cambiarla.\n"
            f"Mínimo: {MIN_USER_INTERVAL} min — Máximo: {MAX_USER_INTERVAL} min (24h)"
        )
    else:
        msg = (
            f"⏱ Estás usando la frecuencia global: cada *{CHECK_INTERVAL_MINUTES} minutos*.\n\n"
            f"Usá /cambiafrecuencia `<minutos>` para personalizarla.\n"
            f"Mínimo: {MIN_USER_INTERVAL} min — Máximo: {MAX_USER_INTERVAL} min (24h)"
        )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_cambiafrecuencia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            f"❗ Uso: /cambiafrecuencia `<minutos>`\n"
            f"Ejemplo: `/cambiafrecuencia 120` (cada 2 horas)\n"
            f"Mínimo: {MIN_USER_INTERVAL} — Máximo: {MAX_USER_INTERVAL}",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    minutes = int(context.args[0])
    if minutes < MIN_USER_INTERVAL:
        await update.message.reply_text(f"❗ El mínimo es {MIN_USER_INTERVAL} minutos.")
        return
    if minutes > MAX_USER_INTERVAL:
        await update.message.reply_text(f"❗ El máximo es {MAX_USER_INTERVAL} minutos (24 horas).")
        return

    db.set_user_interval(chat_id, minutes)

    if minutes < 60:
        readable = f"{minutes} minutos"
    elif minutes == 60:
        readable = "1 hora"
    elif minutes % 60 == 0:
        readable = f"{minutes // 60} horas"
    else:
        readable = f"{minutes // 60}h {minutes % 60}min"

    await update.message.reply_text(
        f"✅ Listo. Ahora recibís alertas cada *{readable}*.",
        parse_mode=ParseMode.MARKDOWN
    )


# ── Mi configuración ──────────────────────────────────────────────────────────

async def cmd_miconfig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Keywords
    custom_kws = db.get_user_keywords(chat_id)
    if custom_kws:
        kws_line = f"🔍 *Palabras clave:* {len(custom_kws)} propias"
    else:
        kws_line = f"🔍 *Palabras clave:* globales ({len(KEYWORDS)})"

    # Fuentes
    user_src = db.get_user_sources(chat_id)
    if user_src:
        enabled = sum(1 for e in user_src.values() if e)
        total = len(user_src)
        src_line = f"📡 *Fuentes:* {enabled}/{total} activas"
    else:
        src_line = f"📡 *Fuentes:* todas las globales ({len(RSS_SOURCES)})"

    # Frecuencia
    interval = _get_effective_interval(chat_id)
    custom_int = db.get_user_interval(chat_id)
    freq_tag = "" if custom_int else " _(global)_"
    if interval < 60:
        freq_str = f"{interval} minutos"
    elif interval == 60:
        freq_str = "1 hora"
    elif interval % 60 == 0:
        freq_str = f"{interval // 60} horas"
    else:
        freq_str = f"{interval // 60}h {interval % 60}min"
    freq_line = f"⏱ *Frecuencia:* cada {freq_str}{freq_tag}"

    # Último chequeo
    last = db.get_last_checked(chat_id)
    if last:
        elapsed = int((datetime.utcnow() - datetime.fromisoformat(last)).total_seconds() / 60)
        last_line = f"🕐 *Último envío:* hace {elapsed} minutos"
    else:
        last_line = "🕐 *Último envío:* aún no recibiste nada"

    msg = (
        "⚙️ *Tu configuración actual*\n\n"
        f"{kws_line}\n"
        f"{src_line}\n"
        f"{freq_line}\n"
        f"{last_line}\n\n"
        "Usá /ayuda para ver cómo editar cada cosa."
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


# ── Comandos admin ────────────────────────────────────────────────────────────

async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_CHAT_ID and str(update.effective_chat.id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔ Comando reservado para el administrador.")
        return
    count = db.subscriber_count()
    msg = (
        f"🤖 *Estado del bot*\n\n"
        f"👥 Suscriptores activos: *{count}*\n"
        f"📡 Fuentes globales: *{len(RSS_SOURCES)}*\n"
        f"🔍 Palabras clave globales: *{len(KEYWORDS)}*\n"
        f"⏱ Frecuencia global: *{CHECK_INTERVAL_MINUTES} min*\n"
        f"🔄 Tick del scheduler: cada *{BASE_TICK_MINUTES} min*"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_ahora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_CHAT_ID and str(update.effective_chat.id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔ Comando reservado para el administrador.")
        return
    await update.message.reply_text("🔄 Chequeando feeds ahora...")
    await job_check_and_send(context.application)


# ── Job del scheduler ─────────────────────────────────────────────────────────

async def job_check_and_send(app: Application):
    """
    Tarea periódica (cada BASE_TICK_MINUTES minutos).
    1. Descarga artículos nuevos de todos los feeds globales.
    2. Para cada suscriptor cuyo intervalo ya se cumplió:
       - Filtra artículos según sus fuentes y keywords.
       - Envía y registra lo enviado.
    """
    logger.info("⏰ Tick del scheduler.")

    # 1. Descargar artículos nuevos (se guardan en seen_articles)
    try:
        scraper.fetch_new_articles()
    except Exception as exc:
        logger.error("Error al scrapear feeds: %s", exc)

    # 2. Procesar cada suscriptor
    subscribers = db.get_subscribers()
    if not subscribers:
        logger.info("Sin suscriptores activos.")
        return

    for chat_id in subscribers:
        if not _is_user_due(chat_id):
            continue

        # Artículos no enviados aún a este usuario (últimas 48h del cache)
        unsent = db.get_unsent_for_user(chat_id, since_hours=48)
        if not unsent:
            db.update_last_checked(chat_id)
            continue

        # Filtrar por fuentes habilitadas del usuario
        enabled_sources = _get_effective_sources(chat_id)
        filtered = [a for a in unsent if a["source"] in enabled_sources]

        # Filtrar por keywords del usuario
        keywords = _get_effective_keywords(chat_id)
        filtered = [a for a in filtered if FeedScraper.matches_keywords(a, keywords)]

        # Limitar cantidad por ciclo
        filtered = filtered[:MAX_ARTICLES_PER_RUN]

        if not filtered:
            db.update_last_checked(chat_id)
            continue

        logger.info("Enviando %d artículo(s) a chat_id %s.", len(filtered), chat_id)

        for article in filtered:
            message = summarizer.summarize(article)
            if not message:
                continue
            try:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=False,
                )
                db.mark_sent_to_user(chat_id, article["url"])
            except Exception as exc:
                logger.warning("Error enviando a chat_id %s: %s", chat_id, exc)
            await asyncio.sleep(1.0)

        db.update_last_checked(chat_id)

    # Limpieza periódica del cache
    db.cleanup_old_articles(days=3)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("Falta TELEGRAM_TOKEN en el archivo .env")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Comandos generales
    app.add_handler(CommandHandler("start",             cmd_start))
    app.add_handler(CommandHandler("stop",              cmd_stop))
    app.add_handler(CommandHandler("ayuda",             cmd_ayuda))

    # Palabras clave
    app.add_handler(CommandHandler("mistemas",          cmd_mistemas))
    app.add_handler(CommandHandler("agregartema",       cmd_agregartema))
    app.add_handler(CommandHandler("eliminartema",      cmd_eliminartema))
    app.add_handler(CommandHandler("reseteartemas",     cmd_reseteartemas))

    # Fuentes
    app.add_handler(CommandHandler("misfuentes",        cmd_misfuentes))
    app.add_handler(CommandHandler("activarfuente",     cmd_activarfuente))
    app.add_handler(CommandHandler("desactivarfuente",  cmd_desactivarfuente))
    app.add_handler(CommandHandler("resetearfuentes",   cmd_resetearfuentes))

    # Frecuencia
    app.add_handler(CommandHandler("mifrecuencia",      cmd_mifrecuencia))
    app.add_handler(CommandHandler("cambiafrecuencia",  cmd_cambiafrecuencia))

    # Config resumen
    app.add_handler(CommandHandler("miconfig",          cmd_miconfig))

    # Admin
    app.add_handler(CommandHandler("estado",            cmd_estado))
    app.add_handler(CommandHandler("ahora",             cmd_ahora))

    # Menú visible en Telegram
    async def set_commands(app):
        await app.bot.set_my_commands([
            BotCommand("start",             "Suscribirse a las alertas"),
            BotCommand("stop",              "Cancelar suscripción"),
            BotCommand("ayuda",             "Ver todos los comandos"),
            BotCommand("mistemas",          "Ver mis palabras clave"),
            BotCommand("agregartema",       "Agregar una palabra clave"),
            BotCommand("eliminartema",      "Eliminar una palabra clave"),
            BotCommand("reseteartemas",     "Volver a las palabras clave globales"),
            BotCommand("misfuentes",        "Ver y gestionar mis fuentes"),
            BotCommand("activarfuente",     "Activar una fuente por número"),
            BotCommand("desactivarfuente",  "Desactivar una fuente por número"),
            BotCommand("resetearfuentes",   "Volver a usar todas las fuentes"),
            BotCommand("mifrecuencia",      "Ver mi frecuencia de chequeo"),
            BotCommand("cambiafrecuencia",  "Cambiar la frecuencia (en minutos)"),
            BotCommand("miconfig",          "Ver toda mi configuración"),
        ])
    app.post_init = set_commands

    # Scheduler: tick base cada BASE_TICK_MINUTES
    scheduler = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")
    scheduler.add_job(
        job_check_and_send,
        trigger="interval",
        minutes=BASE_TICK_MINUTES,
        args=[app],
        id="check_feeds",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info(
        "✅ Scheduler iniciado. Tick base cada %d minutos. Frecuencia global: %d min.",
        BASE_TICK_MINUTES, CHECK_INTERVAL_MINUTES
    )

    logger.info("🤖 Bot iniciado. Esperando mensajes...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
