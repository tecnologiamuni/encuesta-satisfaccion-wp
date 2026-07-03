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
import schedule
import requests
from datetime import datetime

from base_de_datos import pacientes_pendientes_de_ayer, marcar_enviado

LINK_ENCUESTA   = "https://encuesta-guardia.vercel.app/"
WA_SERVER_URL   = "http://localhost:3001"   # servidor whatsapp-web.js

VERDE    = "\033[92m"
AMARILLO = "\033[93m"
ROJO     = "\033[91m"
AZUL     = "\033[94m"
NEGRITA  = "\033[1m"
RESET    = "\033[0m"


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


def armar_mensaje(nombre: str) -> str:
    dia = datetime.now().timetuple().tm_yday
    idx = dia % len(MENSAJES)
    return MENSAJES[idx](nombre)


def enviar_a_todos():
    ahora = datetime.now().strftime("%H:%M:%S")
    print(f"\n{AZUL}{NEGRITA}[{ahora}] Iniciando envío de encuestas...{RESET}")

    # Verificar que el servidor WhatsApp esté listo
    if not verificar_servidor():
        print(f"{ROJO}Abortando envío: servidor no disponible.{RESET}")
        return

    pendientes = pacientes_pendientes_de_ayer()

    if not pendientes:
        print(f"  {AMARILLO}No hay pacientes pendientes de ayer.{RESET}")
        return

    print(f"  {NEGRITA}Pacientes a contactar: {len(pendientes)}{RESET}\n")

    enviados   = 0
    con_error  = 0

    for p in pendientes:
        nombre   = p["nombre"]
        apellido = p["apellido"]
        telefono = p["telefono"]
        mensaje  = armar_mensaje(nombre)

        print(f"  → Enviando a {nombre} {apellido} ({telefono})... ", end="", flush=True)

        ok = enviar_whatsapp(telefono, mensaje)

        if ok:
            marcar_enviado(p["id"])
            print(f"{VERDE}✓ Enviado{RESET}")
            enviados += 1
        else:
            print(f"{ROJO}✗ Falló{RESET}")
            con_error += 1

        # Pausa entre mensajes para no saturar WhatsApp
        if len(pendientes) > 1:
            time.sleep(3)

    print(f"\n{VERDE}{NEGRITA}Resumen: {enviados} enviados, {con_error} con error.{RESET}\n")


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

    schedule.every().day.at("09:00").do(enviar_a_todos)

    prox = schedule.next_run()
    print(f"  Próximo envío: {NEGRITA}{prox.strftime('%d/%m/%Y %H:%M')}{RESET}\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
