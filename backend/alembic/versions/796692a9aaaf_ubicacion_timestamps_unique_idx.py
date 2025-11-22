"""ubicacion: timestamps + unique + idx

Revision ID: 796692a9aaaf
Revises: adc6fbc7ed40
Create Date: 2025-10-27 01:08:16.233025
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = "e3f1a2b9c7d0"
down_revision = "c1b044594b18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 1) Nuevas columnas de timestamp (UTC) ---
    # Se añaden con server_default now() para rellenar filas existentes.
    with op.batch_alter_table("ubicacion") as batch_op:
        batch_op.add_column(
            sa.Column(
                "creado_en",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "actualizado_en",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            )
        )

    # --- 2) Índices útiles ---
    # Usamos SQL crudo con IF NOT EXISTS para evitar colisiones por nombres.
    conn = op.get_bind()
    conn.execute(sa.text('CREATE INDEX IF NOT EXISTS "ix_ubicacion_nombre" ON ubicacion (nombre);'))
    conn.execute(sa.text('CREATE INDEX IF NOT EXISTS "ix_ubicacion_seccion" ON ubicacion (seccion_id);'))

    # --- 3) Restricción única (seccion_id, nombre) ---
    # Nota: fallará si hay duplicados existentes.
    # Intentamos crearla sólo si no existe; si aún así hay duplicados, informamos sin romper migración por completo.
    try:
        conn.execute(
            sa.text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'uq_ubicacion_seccion_nombre'
                    ) THEN
                        ALTER TABLE ubicacion
                        ADD CONSTRAINT "uq_ubicacion_seccion_nombre"
                        UNIQUE (seccion_id, nombre);
                    END IF;
                END $$;
                """
            )
        )
    except Exception as e:
        # Suele indicar duplicados en (seccion_id, nombre).
        # Mostramos aviso claro en logs; la migración puede continuar si lo prefieres.
        print(
            "[alembic][WARN] No se pudo crear UNIQUE (seccion_id, nombre) en 'ubicacion'. "
            "Posibles duplicados. Revisa y deduplica antes de reintentar.\n"
            f"Detalle: {e}"
        )
        # Si prefieres abortar aquí, descomenta la siguiente línea:
        # raise


def downgrade() -> None:
    conn = op.get_bind()

    # 1) Eliminar UNIQUE (si existe)
    try:
        conn.execute(
            sa.text(
                'ALTER TABLE ubicacion DROP CONSTRAINT IF EXISTS "uq_ubicacion_seccion_nombre";'
            )
        )
    except Exception as e:
        print(f"[alembic][WARN] No se pudo eliminar UNIQUE uq_ubicacion_seccion_nombre: {e}")

    # 2) Eliminar índices (si existen)
    try:
        conn.execute(sa.text('DROP INDEX IF EXISTS "ix_ubicacion_nombre";'))
    except Exception as e:
        print(f"[alembic][WARN] No se pudo eliminar índice ix_ubicacion_nombre: {e}")

    try:
        conn.execute(sa.text('DROP INDEX IF EXISTS "ix_ubicacion_seccion";'))
    except Exception as e:
        print(f"[alembic][WARN] No se pudo eliminar índice ix_ubicacion_seccion: {e}")

    # 3) Quitar columnas timestamp
    with op.batch_alter_table("ubicacion") as batch_op:
        try:
            batch_op.drop_column("actualizado_en")
        except Exception as e:
            print(f"[alembic][WARN] No se pudo eliminar columna actualizado_en: {e}")
        try:
            batch_op.drop_column("creado_en")
        except Exception as e:
            print(f"[alembic][WARN] No se pudo eliminar columna creado_en: {e}")