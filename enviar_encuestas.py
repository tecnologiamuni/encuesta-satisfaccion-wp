"""
enviar_encuestas.py
───────────────────
Tarea que corre todos los días a las 9:00 hs.
Lee la base de datos, busca los pacientes cargados ayer que no
recibieron mensaje, y les manda el WhatsApp con el link a la encuesta.

REQUISITO: el servidor whatsapp-server/server.js tiene que estar corriendo
antes de ejecutar este script.

Modos de uso:

  1) Modo cron (queda corriendo en segundo plano, envía a las 9hs):
        python enviar_encuestas.py

  2) Envío inmediato de prueba:
        python enviar_encuestas.py --ahora
"""
import sys
import time
import traceback
import schedule
import requests
from datetime import datetime
from pathlib import Path

from base_de_datos import pacientes_pendientes_de_hoy, registrar_envio

LINK_ENCUESTA   = "https://encuesta-guardia.vercel.app/"
WA_SERVER_URL   = "http://localhost:3001"   # servidor whatsapp-web.js

VERDE    = "\033[92m"
AMARILLO = "\033[93m"
ROJO     = "\033[91m"
AZUL     = "\033[94m"
NEGRITA  = "\033[1m"
RESET    = "\033[0m"

# ── Logging a archivo ─────────────────────────────────────────────────────────
# Además de imprimir en consola, dejamos un registro en disco para poder
# revisar a la mañana qué pasó durante la noche si algo falló y nadie
# estaba mirando la pantalla.
LOG_DIR  = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "enviar_encuestas.log"


def log_a_archivo(mensaje: str):
    """Escribe una línea con timestamp en logs/enviar_encuestas.log (sin colores ANSI)."""
    limpio = mensaje
    for c in (VERDE, AMARILLO, ROJO, AZUL, NEGRITA, RESET):
        limpio = limpio.replace(c, "")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {limpio}\n")
    except Exception:
        pass  # si ni siquiera se puede escribir el log, no vale la pena crashear por eso


# ── WhatsApp via servidor Node ────────────────────────────────────────────────

def verificar_servidor() -> bool:
    """Devuelve True si el servidor Node está corriendo y WhatsApp conectado."""
    try:
        r = requests.get(f"{WA_SERVER_URL}/estado", timeout=5)
        data = r.json()
        estado = data.get("estado", "")
        if estado == "conectado":
            return True
        elif estado == "qr_pendiente":
            print(f"{AMARILLO}⚠ WhatsApp esperando QR. Abrí http://localhost:3001/qr "
                f"o mirá la consola del servidor para escanearlo.{RESET}")
        else:
            print(f"{ROJO}✗ Servidor en estado: {estado}{RESET}")
        return False
    except requests.ConnectionError:
        print(
            f"{ROJO}✗ No se pudo conectar al servidor WhatsApp "
            f"(http://localhost:3001).{RESET}\n"
            f"  Asegurate de haber iniciado INICIAR_WHATSAPP_SERVER.bat primero."
        )
        return False


def enviar_whatsapp(telefono: str, mensaje: str) -> bool:
    """
    Llama al servidor Node para enviar el mensaje.
    Devuelve True si fue exitoso.
    """
    try:
        r = requests.post(
            f"{WA_SERVER_URL}/enviar",
            json={"telefono": telefono, "mensaje": mensaje},
            timeout=30,
        )
        if r.status_code == 200:
            return True
        else:
            print(f"{ROJO}Error del servidor: {r.json().get('error', r.text)}{RESET}")
            return False
    except requests.Timeout:
        print(f"{ROJO}✗ Timeout al enviar mensaje{RESET}")
        return False
    except Exception as e:
        print(f"{ROJO}✗ Excepción: {e}{RESET}")
        return False


# ── Lógica de envío ───────────────────────────────────────────────────────────

MENSAJES = [
    lambda n: (
        f"Hola {n} 👋, esperamos que te encuentres mejor.\n\n"
        f"Nos gustaría conocer tu opinión sobre la atención que recibiste "
        f"en la guardia. ¿Podrías completar esta breve encuesta?\n\n"
        f"👉 {LINK_ENCUESTA}\n\n"
        f"¡Muchas gracias! Tu opinión nos ayuda a mejorar 🙏"
    ),
    lambda n: (
        f"¡Hola {n}! 🙌 Esperamos que ya estés mucho mejor.\n\n"
        f"Queremos saber cómo fue tu experiencia en la guardia. "
        f"Te agradeceríamos si completás esta encuesta breve:\n\n"
        f"👉 {LINK_ENCUESTA}\n\n"
        f" Gracias por ayudarnos a seguir mejorando 🙌"
    ),
    lambda n: (
        f"Hola {n} 😊, ¿cómo estás?\n\n"
        f"Desde la guardia médica queremos conocer tu opinión "
        f"sobre la atención que recibiste. ¿Nos ayudás con esta encuesta?\n\n"
        f"👉 {LINK_ENCUESTA}\n\n"
        f"¡Muchas gracias por tu tiempo! 🙏"
    ),
]


