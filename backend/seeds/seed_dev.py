# backend/seeds/seed_dev.py
from sqlmodel import Session, select
from app.core.db import engine
from app.models.usuario import Usuario
from app.models.ubicacion import Ubicacion
from app.models.equipo import Equipo
from app.core.security import hash_password

def ensure_admin(session: Session) -> None:
    admin = session.exec(select(Usuario).where(Usuario.username == "admin")).first()
    if not admin:
        session.add(
            Usuario(
                username="admin",
                password_hash=hash_password("admin123"),
                role="ADMIN",
                active=True,
            )
        )

def ensure_defaults(session: Session) -> None:
    # Ubicaciones por defecto (SIN 'tipo')
    has_ubis = session.exec(select(Ubicacion)).first()
    if not has_ubis:
        session.add_all(
            [
                Ubicacion(nombre="Almacén Central"),
                Ubicacion(nombre="Lab Metrología"),
                Ubicacion(nombre="OPERARIO: Juan Pérez"),
            ]
        )

    # Equipos por defecto
    has_eqs = session.exec(select(Equipo)).first()
    if not has_eqs:
        session.add_all(
            [
                Equipo(identidad="EQ-0001", numero_serie="SN-0001"),
                Equipo(identidad="EQ-0002", numero_serie="SN-0002"),
            ]
        )

def run() -> None:
    with Session(engine) as s:
        ensure_admin(s)
        ensure_defaults(s)
        s.commit()

if __name__ == "__main__":
    run()
