# 📰 neo_cronista — Bot de Telegram para alertas de noticias con IA

Bot que monitorea feeds RSS de medios internacionales (ES/EN), filtra artículos por palabras clave, genera resúmenes con Google Gemini y los envía a suscriptores de Telegram. Corre localmente desde WSL en Windows.

---

## 🗂 Estructura del proyecto

```
micronista_bot/
├── bot.py           ← Punto de entrada principal y comandos de Telegram
├── config.py        ← Fuentes RSS, keywords y configuración del scheduler
├── database.py      ← SQLite: suscriptores, artículos vistos, preferencias
├── scraper.py       ← Lectura de feeds RSS + extracción de artículos
├── summarizer.py    ← Resúmenes con Google Gemini API
├── start.sh         ← Script para arrancar el bot desde WSL
├── requirements.txt
└── .python-version  ← Fija Python 3.11
```

> La base de datos `newsbot.db` y el log `newsbot.log` se crean automáticamente al iniciar y están ignorados por git.

---

## ⚙️ Instalación

### Requisitos previos

- Windows con WSL (Ubuntu)
- Python 3.11
- [uv](https://astral.sh/uv) como gestor de paquetes
- Token de Telegram (via [@BotFather](https://t.me/BotFather))
- API key de [Google AI Studio](https://aistudio.google.com/app/apikey) (Gemini, gratuito)

### 1. Clonar el repositorio en WSL

```bash
git clone git@github.com:Nikolaiev1745/micronista_bot.git ~/micronista_bot
cd ~/micronista_bot
```

### 2. Crear entorno virtual e instalar dependencias

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
nano .env
```

```
TELEGRAM_TOKEN=tu_token_aqui
GEMINI_API_KEY=tu_key_aqui
ADMIN_CHAT_ID=tu_chat_id_aqui
```

> **¿Cómo obtengo mi chat_id?** Hablá con [@userinfobot](https://t.me/userinfobot) en Telegram.

### 4. Dar permisos al script de inicio

```bash
chmod +x start.sh
```

---

## 🚀 Uso

**Prender el bot:**
```bash
~/micronista_bot/start.sh
```

**Apagar el bot:** `Ctrl+C`

El bot corre mientras la terminal de WSL esté abierta.

---

## 💬 Comandos disponibles

### Generales
| Comando | Descripción |
|---|---|
| `/start` | Suscribirse a las alertas |
| `/stop` | Cancelar la suscripción |
| `/ayuda` | Ver todos los comandos |

### Palabras clave
| Comando | Descripción |
|---|---|
| `/mistemas` | Ver tus palabras clave activas |
| `/agregartema <palabra>` | Agregar una palabra clave propia |
| `/eliminartema <palabra>` | Eliminar una palabra clave |
| `/reseteartemas` | Volver a las palabras clave globales |

### Fuentes
| Comando | Descripción |
|---|---|
| `/misfuentes` | Ver y gestionar tus fuentes activas |
| `/activarfuente <número>` | Activar una fuente |
| `/desactivarfuente <número>` | Desactivar una fuente |
| `/resetearfuentes` | Volver a usar todas las fuentes |

### Frecuencia
| Comando | Descripción |
|---|---|
| `/mifrecuencia` | Ver tu frecuencia de chequeo actual |
| `/cambiafrecuencia <minutos>` | Cambiar la frecuencia (mín. 15, máx. 1440) |

### Configuración
| Comando | Descripción |
|---|---|
| `/miconfig` | Resumen de toda tu configuración |

### Admin
| Comando | Descripción |
|---|---|
| `/ahora` | Forzar chequeo inmediato de feeds |
| `/estado` | Estadísticas del bot |

---

## 🔧 Personalización

Editá `config.py` para modificar:

- **`KEYWORDS`** — palabras clave globales para filtrar artículos
- **`RSS_SOURCES`** — diccionario de fuentes RSS monitoreadas
- **`CHECK_INTERVAL_MINUTES`** — frecuencia global de chequeo (default: 60 min)
- **`MAX_ARTICLES_PER_RUN`** — límite de artículos enviados por ciclo

### Agregar una fuente RSS

```python
# En config.py, dentro de RSS_SOURCES:
"Nombre del medio": "https://ejemplo.com/feed/rss",
```

---

## 🔄 Workflow de desarrollo

```bash
# Hacer cambios en el código
nano config.py

# Probar localmente
~/micronista_bot/start.sh

# Subir cambios a GitHub
git add .
git commit -m "descripción del cambio"
git push
```

---

## 📦 Dependencias principales

| Librería | Uso |
|---|---|
| `python-telegram-bot` | Bot de Telegram (async) |
| `apscheduler` | Scheduler periódico |
| `beautifulsoup4` + `lxml` | Extracción de texto de artículos web |
| `google-generativeai` | Resúmenes con Gemini 1.5 Flash |
| `python-dotenv` | Variables de entorno desde `.env` |
| `requests` | Descarga de feeds y artículos |

---

## 🆓 Límites gratuitos de Google Gemini

El bot usa **Gemini 1.5 Flash**, con tier gratuito:
- 15 requests por minuto
- 1.500 requests por día

Más que suficiente para un bot personal o con pocos suscriptores.

---

## 📝 Licencia

MIT — libre uso y modificación.