def armar_mensaje(nombre: str, mensajes_enviados: int) -> str:
    """
    Arma el mensaje que corresponde según cuántos ya se le mandaron a
    este paciente, usando el resto de la división por 3 para que el
    ciclo se repita indefinidamente:
    mensajes_enviados=0 -> mensaje 1 (día 1)
    mensajes_enviados=1 -> mensaje 2 (día 2)
    mensajes_enviados=2 -> mensaje 3 (día 3)
    mensajes_enviados=3 -> mensaje 1 de nuevo (día 4)
    mensajes_enviados=4 -> mensaje 2 (día 5) ... y así siempre.
    """
    idx = mensajes_enviados % len(MENSAJES)
    return MENSAJES[idx](nombre)


def enviar_a_todos():
    ahora = datetime.now().strftime("%H:%M:%S")
    print(f"\n{AZUL}{NEGRITA}[{ahora}] Iniciando envío de encuestas...{RESET}")
    log_a_archivo("Iniciando envío de encuestas...")

    # Verificar que el servidor WhatsApp esté listo
    if not verificar_servidor():
        print(f"{ROJO}Abortando envío: servidor no disponible.{RESET}")
        log_a_archivo("ABORTADO: servidor de WhatsApp no disponible.")
        return

    pendientes = pacientes_pendientes_de_hoy()

    if not pendientes:
        print(f"  {AMARILLO}No hay pacientes pendientes de recibir mensaje hoy.{RESET}")
        log_a_archivo("Sin pacientes pendientes hoy.")
        return

    print(f"  {NEGRITA}Pacientes a contactar: {len(pendientes)}{RESET}\n")

    enviados   = 0
    con_error  = 0

    for p in pendientes:
        nombre    = p["nombre"]
        apellido  = p["apellido"]
        telefono  = p["telefono"]
        ya_env    = p["mensajes_enviados"]
        n_msj     = ya_env + 1  # el mensaje que le toca (1, 2 o 3, repitiendo el ciclo)
        mensaje   = armar_mensaje(nombre, ya_env)

        print(f"  → Enviando mensaje {n_msj}/3 a {nombre} {apellido} ({telefono})... ", end="", flush=True)

        ok = enviar_whatsapp(telefono, mensaje)

        if ok:
            registrar_envio(p["id"])
            print(f"{VERDE}✓ Enviado{RESET}")
            enviados += 1
        else:
            print(f"{ROJO}✗ Falló{RESET}")
            log_a_archivo(f"Falló el envío a {nombre} {apellido} ({telefono}).")
            con_error += 1

        # Pausa entre mensajes para no saturar WhatsApp
        if len(pendientes) > 1:
            time.sleep(3)

    resumen = f"Resumen: {enviados} enviados, {con_error} con error."
    print(f"\n{VERDE}{NEGRITA}{resumen}{RESET}\n")
    log_a_archivo(resumen)


def job_seguro():
    """
    Envoltorio que ejecuta enviar_a_todos() atrapando CUALQUIER excepción.
    Sin esto, un error inesperado (ej. la base de datos no responde un
    instante, un timeout raro) se propaga hacia arriba y mata todo el loop
    del cron — quedaría la ventana abierta pero sin programar más envíos
    hasta que alguien la reinicie a mano. Con este wrapper, el error queda
    logueado y el cron sigue vivo para el próximo día.
    """
    try:
        enviar_a_todos()
    except Exception:
        error_txt = traceback.format_exc()
        print(f"{ROJO}{NEGRITA}✗ ERROR INESPERADO durante el envío:{RESET}\n{error_txt}")
        log_a_archivo(f"ERROR INESPERADO:\n{error_txt}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    modo_ahora = "--ahora" in sys.argv

    if modo_ahora:
        print(f"{AZUL}{NEGRITA}── Modo prueba: envío inmediato ──{RESET}")
        enviar_a_todos()
        return

    # Modo cron: queda corriendo y envía a las 9:00 hs todos los días
    print(f"\n{AZUL}{NEGRITA}╔══════════════════════════════════════════╗")
    print(        "║   GUARDIA MÉDICA · Envío automático WA   ║")
    print(        f"╚══════════════════════════════════════════╝{RESET}")
    print(f"\n  Cron iniciado. Se enviarán los mensajes todos los días a las {NEGRITA}09:00 hs{RESET}.")
    print(f"  {AMARILLO}No cierres esta ventana.{RESET}")
    print(f"  Presioná Ctrl+C para detener.\n")

    schedule.every().day.at("09:00").do(job_seguro)

    prox = schedule.next_run()
    print(f"  Próximo envío: {NEGRITA}{prox.strftime('%d/%m/%Y %H:%M')}{RESET}\n")
    log_a_archivo("Cron iniciado. Próximo envío programado a las 09:00 hs.")

    while True:
        try:
            schedule.run_pending()
        except Exception:
            # Defensa extra: aunque job_seguro ya atrapa errores del envío,
            # esto cubre cualquier falla imprevista del propio scheduler.
            error_txt = traceback.format_exc()
            print(f"{ROJO}✗ Error inesperado en el loop del cron:{RESET}\n{error_txt}")
            log_a_archivo(f"ERROR EN EL LOOP DEL CRON:\n{error_txt}")
        time.sleep(30)


if __name__ == "__main__":
    main()