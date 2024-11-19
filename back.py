from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
import json
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
from flask_login import current_user
import json
import mysql.connector
import os
import random
from datetime import datetime, timedelta
import pickle


# Convertir la fecha a días del año
def convertir_fecha_a_dias(fecha):
    fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
    inicio_año = datetime(fecha_obj.year, 1, 1)
    return (fecha_obj - inicio_año).days

# Generar un tipo de uva aleatorio
def generar_tipo_uva():
    tipos_uva = ["Cabernet Sauvignon", "Malbec", "Chardonnay"]
    return random.choice(tipos_uva)

# Generar una fecha aleatoria dentro de un rango
def generar_fecha_aleatoria(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime("%Y-%m-%d")

# Generar cantidad y litros aleatorios
def generar_cantidad_y_litros():
    cantidad = random.randint(8000, 20000)  # en Kg
    litros = random.randint(1000, 3000)  # en Litros
    return cantidad, litros

# Guardar los datos generados en un archivo JSON
def guardar_datos_en_json(num_datos=10):
    start_date = datetime(2023, 1, 1)  # Fecha de inicio
    end_date = datetime(2023, 12, 31)  # Fecha de fin
    
    datos = []
    
    for _ in range(num_datos):
        fecha = generar_fecha_aleatoria(start_date, end_date)
        uva = generar_tipo_uva()
        cantidad, litros = generar_cantidad_y_litros()
        
        # Crear un objeto con los datos generados
        dato = {
            "fecha": fecha,
            "uva": uva,
            "cantidad": cantidad,
            "litros": litros
        }
        
        datos.append(dato)
    
    # Guardar los datos en un archivo JSON
    with open('cosecha.json', 'w') as archivo:
        json.dump(datos, archivo, indent=4)
    
    print(f"{num_datos} datos generados y guardados en cosecha.json.")

# Llamar a la función para generar y guardar los datos
guardar_datos_en_json(10)  # Generar 10 datos de ejemplo

# Cargar los datos JSON
def cargar_datos_json():
    with open('cosecha.json', 'r') as archivo:
        datos = json.load(archivo)
    return datos

# Preparar los datos para el entrenamiento
def preparar_datos():
    datos = cargar_datos_json()
    
    fechas = [convertir_fecha_a_dias(d['fecha']) for d in datos]
    tipos_uva = [d['uva'] for d in datos]  # Tipos de uva (cadena)
    cantidad = [d['cantidad'] for d in datos]  # Cantidad en Kg
    litros = [d['litros'] for d in datos]  # Litros producidos

    tipos_uva_map = {
        "Cabernet Sauvignon": 1,
        "Malbec": 2,
        "Chardonnay": 3,  # Asegúrate de que esta línea esté presente
        "Merlot": 4,
        "Ruby Cabernet": 5,
        "Cinsault": 6,
        "Fumé Blanc": 7,
        "Tempranillo": 8
    }


    tipos_uva_codificados = [tipos_uva_map[uva] for uva in tipos_uva]


    # Organizar los datos
    entradas = np.column_stack((fechas, tipos_uva_codificados, cantidad, litros))

    # Normalizar los datos
    scaler = StandardScaler()
    entradas_normalizadas = scaler.fit_transform(entradas)
    
    return entradas_normalizadas, cantidad, scaler

# Crear y entrenar el modelo
def crear_modelo():
    modelo = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(4,)),  # Solo 4 características (fecha, uva, cantidad, litros)
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1)  # Salida para la predicción de cantidad
    ])
    
    modelo.compile(optimizer='adam', loss='mse', metrics=['mae'])  # MSE y MAE
    return modelo

# Preparar y entrenar el modelo
entradas_normalizadas, etiquetas, scaler = preparar_datos()
modelo = crear_modelo()
modelo.fit(entradas_normalizadas, np.array(etiquetas, dtype=np.float32), epochs=50, batch_size=32)

# Guardar el modelo en formato .keras
modelo.save("modelo_tf.keras")

