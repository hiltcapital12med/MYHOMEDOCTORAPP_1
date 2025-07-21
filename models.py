from sqlalchemy import Column, Integer, String, Date, ForeignKey, Text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Miembro(Base):
    __tablename__ = 'miembros'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    apellido = Column(String(50), default='')
    sexo = Column(String(1), nullable=False)  # 'M' o 'F'
    fecha_nacimiento = Column(Date, nullable=False)
    edad_anios = Column(Integer)
    edad_meses = Column(Integer)
    edad_dias = Column(Integer)
    antecedentes_pat = Column(String(500), default='')
    antecedentes_quir = Column(String(500), default='')
    antecedentes_alerg = Column(String(500), default='')
    medicamentos_actuales = Column(Text, default='')  # Para JSON de medicamentos
    administrador_id = Column(Integer, ForeignKey('miembros.id'))
    
    hijos = relationship("Relacion", back_populates="padre", foreign_keys="[Relacion.padre_id]")
    padre_rel = relationship("Relacion", back_populates="hijo", foreign_keys="[Relacion.hijo_id]")
    
    @property
    def edad(self):
        return (self.edad_anios, self.edad_meses, self.edad_dias)

class Relacion(Base):
    __tablename__ = 'relaciones'
    id = Column(Integer, primary_key=True)
    padre_id = Column(Integer, ForeignKey('miembros.id'), nullable=False)
    hijo_id = Column(Integer, ForeignKey('miembros.id'), nullable=False)
    
    padre = relationship("Miembro", foreign_keys=[padre_id], back_populates="hijos")
    hijo = relationship("Miembro", foreign_keys=[hijo_id], back_populates="padre_rel")
    
    @validates('padre_id', 'hijo_id')
    def validar_edades(self, key, value):
        # Implementar validación si es necesaria
        return value

# Validación de relaciones para evitar ciclos o duplicidades
def validar_relacion(session, padre, hijo):
    # Evita que un miembro sea su propio padre/hijo
    if padre.id == hijo.id:
        raise ValueError("Un miembro no puede ser su propio padre/hijo.")
    # Evita ciclos directos
    relaciones = session.query(Relacion).filter_by(padre_id=hijo.id, hijo_id=padre.id).first()
    if relaciones:
        raise ValueError("Relación familiar inválida (ciclo detectado).")
