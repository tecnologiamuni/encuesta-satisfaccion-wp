"""
Manejo de la base de datos PostgreSQL (Neon).
Lee la connection string desde el archivo .env o variable de entorno DATABASE_URL.
"""
import os
import psycopg
from psycopg.rows import dict_row
from datetime import date, timedelta
from pathlib import Path

# Intentar cargar .env si existe
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

DATABASE_URL = os.getenv("DATABASE_URL")


def _conexion():
    if not DATABASE_URL:
        raise RuntimeError(
            "\n\n  ❌ Falta DATABASE_URL.\n"
            "  Creá un archivo .env en esta carpeta con el contenido:\n"
            "  DATABASE_URL=postgresql://usuario:password@host/db?sslmode=require\n"
        )
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


CANTIDAD_MENSAJES = 3  # cuántos mensajes tiene la secuencia (día 1, día 2, día 3)


def init_db():
    """Crea las tablas si no existen y migra el esquema viejo al nuevo."""
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pacientes (
                    id              SERIAL PRIMARY KEY,
                    dni             TEXT UNIQUE,
                    nombre          TEXT NOT NULL,
                    apellido        TEXT NOT NULL,
                    telefono        TEXT NOT NULL,
                    fecha_carga     DATE NOT NULL DEFAULT CURRENT_DATE,
                    mensaje_enviado BOOLEAN NOT NULL DEFAULT FALSE,
                    fecha_envio     TIMESTAMPTZ
                );
            """)
            cur.execute("""
                ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS dni TEXT UNIQUE;
            """)
            # ── Migración: contador de mensajes de la secuencia (0,1,2,3) ──
            cur.execute("""
                ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS mensajes_enviados INT NOT NULL DEFAULT 0;
            """)
            cur.execute("""
                ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS fecha_ultimo_envio TIMESTAMPTZ;
            """)
            # Si venías del esquema viejo (booleano), lo migramos a contador completo/cero
            cur.execute("""
                UPDATE pacientes
                SET mensajes_enviados = %s
                WHERE mensaje_enviado = TRUE AND mensajes_enviados = 0;
            """, (CANTIDAD_MENSAJES,))
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_pacientes_pendientes
                ON pacientes (mensajes_enviados, fecha_carga);
            """)
        conn.commit()


def agregar_paciente(nombre: str, apellido: str, telefono: str, dni: str = "") -> int:
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pacientes (nombre, apellido, telefono, dni)
                VALUES (%s, %s, %s, NULLIF(%s, '')) RETURNING id;
                """,
                (nombre.strip(), apellido.strip(), telefono.strip(), dni.strip())
            )
            row = cur.fetchone()
        conn.commit()
        return row["id"]


def buscar_por_dni(dni: str) -> dict | None:
    if not dni.strip():
        return None
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM pacientes WHERE dni = %s;",
                (dni.strip(),)
            )
            return cur.fetchone()


def actualizar_telefono(paciente_id: int, telefono: str):
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pacientes SET telefono = %s WHERE id = %s;",
                (telefono.strip(), paciente_id)
            )
        conn.commit()


def reactivar_paciente(paciente_id: int):
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pacientes
                SET mensaje_enviado = FALSE,
                    mensajes_enviados = 0,
                    fecha_ultimo_envio = NULL,
                    fecha_carga = CURRENT_DATE
                WHERE id = %s;
                """,
                (paciente_id,)
            )
        conn.commit()


