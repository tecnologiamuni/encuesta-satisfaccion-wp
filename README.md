# Guardia Médica · Sistema de Encuestas por WhatsApp

Sistema para el envío automático de encuestas de satisfacción a pacientes de guardia médica via WhatsApp. Los pacientes cargados un día reciben automáticamente un mensaje con el link a la encuesta al día siguiente a las 9:00 hs.

---

## Características

- **Carga de pacientes** con nombre, apellido, teléfono y DNI opcional
- **Envío automático diario** a las 9:00 hs vía WhatsApp
- **Interfaz gráfica** para gestionar pacientes sin tocar la terminal
- **Base de datos PostgreSQL** en la nube (Neon)
- **Envío rápido** (~3 seg por mensaje) usando `whatsapp-web.js`
- **No bloquea la PC** — corre en segundo plano sin necesidad de Chrome visible

---

## Requisitos

- **Python 3.10+** → [Descargar](https://www.python.org/downloads/)
- **Node.js 18+** → [Descargar](https://nodejs.org/) (versión LTS)
- **Conexión a Internet**

---

## Instalación

### 1. Clonar el proyecto

```bash
git clone <repo-url>
cd guardia-local2
```

### 2. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

### 3. Instalar dependencias del servidor WhatsApp

```bash
cd whatsapp-server
npm install
cd ..
```

> ⚠ **Nota:** Si descargaste el proyecto sin la carpeta `node_modules` (porque pesa mucho), tenés que ejecutar `npm install` dentro de `whatsapp-server/` para instalarla.

### 4. Configurar la base de datos

Creá un archivo `.env` en la raíz del proyecto con tu connection string de PostgreSQL (recomendado: [Neon](https://neon.tech)):

```
DATABASE_URL=postgresql://usuario:password@host/db?sslmode=require
```

Las tablas se crean automáticamente al ejecutar cualquiera de los scripts.

---

## Uso diario

Seguí este orden:

### ① Iniciar el servidor WhatsApp

```bash
cd whatsapp-server
node server.js
```

O hacé doble click en **`INICIAR_WHATSAPP_SERVER.bat`**.

La **primera vez** aparecerá un código QR en la consola. Escanealo desde WhatsApp: *Tres puntos → Aparatos vinculados → Vincular dispositivo*. Luego se reconecta solo.

**Dejá esta ventana abierta.**

### ② Cargar pacientes

Usá la interfaz gráfica:

```bash
python interfaz.py
```

O hacé doble click en **`ABRIR_INTERFAZ.bat`**.

También podés ejecutar directamente el script de alta si existe.

### ③ Envío automático

```bash
python enviar_encuestas.py
```

O hacé doble click en **`INICIAR_CRON.bat`**.

Esto queda corriendo en segundo plano. Todos los días a las **9:00 hs** envía automáticamente el mensaje a los pacientes cargados el día anterior.

### Envío de prueba

```bash
python enviar_encuestas.py --ahora
```

O hacé doble click en **`PROBAR_ENVIO_AHORA.bat`**. Envía los mensajes pendientes inmediatamente, sin esperar a las 9:00.

---

## Arquitectura

```
┌─────────────────────────────────────────────────┐
│                  PostgreSQL (Neon)               │
│  ┌───────────────────────────────────────────┐   │
│  │  pacientes                                │   │
│  │  ├─ id (PK)                               │   │
│  │  ├─ dni (UNIQUE)                          │   │
│  │  ├─ nombre / apellido / telefono          │   │
│  │  ├─ fecha_carga                           │   │
│  │  ├─ mensaje_enviado (boolean)             │   │
│  │  └─ fecha_envio                           │   │
│  └───────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   envía_encuestas.py        interfaz.py
   (cron / --ahora)          (GUI tkinter)
        │                         │
        └────────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │   whatsapp-server/       │
        │   (Express API)          │
        │   POST /enviar           │
        │   GET  /estado           │
        │   GET  /qr               │
        └────────────┬────────────┘
                     │
           whatsapp-web.js
           (protocolo WhatsApp)
```

### Flujo de datos

1. Se carga un paciente a través de `interfaz.py` → se inserta en la DB con `fecha_carga = hoy`
2. Al día siguiente, `enviar_encuestas.py` (modo cron o `--ahora`) consulta `pacientes_pendientes_de_ayer()`
3. Por cada paciente pendiente, hace un `POST /enviar` al servidor Node.js
4. El servidor Node usa `whatsapp-web.js` para enviar el mensaje real
5. Si el envío es exitoso, se marca `mensaje_enviado = TRUE` en la DB

---

## Estructura de archivos

```
guardia-local2/
├── .env                         # Connection string de la DB
├── requirements.txt             # Dependencias Python
├── base_de_datos.py             # Capa de acceso a PostgreSQL
├── enviar_encuestas.py          # Script de envío (cron o inmediato)
├── interfaz.py                  # Interfaz gráfica (tkinter)
├── LEEME.md                     # Manual de uso original
├── ABRIR_INTERFAZ.bat           # Atajo para abrir la GUI
├── INICIAR_CRON.bat             # Atajo para iniciar el cron
├── INICIAR_WHATSAPP_SERVER.bat  # Atajo para el servidor WhatsApp
├── PROBAR_ENVIO_AHORA.bat       # Atajo para envío de prueba
└── whatsapp-server/
    ├── package.json
    ├── server.js                # Servidor Express + whatsapp-web.js
    ├── .wwebjs_cache/           # Caché de WhatsApp (no borrar)
    .webjs_auth/                 # Sesión guardada (no borrar)
    └── node_modules/            # Se genera con npm install
```

---

## Solución de problemas

| Problema | Solución |
|---|---|
| `No se pudo conectar al servidor WhatsApp` | Asegurate de que `INICIAR_WHATSAPP_SERVER.bat` esté abierto y muestre "✅ WhatsApp conectado" |
| El QR venció | Esperá ~20 segundos y aparece uno nuevo automáticamente |
| `WhatsApp desconectado` después de varios días | Re-iniciá el servidor. Si pide QR, re-escaneá |
| La DB no funciona | Verificá que el `.env` tenga la `DATABASE_URL` correcta |
| Error de módulo Node | Ejecutá `npm install` dentro de `whatsapp-server/` |

---

## Tecnologías

- **Python** — Lógica de negocio y scheduling (`schedule`, `requests`, `psycopg`)
- **Node.js / Express** — API REST para WhatsApp
- **whatsapp-web.js** — Cliente no-oficial de WhatsApp Web
- **PostgreSQL (Neon)** — Base de datos en la nube
- **Tkinter** — Interfaz gráfica de escritorio
