# 📰 NewsBot — Bot de Telegram para alertas de noticias y análisis

Bot que monitorea feeds RSS de medios internacionales (ES/EN), filtra por palabras clave, genera resúmenes con IA y los envía a suscriptores de Telegram. Desplegado en Railway, corre 24/7 sin depender de ninguna computadora local.

---

## 🗂 Estructura del proyecto

```
newsbot/
├── bot.py           ← Punto de entrada principal
├── config.py        ← Fuentes, keywords, configuración
├── database.py      ← SQLite (suscriptores + artículos vistos)
├── scraper.py       ← Lectura de feeds RSS + extracción de artículos
├── summarizer.py    ← Resúmenes con Google Gemini API (gratuito)
├── requirements.txt
├── .env.example     ← Plantilla de variables de entorno
├── Procfile         ← Comando de inicio para Railway
├── .python-version  ← Fija Python 3.11 para compatibilidad
└── newsbot.db       ← Se crea automáticamente al iniciar
```

---

## ⚙️ Instalación local

### 1. Requisitos previos

- Python 3.11+
- Una cuenta en [Telegram](https://telegram.org/)
- Una API key gratuita de [Google AI Studio](https://aistudio.google.com/app/apikey)

### 2. Clonar y preparar entorno

```bash
git clone https://github.com/tu-usuario/newsbot.git
cd newsbot

python3.11 -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Crear el bot de Telegram

1. Abrí Telegram y hablá con **@BotFather**
2. Enviá `/newbot` y seguí las instrucciones
3. Copiá el **token** que te da BotFather

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Editá `.env` y completá:
```
TELEGRAM_TOKEN=tu_token_aqui
GEMINI_API_KEY=tu_api_key_aqui
ADMIN_CHAT_ID=tu_chat_id_aqui   # opcional
```

> **¿Cómo obtengo mi chat_id?** Hablá con [@userinfobot](https://t.me/userinfobot) en Telegram.

### 5. Personalizar fuentes y keywords (opcional)

Editá `config.py` para agregar o quitar:
- **Fuentes RSS** en el diccionario `RSS_SOURCES`
- **Palabras clave** en la lista `KEYWORDS`
- **Frecuencia de chequeo** con `CHECK_INTERVAL_MINUTES`

### 6. Ejecutar el bot

```bash
python bot.py
```

El bot arranca, carga el scheduler y queda esperando. Los suscriptores recibirán artículos automáticamente.

---

## 💬 Comandos del bot

| Comando     | Descripción                              |
|-------------|------------------------------------------|
| `/start`    | Suscribirse a las alertas                |
| `/stop`     | Cancelar la suscripción                  |
| `/fuentes`  | Ver los medios monitoreados              |
| `/temas`    | Ver las palabras clave activas           |
| `/ahora`    | Forzar chequeo inmediato (solo admin)    |
| `/estado`   | Estadísticas del bot (solo admin)        |

---

## 🚀 Despliegue en Railway (recomendado)

Railway corre el bot 24/7 de forma gratuita. El proyecto ya incluye el `Procfile` y `.python-version` necesarios.

### 1. Subir el código a GitHub

```bash
git init
git add .
git commit -m "primer commit"
git remote add origin https://github.com/TU_USUARIO/newsbot.git
git branch -M main
git push -u origin main
```

### 2. Crear proyecto en Railway

1. Entrá a [railway.app](https://railway.app) e iniciá sesión con GitHub
2. **New Project** → **Deploy from GitHub repo** → seleccioná el repositorio
3. Railway detecta Python automáticamente

### 3. Cargar variables de entorno

En el panel de Railway → **Variables** → agregá una por una:

| Variable | Valor |
|---|---|
| `TELEGRAM_TOKEN` | Token de @BotFather |
| `GEMINI_API_KEY` | API key de Google AI Studio |
| `ADMIN_CHAT_ID` | Tu chat_id de Telegram (opcional) |

### 4. Volumen persistente (recomendado)

Sin un volumen, la base de datos se reinicia en cada redeploy y se pierden los suscriptores.

1. En Railway → **Add Service** → **Volume**
2. Montalo en `/app/data`
3. Agregá la variable: `DB_PATH=/app/data/newsbot.db`

### 5. Verificar que está corriendo

En **Deployments** → deploy activo → **Logs**, deberías ver:

```
✅ Scheduler iniciado. Chequeo cada 60 minutos.
🤖 Bot iniciado. Esperando mensajes...
```

Cada redeploy se dispara automáticamente al hacer `git push`.

---

## 🔧 Agregar una nueva fuente RSS

En `config.py`, agregá una línea al diccionario `RSS_SOURCES`:

```python
"Nombre del medio": "https://ejemplo.com/feed/rss",
```

> **¿Cómo encontrar el RSS de un sitio?**
> - Probá `https://sitio.com/feed`, `https://sitio.com/rss`, `https://sitio.com/feed.xml`
> - Buscá el ícono 📡 en el sitio web
> - Usá la extensión [RSS Feed Reader](https://chromewebstore.google.com/detail/rss-feed-reader/pnjaodmkngahhkoihejjehlcdlnohgmp) en Chrome

---

## 📦 Dependencias principales

| Librería | Uso |
|----------|-----|
| `python-telegram-bot` | Bot de Telegram (async) |
| `apscheduler` | Scheduler periódico |
| `beautifulsoup4` + `lxml` | Extracción de texto de artículos web |
| `google-generativeai` | Resúmenes con Gemini 1.5 Flash (gratuito) |
| `python-dotenv` | Variables de entorno desde `.env` |
| `requests` | Descarga de feeds y artículos |

---

## 🆓 Límites gratuitos de Google Gemini

El bot usa **Gemini 1.5 Flash**, que en el tier gratuito ofrece:
- 15 requests por minuto
- 1.500 requests por día
- 1 millón de tokens de contexto por request

Más que suficiente para un bot de noticias con cientos de suscriptores.

---

## 📝 Licencia

MIT — libre uso y modificación.
