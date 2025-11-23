# backend/scripts/drop_reparacion_factura.py

from sqlalchemy import create_engine, text
from app.core.config import settings

def main():
    engine = create_engine(settings.DATABASE_URL)

    sql = """
    DROP TABLE IF EXISTS reparacion_factura CASCADE;
    """
    print("Conectando a la base de datos...")
    with engine.connect() as conn:
        print("Ejecutando:", sql.strip())
        conn.execute(text(sql))
        conn.commit()
    print("Tabla reparacion_factura eliminada (si existía).")

if __name__ == "__main__":
    main()