def actualizar_paciente(paciente_id: int, dni: str, nombre: str, apellido: str, telefono: str):
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pacientes
                SET dni = NULLIF(%s, ''),
                    nombre = %s,
                    apellido = %s,
                    telefono = %s,
                    mensaje_enviado = FALSE,
                    mensajes_enviados = 0,
                    fecha_ultimo_envio = NULL,
                    fecha_carga = CURRENT_DATE
                WHERE id = %s;
                """,
                (dni.strip(), nombre.strip(), apellido.strip(), telefono.strip(), paciente_id)
            )
        conn.commit()


def pacientes_pendientes_de_hoy() -> list:
    """
    Devuelve los pacientes a los que hoy les toca el PRÓXIMO mensaje del
    ciclo, según cuántos días pasaron desde fecha_carga.

    El ciclo de 3 mensajes se repite indefinidamente:
    - Día 1 después de cargado -> mensaje 1 (mensajes_enviados pasa de 0 a 1)
    - Día 2 después de cargado -> mensaje 2 (mensajes_enviados pasa de 1 a 2)
    - Día 3 después de cargado -> mensaje 3 (mensajes_enviados pasa de 2 a 3)
    - Día 4 después de cargado -> mensaje 1 de nuevo (mensajes_enviados 3 a 4)
    - Día 5 -> mensaje 2, día 6 -> mensaje 3, día 7 -> mensaje 1... y así
      para siempre, mientras el paciente siga en la base.

    A propósito NO se limita por CANTIDAD_MENSAJES: mensajes_enviados es un
    contador acumulado que crece sin techo, y armar_mensaje() (en
    enviar_encuestas.py) usa el resto de la división por 3 para saber cuál
    de los 3 textos corresponde en cada vuelta del ciclo.

    El ">=" (en vez de "=") permite que, si el cron no corrió un día
    (PC apagada, etc.), al volver a correr igual mande el mensaje que
    correspondía sin saltearlo. fecha_ultimo_envio evita mandar dos veces
    el mismo mensaje el mismo día si el cron corre varias veces.
    """
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre, apellido, telefono, mensajes_enviados
                FROM pacientes
                WHERE (CURRENT_DATE - fecha_carga) >= (mensajes_enviados + 1)
                  AND (fecha_ultimo_envio IS NULL OR fecha_ultimo_envio::date < CURRENT_DATE)
                ORDER BY id ASC;
                """
            )
            return cur.fetchall()


def registrar_envio(paciente_id: int):
    """Suma 1 al contador de mensajes enviados (sin techo, sigue creciendo
    para siempre) y marca la fecha del envío."""
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pacientes
                SET mensajes_enviados = mensajes_enviados + 1,
                    fecha_ultimo_envio = now(),
                    mensaje_enviado = TRUE,
                    fecha_envio = now()
                WHERE id = %s;
                """,
                (paciente_id,)
            )
        conn.commit()


# ── Helpers SOLO para testing (no los usa la app en producción) ─────────────

def crear_o_reusar_paciente_prueba(dni: str, nombre: str, apellido: str, telefono: str) -> int:
    """Busca un paciente de prueba por DNI; si no existe, lo crea. Devuelve el id."""
    existente = buscar_por_dni(dni)
    if existente:
        return existente["id"]
    return agregar_paciente(nombre, apellido, telefono, dni)


def fijar_estado_prueba(paciente_id: int, dias_atras: int, mensajes_enviados: int):
    """
    Fuerza el estado de un paciente para simular en qué punto de la secuencia
    está, sin tener que esperar días reales. Por ejemplo:
      fijar_estado_prueba(id, dias_atras=2, mensajes_enviados=1)
    simula "se cargó hace 2 días y ya se le mandó 1 mensaje", por lo tanto
    hoy le toca el mensaje 2. Con el ciclo infinito, mensajes_enviados=4
    simula que ya completó una vuelta entera y le toca el mensaje 1 de la
    segunda vuelta.
    """
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pacientes
                SET fecha_carga = CURRENT_DATE - %s,
                    mensajes_enviados = %s,
                    fecha_ultimo_envio = NULL,
                    mensaje_enviado = (%s > 0)
                WHERE id = %s;
                """,
                (dias_atras, mensajes_enviados, mensajes_enviados, paciente_id)
            )
        conn.commit()


def listar_todos() -> list:
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM pacientes ORDER BY fecha_carga DESC, id DESC;"
            )
            rows = cur.fetchall()
    for r in rows:
        if r.get("fecha_carga"):
            r["fecha_carga"] = r["fecha_carga"].isoformat()
        if r.get("fecha_envio"):
            r["fecha_envio"] = r["fecha_envio"].isoformat()
    return rows


# Inicializar al importar
init_db()