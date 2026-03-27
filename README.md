# 🤖 Micronistabot

Bot de Telegram que monitorea fuentes RSS internacionales, filtra artículos por palabras clave y envía resúmenes generados con IA (Google Gemini) directamente a tu chat.

Cada usuario puede personalizar sus propias palabras clave, fuentes y frecuencia de alertas desde el chat.

---

## Comandos disponibles

### Suscripción
| Comando | Descripción |
|---|---|
| `/start` | Suscribirse a las alertas |
| `/stop` | Cancelar suscripción |
| `/ayuda` | Ver todos los comandos |

### Palabras clave
| Comando | Descripción |
|---|---|
| `/mistemas` | Ver tus palabras clave activas |
| `/agregartema <palabra>` | Agregar una palabra clave |
| `/eliminartema <palabra>` | Eliminar una palabra clave |
| `/reseteartemas` | Volver a las palabras clave globales |

### Fuentes RSS
| Comando | Descripción |
|---|---|
| `/misfuentes` | Ver tu lista de fuentes con estado |
| `/activarfuente <número>` | Activar una fuente |
| `/desactivarfuente <número>` | Desactivar una fuente |
| `/resetearfuentes` | Volver a usar todas las fuentes |

### Frecuencia
| Comando | Descripción |
|---|---|
| `/mifrecuencia` | Ver tu frecuencia de chequeo actual |
| `/cambiafrecuencia <minutos>` | Cambiar la frecuencia (mínimo 15 min) |

### Configuración
| Comando | Descripción |
|---|---|
| `/miconfig` | Resumen de toda tu configuración |

### Admin
| Comando | Descripción |
|---|---|
| `/estado` | Ver estadísticas del bot |
| `/ahora` | Forzar chequeo inmediato de feeds |

---

## Deploy en Railway (fork propio)

### Requisitos
- Cuenta en [Railway](https://railway.app)
- Token de bot de Telegram (vía [@BotFather](https://t.me/BotFather))
- API Key de Google Gemini ([Google AI Studio](https://aistudio.google.com))

### Pasos

**1. Clonar el repositorio**
```bash
git clone https://github.com/TuUsuario/micronistabot.git
cd micronistabot
```

**2. Configurar variables de entorno**

Crear un archivo `.env` (no se sube a git):
```env
TELEGRAM_TOKEN=tu_token_aqui
GEMINI_API_KEY=tu_api_key_aqui
ADMIN_CHAT_ID=tu_chat_id_aqui
```

**3. Subir a Railway**

En el dashboard de Railway: New Project → Deploy from GitHub repo → agregar las variables en Variables. Railway detecta el `Procfile` automáticamente.

**4. Personalizar** (`config.py`)

Editá `KEYWORDS` y `RSS_SOURCES` para definir los temas y fuentes globales por defecto.

---

## Estructura del proyecto

```
micronistabot/
├── bot.py           # Lógica principal y comandos de Telegram
├── config.py        # Keywords, fuentes y configuración global
├── database.py      # Gestión de SQLite (suscriptores, artículos, config por usuario)
├── scraper.py       # Descarga y parseo de feeds RSS
├── summarizer.py    # Resúmenes con Google Gemini
├── Procfile         # Comando de arranque para Railway
├── requirements.txt # Dependencias Python
└── .python-version  # Versión de Python (3.11)
```

---

## Variables de entorno

| Variable | Requerida | Descripción |
|---|---|---|
| `TELEGRAM_TOKEN` | Sí | Token del bot de Telegram |
| `GEMINI_API_KEY` | Sí | API Key de Google Gemini |
| `ADMIN_CHAT_ID` | No | Tu chat ID para comandos de admin |

---

## Notas técnicas

- La base de datos (`newsbot.db`) es SQLite local. En Railway el filesystem es efímero: si redesplegás se reinicia. Para producción con muchos usuarios se recomienda migrar a PostgreSQL.
- El scheduler corre con un tick base de 15 minutos. Cada usuario puede configurar su propio intervalo (mínimo 15 min, máximo 24 horas).
- Si un usuario no configura keywords o fuentes propias, el bot usa las globales de `config.py`.
- Gemini 1.5 Flash (tier gratuito): 15 requests/minuto, 1500 requests/día.
