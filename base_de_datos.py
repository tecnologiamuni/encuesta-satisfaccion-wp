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


def init_db():
    """Crea las tablas si no existen."""
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
                CREATE INDEX IF NOT EXISTS idx_pacientes_pendientes
                ON pacientes (mensaje_enviado, fecha_carga);
            """)
            cur.execute("""
                ALTER TABLE pacientes ADD COLUMN IF NOT EXISTS dni TEXT UNIQUE;
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
                    fecha_carga = CURRENT_DATE
                WHERE id = %s;
                """,
                (dni.strip(), nombre.strip(), apellido.strip(), telefono.strip(), paciente_id)
            )
        conn.commit()


def pacientes_pendientes_de_ayer() -> list:
    ayer = (date.today() - timedelta(days=1)).isoformat()
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre, apellido, telefono
                FROM pacientes
                WHERE fecha_carga = %s AND mensaje_enviado = FALSE
                ORDER BY id ASC;
                """,
                (ayer,)
            )
            return cur.fetchall()


def marcar_enviado(paciente_id: int):
    with _conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pacientes
                SET mensaje_enviado = TRUE, fecha_envio = now()
                WHERE id = %s;
                """,
                (paciente_id,)
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
