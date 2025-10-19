from sqlmodel import Session
from app.core.db import engine
from app.models.usuario import Usuario
from app.models.ubicacion import Ubicacion
from app.models.equipo import Equipo
from app.core.security import hash_password

def run():
    with Session(engine) as s:
        if not s.query(Usuario).first():
            s.add_all([
                Usuario(username="admin", password_hash=hash_password("admin123"), role="ADMIN"),
                Usuario(username="mant",  password_hash=hash_password("mant123"),  role="MANTENIMIENTO"),
                Usuario(username="op",    password_hash=hash_password("op123"),    role="OPERARIO"),
            ])
        if not s.query(Ubicacion).first():
            s.add_all([
                Ubicacion(nombre="Almacén Central", tipo="ALMACEN"),
                Ubicacion(nombre="Lab Metrología",  tipo="LAB"),
                Ubicacion(nombre="OPERARIO: Juan Pérez", tipo="PERSONA"),
            ])
        if not s.query(Equipo).first():
            s.add_all([
                Equipo(codigo="EQ-0001", tipo="Calibrador"),
                Equipo(codigo="EQ-0002", tipo="Manómetro"),
            ])
        s.commit()

if __name__ == "__main__":
    run()