# Guardar el scaler como archivo pickle
def guardar_scaler_pickle(scaler, filename='scaler.pkl'):
    with open(filename, 'wb') as f:
        pickle.dump(scaler, f)

guardar_scaler_pickle(scaler)

# Cargar el modelo en formato .keras
modelo = tf.keras.models.load_model("modelo_tf.keras")

# Cargar el scaler desde archivo pickle
def cargar_scaler_pickle(filename='scaler.pkl'):
    with open(filename, 'rb') as f:
        scaler = pickle.load(f)
    return scaler

# Cargar el scaler
scaler = cargar_scaler_pickle()
def get_db_connection():
    connection = mysql.connector.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['database']
    )
    return connection

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  
    'database': 'gestion_de_bodega'
}
# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Si el usuario no está logueado, lo redirige al login

# Cargar el usuario actual
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Cargar usuarios desde un archivo JSON
def load_users():
    try:
        with open("usuarios.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open("usuarios.json", "w") as f:
        json.dump(users, f)

# Clase de Usuario para la autenticación con Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email, password):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
    
    @classmethod
    def get(cls, user_id):
        users = load_users()
        for user_data in users.values():
            if user_data['id'] == user_id:
                return cls(user_data['id'], user_data['username'], user_data['email'], user_data['password'])
        return None

    @classmethod
    def create(cls, username, email, password):
        users = load_users()
        user_id = str(len(users) + 1)  # Simple incrementing ID
        new_user = cls(user_id, username, email, password)
        users[user_id] = {
            "id": user_id,
            "username": username,
            "email": email,
            "password": password
        }
        save_users(users)
        return new_user

# Rutas de la aplicación
@app.route("/")
def index():
    return render_template("index.html")
# Solo usuarios logueados pueden acceder





@app.route("/pagina")
@login_required  # Requiere que el usuario esté logueado
def pagina():
    return render_template("pagina.html", prediccion=None)



@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    if request.method == "POST":  # Solo se ejecuta cuando el formulario de cierre de sesión se envía
        logout_user()  # Desloguea al usuario
        flash("Has cerrado sesión correctamente", "success")  # Muestra un mensaje de éxito
        return redirect(url_for("login"))  # Redirige a la página de login
    # Si la ruta es visitada con GET (por ejemplo, si se navega directamente a /logout sin enviar el formulario),
    # también podrías redirigir o manejar la sesión de alguna forma si lo deseas.
    return redirect(url_for("login"))# Redirige a la página de login

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        # Cargar el archivo usuarios.json
        with open('usuarios.json', 'r') as file:
            usuarios = json.load(file)

        # Buscar el usuario por correo electrónico
        usuario_encontrado = None
        for user_id, usuario in usuarios.items():
            if usuario["email"] == email:
                usuario_encontrado = usuario
                break

        if usuario_encontrado:
            # Comparar contraseñas directamente
            if usuario_encontrado["password"] == password:
                # Crear un objeto User para Flask-Login
                user = User(usuario_encontrado["id"], usuario_encontrado["username"], usuario_encontrado["email"], usuario_encontrado["password"])
                login_user(user)  # Iniciar sesión
                return redirect(url_for("index"))  # Redirigir a la página principal

            else:
                flash("Contraseña incorrecta", "danger")
        else:
            flash("Correo electrónico no encontrado", "danger")

    return render_template("login.html")

    if current_user.is_authenticated:
        return redirect(url_for("index"))  # Si el usuario ya está logueado, redirige a la página principal

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        # Cargar el archivo usuarios.json
        with open('usuarios.json', 'r') as file:
            usuarios = json.load(file)

        # Buscar el usuario por correo electrónico
        usuario_encontrado = None
        for user_id, usuario in usuarios.items():
            if usuario["email"] == email:
                usuario_encontrado = usuario
                break

        if usuario_encontrado:
            # Comparar contraseñas directamente
            if usuario_encontrado["password"] == password:
                # Crear un objeto User para Flask-Login
                user = User(usuario_encontrado["id"], usuario_encontrado["username"], usuario_encontrado["email"], usuario_encontrado["password"])
                login_user(user)  # Iniciar sesión

                flash("Inicio de sesión exitoso", "success")
                return redirect(url_for("index"))  # Redirigir a la página principal

            else:
                flash("Contraseña incorrecta", "danger")
        else:
            flash("Correo electrónico no encontrado", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]  # Cambiar "name" a "username"
        email = request.form["email"]
        password = request.form["password"]

        # Verificar si el archivo usuarios.json existe, si no, crearlo
        if not os.path.exists("usuarios.json"):
            with open("usuarios.json", "w") as f:
                json.dump({}, f)  # Crear archivo vacío con un diccionario vacío

        # Leer el archivo usuarios.json de forma segura
        with open("usuarios.json", "r") as f:
            try:
                usuarios = json.load(f)
            except json.decoder.JSONDecodeError:
                usuarios = {}  # Si el archivo está vacío o malformado, inicializar como un diccionario vacío

        # Verificar si el correo electrónico ya está registrado
        if any(u["email"] == email for u in usuarios.values()):
            flash("El correo electrónico ya está registrado", "danger")
            return redirect(url_for("register"))
        
        # Crear el nuevo usuario
        nuevo_usuario = {
            "id": str(len(usuarios) + 1),  # Generar un nuevo ID (en base al número de usuarios)
            "username": username,
            "email": email,
            "password": password  # Aquí no estamos cifrando la contraseña
        }

        # Agregar el nuevo usuario a los usuarios existentes
        usuarios[nuevo_usuario["id"]] = nuevo_usuario

        # Guardar los usuarios actualizados en el archivo usuarios.json
        with open("usuarios.json", "w") as f:
            json.dump(usuarios, f, indent=4)

        flash("Usuario registrado exitosamente", "success")
        return redirect(url_for("login"))

    return render_template("register.html")






@app.route('/predecir', methods=['POST'])
def predecir():
    fecha = request.form['fecha']
    uva = request.form['uva']  # El valor de 'uva' debe ser una cadena
    cantidad = float(request.form['cantidad'])
    litros = float(request.form['litros'])

    # Convertir la fecha a días del año
    fecha_convertida = convertir_fecha_a_dias(fecha)

    # Codificar el tipo de uva usando el nombre de la uva como clave
    tipos_uva_map = {
        "Cabernet Sauvignon": 1,
        "Malbec": 2,
        "Chardonnay": 3,
        "Merlot": 4,
        "Ruby Cabernet": 5,
        "Cinsault": 6,
        "Fumé Blanc": 7,
        "Tempranillo": 8
    }

    # Usar el nombre de la uva directamente (sin convertir a int)
    uva_codificada = tipos_uva_map.get(uva, 0)  # Si no se encuentra, devuelve 0 (valor predeterminado)

    # Preparar los datos de entrada
    datos_entrada = np.array([[fecha_convertida, uva_codificada, cantidad, litros]])
    datos_entrada_normalizados = scaler.transform(datos_entrada)

    # Realizar la predicción
    prediccion = modelo.predict(datos_entrada_normalizados)

    # Buscar la mejor comparación con los datos de entrenamiento
    mejor_comparacion = obtener_mejor_comparacion(fecha_convertida, uva_codificada, cantidad, litros)

    # Devolver el resultado a la plantilla
    return render_template('pagina.html', prediccion=prediccion[0][0], mejor_comparacion=mejor_comparacion)

# Función para obtener la mejor comparación con los datos de entrenamiento
def obtener_mejor_comparacion(fecha, uva, cantidad, litros):
    datos = cargar_datos_json()  # Cargar los datos generados
    mejor_comparacion = min(datos, key=lambda d: abs(convertir_fecha_a_dias(d['fecha']) - fecha))
    return mejor_comparacion


if __name__ == "__main__":
    app.run(debug=True)
