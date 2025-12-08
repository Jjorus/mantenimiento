# backend/seeds/seed_dev.py
from sqlmodel import Session, select
from app.core.db import engine
from app.models.usuario import Usuario
from app.models.ubicacion import Ubicacion
from app.models.equipo import Equipo
from app.core.security import hash_password


def ensure_admin(session: Session) -> Usuario:
    """
    Crea (si no existe) el usuario admin.
    Devuelve siempre el admin.
    """
    admin = session.exec(
        select(Usuario).where(Usuario.username == "admin")
    ).first()
    if not admin:
        admin = Usuario(
            username="admin",
            email="admin@mantenimiento.com",
            password_hash=hash_password("admin123"),
            role="ADMIN",
            active=True,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
    return admin


def ensure_tecnico(session: Session) -> Usuario:
    """
    Crea (si no existe) un usuario técnico por defecto.
    Devuelve siempre ese usuario técnico.
    """
    tecnico = session.exec(
        select(Usuario).where(Usuario.username == "tecnico1")
    ).first()
    if not tecnico:
        tecnico = Usuario(
            username="tecnico1",
            email="tecnico@mantenimiento.com",
            password_hash=hash_password("tecnico123"),
            role="OPERARIO",
            active=True,
        )
        session.add(tecnico)
        session.commit()
        session.refresh(tecnico)
    return tecnico


def ensure_defaults(session: Session, tecnico: Usuario) -> None:
    """
    Crea ubicaciones y equipos por defecto.

    IMPORTANTE:
    - Usa el nuevo esquema de Ubicacion con 'tipo' y 'usuario_id'.
    - Asocia una ubicación de tipo TECNICO al usuario 'tecnico1'.
    """
    # Ubicaciones por defecto
    has_ubis = session.exec(select(Ubicacion)).first()
    if not has_ubis:
        almac = Ubicacion(
            nombre="Almacén Central",
            tipo="ALMACEN",
        )
        lab = Ubicacion(
            nombre="Lab Metrología",
            tipo="LABORATORIO",
        )
        ubi_tecnico = Ubicacion(
            nombre="OPERARIO: Técnico 1",
            tipo="TECNICO",
            usuario_id=tecnico.id,  # <- ubicación personal del técnico
        )
        session.add_all([almac, lab, ubi_tecnico])
        session.commit()

    # Equipos por defecto
    # 'tipo' (obligatorio) y 'estado' para cumplir con el esquema
    has_eqs = session.exec(select(Equipo)).first()
    if not has_eqs:
        session.add_all(
            [
                Equipo(
                    identidad="EQ-0001",
                    numero_serie="SN-0001",
                    tipo="Multímetro",
                    estado="OPERATIVO",
                ),
                Equipo(
                    identidad="EQ-0002",
                    numero_serie="SN-0002",
                    tipo="Calibrador",
                    estado="OPERATIVO",
                ),
            ]
        )
        session.commit()


def run() -> None:
    """
    Ejecuta el seed completo para entorno de desarrollo:
    - admin
    - tecnico1 + su ubicación
    - ubicaciones y equipos por defecto
    """
    with Session(engine) as s:
        admin = ensure_admin(s)
        tecnico = ensure_tecnico(s)
        ensure_defaults(s, tecnico)


if __name__ == "__main__":
    run()
