import os
import json
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from medical_app.models import Base, Miembro, Relacion, validar_relacion
from datetime import datetime, date, timedelta

# Configuración de Flask con rutas explícitas
dirs = os.path.dirname(__file__)
app = Flask(
    __name__,
    template_folder=os.path.join(dirs, 'templates'),
    static_folder=os.path.join(dirs, 'static')
)
CORS(app)

# SQLite: fichero familia.db en la raíz del proyecto
engine = create_engine('sqlite:///familia.db', connect_args={'check_same_thread': False})
# --- SOLO PARA DESARROLLO INICIAL: eliminar tablas antiguas si cambias modelos
# Base.metadata.drop_all(engine)
# Crear tablas según modelo actual
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# -------------------- Funciones Auxiliares --------------------
def calcular_edad(fecha_nac: date):
    hoy = date.today()
    anios = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
    meses = hoy.month - fecha_nac.month - (hoy.day < fecha_nac.day)
    if meses < 0:
        meses += 12
    dias = hoy.day - fecha_nac.day
    if dias < 0:
        prev_month_last = (hoy.replace(day=1) - timedelta(days=1)).day
        dias += prev_month_last
    return anios, meses, dias

# -------------------- Serialización a JSON --------------------
def miembro_to_dict(m: Miembro):
    # Medicamentos: intenta decodificar JSON, si no es posible, pasa como string
    try:
        meds = json.loads(m.medicamentos_actuales)
    except Exception:
        meds = m.medicamentos_actuales
    return {
        'id': m.id,
        'nombre': m.nombre,
        'apellido': m.apellido,
        'sexo': m.sexo,
        'fecha_nacimiento': m.fecha_nacimiento.isoformat(),
        'edad_anios': m.edad_anios,
        'edad_meses': m.edad_meses,
        'edad_dias': m.edad_dias,
        'antecedentes_pat': m.antecedentes_pat,
        'antecedentes_quir': m.antecedentes_quir,
        'antecedentes_alerg': m.antecedentes_alerg,
        'medicamentos_actuales': meds,
        'administrador_id': m.administrador_id
    }

# -------------------- Endpoints REST --------------------
@app.route('/members')
def api_members():
    session = Session()
    miembros = session.query(Miembro).all()
    data = [miembro_to_dict(m) for m in miembros]
    session.close()
    return jsonify(data)

@app.route('/family/<int:id>')
def api_family(id):
    session = Session()
    admin = session.query(Miembro).get(id)
    if not admin:
        session.close()
        return jsonify({'error': 'Miembro no encontrado'}), 404
    hijos = [miembro_to_dict(rel.hijo) for rel in admin.hijos]
    info = miembro_to_dict(admin)
    info['hijos'] = hijos
    session.close()
    return jsonify(info)

# -------------------- Rutas de Páginas --------------------
@app.route('/')
def index():
    session = Session()
    miembros = session.query(Miembro).all()
    session.close()
    return render_template('index.html', miembros=miembros)

@app.route('/miembro/nuevo', methods=['GET','POST'])
def nuevo_miembro():
    session = Session()
    if request.method == 'POST':
        data = request.form
        fn = datetime.strptime(data['fecha_nacimiento'], '%Y-%m-%d').date()
        anios, meses, dias = calcular_edad(fn)
        meds = []
        for k, v in data.items():
            if k.startswith('med_name_'):
                idx = k.split('_')[-1]
                freq = data.get(f'med_freq_{idx}')
                times = [val for key,val in data.items() if key.startswith(f'med_time_{idx}_')]
                meds.append({'name': v, 'frequency': freq, 'times': times})
        miembro = Miembro(
            nombre=data['nombre'],
            apellido=data.get('apellido',''),
            sexo=data['sexo'],
            fecha_nacimiento=fn,
            edad_anios=anios,
            edad_meses=meses,
            edad_dias=dias,
            antecedentes_pat=data.get('ante_pat',''),
            antecedentes_quir=data.get('ante_quir',''),
            antecedentes_alerg=data.get('ante_alerg',''),
            medicamentos_actuales=json.dumps(meds),
            administrador_id=int(data['admin']) if data.get('admin') else None
        )
        session.add(miembro)
        session.commit()
        session.close()
        return redirect(url_for('index'))
    admins = session.query(Miembro).all()
    session.close()
    return render_template('miembro.html', admins=admins)

@app.route('/familia/<int:id>')
def ver_familia(id):
    session = Session()
    admin = session.query(Miembro).get(id)
    session.close()
    return render_template('familia.html', admin=admin)

@app.route('/relacion/agregar', methods=['POST'])
def agregar_relacion():
    session = Session()
    padre_id = int(request.form['padre'])
    hijo_id = int(request.form['hijo'])
    padre = session.query(Miembro).get(padre_id)
    hijo = session.query(Miembro).get(hijo_id)
    validar_relacion(session, padre, hijo)
    rel = Relacion(padre=padre, hijo=hijo)
    session.add(rel)
    session.commit()
    session.close()
    return redirect(url_for('ver_familia', id=padre_id))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
