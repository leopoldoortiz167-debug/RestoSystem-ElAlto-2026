from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'resto-2026-el-alto-seguro'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resto.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30) # Sesión dura 30 min
db = SQLAlchemy(app)

# ===== MODELOS =====
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    contrasena = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(50), default='Admin')

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=50)
    categoria = db.Column(db.String(50))

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mesa = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.now)
    estado = db.Column(db.String(20), default='Pendiente')
    total = db.Column(db.Float, default=0)
    notas = db.Column(db.Text)

class Detalle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_pedido = db.Column(db.Integer, db.ForeignKey('pedido.id'))
    id_producto = db.Column(db.Integer, db.ForeignKey('producto.id'))
    cantidad = db.Column(db.Integer)
    subtotal = db.Column(db.Float)

def inicializar_bd():
    with app.app_context():
        db.create_all()
        if not Usuario.query.first():
            db.session.add(Usuario(nombre='admin', contrasena='admin123', rol='Admin'))
        if not Producto.query.first():
            productos = [
                Producto(nombre='Pique Macho', precio=35.00, stock=45, categoria='Plato'),
                Producto(nombre='Silpancho', precio=25.00, stock=50, categoria='Plato'),
                Producto(nombre='Fricasé', precio=30.00, stock=8, categoria='Plato'),
                Producto(nombre='Chairo', precio=15.00, stock=60, categoria='Sopa'),
                Producto(nombre='Coca Cola 2L', precio=12.00, stock=30, categoria='Bebida'),
                Producto(nombre='Mocochinchi', precio=8.00, stock=5, categoria='Bebida')
            ]
            db.session.add_all(productos)
        db.session.commit()

def login_requerido(f):
    def wrapper(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
@login_requerido
def dashboard():
    hoy = datetime.now().date()
    total = Pedido.query.count()
    hoy_count = Pedido.query.filter(func.date(Pedido.fecha) == hoy).count()
    ventas = db.session.query(func.sum(Pedido.total)).filter(func.date(Pedido.fecha) == hoy).scalar() or 0
    
    labels, datos = [], []
    for i in range(6, -1, -1):
        fecha = hoy - timedelta(days=i)
        labels.append(fecha.strftime('%d/%m'))
        total_dia = db.session.query(func.sum(Pedido.total)).filter(func.date(Pedido.fecha) == fecha).scalar() or 0
        datos.append(float(total_dia))
    
    stock_bajo = Producto.query.filter(Producto.stock < 10).all()
    return render_template('dashboard.html', total=total, hoy=hoy_count, ventas=ventas, 
                         labels=labels, datos=datos, stock_bajo=stock_bajo, usuario=session.get('usuario'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya estás logueado, te manda al dashboard
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        user = Usuario.query.filter_by(nombre=request.form['nombre'], contrasena=request.form['contrasena']).first()
        if user:
            session['usuario'] = user.nombre
            session['rol'] = user.rol
            session.permanent = True  # ← Esta línea hace que dure 30 min
            flash('Bienvenido al sistema', 'success')
            return redirect(url_for('dashboard'))
        flash('Usuario o contraseña incorrectos', 'error')
    return render_template('login.html')

@app.route('/pedidos', methods=['GET', 'POST'])
@login_requerido
def pedidos():
    if request.method == 'POST':
        nuevo = Pedido(mesa=int(request.form['mesa']), notas=request.form['notas'])
        db.session.add(nuevo)
        db.session.commit()
        producto = Producto.query.get(request.form['plato_id'])
        cantidad = int(request.form['cantidad'])
        subtotal = producto.precio * cantidad
        detalle = Detalle(id_pedido=nuevo.id, id_producto=producto.id, cantidad=cantidad, subtotal=subtotal)
        nuevo.total = subtotal
        producto.stock -= cantidad
        db.session.add(detalle)
        db.session.commit()
        flash('Pedido registrado', 'success')
        return redirect(url_for('pedidos'))
    platos = Producto.query.all()
    recientes = Pedido.query.order_by(Pedido.fecha.desc()).limit(5).all()
    return render_template('pedidos.html', platos=platos, recientes=recientes, usuario=session.get('usuario'))

@app.route('/cocina')
@login_requerido
def cocina():
    pedidos = Pedido.query.filter(Pedido.estado.in_(['Pendiente', 'Preparando'])).all()
    return render_template('cocina.html', pedidos=pedidos, usuario=session.get('usuario'))

@app.route('/estado/<int:id>/<estado>')
@login_requerido
def cambiar_estado(id, estado):
    pedido = Pedido.query.get_or_404(id)
    pedido.estado = estado
    db.session.commit()
    flash(f'Pedido #{id} actualizado a {estado}', 'info')
    return redirect(url_for('cocina'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    inicializar_bd()
    print("\n=== RESTOSYSTEM FUNCIONANDO ===")
    print("Usuario: admin | Contraseña: admin123")
    print("URL: http://127.0.0.1:5000")
    print("Sesión dura: 30 minutos\n")
    app.run(debug=True)