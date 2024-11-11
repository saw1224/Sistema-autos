from flask import Flask, render_template, request, redirect, url_for, jsonify
from pyzbar.pyzbar import decode
import cv2
import base64
import numpy as np
from datetime import datetime
import pyodbc

app = Flask(__name__)

# Conexión a SQL Server
connection_string = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=DESKTOP-1F9VP1F\SQLEXPRESS;DATABASE=carrosISI;UID=saa;PWD=12345'
)

def registrar_salida_regreso(qr_code, nombre_tecnico, ultimo_mantenimiento, accion):
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        try:
            ultimo_mantenimiento_dt = datetime.fromisoformat(ultimo_mantenimiento)
        except ValueError as e:
            print(f"Formato de fecha incorrecto en 'ultimo_mantenimiento': {e}")
            return False

        print(f"Registrando con QR code: {qr_code}, Acción: {accion}")

        query_select = "SELECT id, salida, regreso FROM RegistrosAutos WHERE qr_code = ?"
        cursor.execute(query_select, (qr_code,))
        registro_existente = cursor.fetchone()

        if registro_existente:
            if accion == "Salida":
                query_update = "UPDATE RegistrosAutos SET salida = ?, nombre_tecnico = ?, ultimo_mantenimiento = ? WHERE qr_code = ?"
                cursor.execute(query_update, (datetime.now(), nombre_tecnico, ultimo_mantenimiento_dt, qr_code))
            elif accion == "Regreso":
                query_update = "UPDATE RegistrosAutos SET regreso = ?, nombre_tecnico = ?, ultimo_mantenimiento = ? WHERE qr_code = ?"
                cursor.execute(query_update, (datetime.now(), nombre_tecnico, ultimo_mantenimiento_dt, qr_code))
        else:
            if accion == "Salida":
                query_insert = "INSERT INTO RegistrosAutos (qr_code, nombre_tecnico, ultimo_mantenimiento, salida) VALUES (?, ?, ?, ?)"
                cursor.execute(query_insert, (qr_code, nombre_tecnico, ultimo_mantenimiento_dt, datetime.now()))
            else:
                print(f"No se puede registrar regreso sin salida para QR: {qr_code}")
                return False

        conn.commit()
        print("Datos guardados correctamente")
        return True
    except pyodbc.DatabaseError as e:
        print(f"Error de base de datos en registrar_salida_regreso: {e}")
        return False
    except Exception as e:
        print(f"Error general en registrar_salida_regreso: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    registros = []
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query_view = "SELECT TOP (1000) [id], [qr_code], [nombre_tecnico], [ultimo_mantenimiento], [salida], [regreso] FROM [carrosISI].[dbo].[RegistrosAutos]"
        cursor.execute(query_view)
        registros = cursor.fetchall()
    except Exception as e:
        print(f"Error al conectar o consultar la base de datos en index: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

    if request.method == 'POST':
        nombre_tecnico = request.form['nombre_tecnico']
        ultimo_mantenimiento = request.form['ultimo_mantenimiento']
        qr_data = request.form['qr_data']
        accion = request.form['accion']

        print(f"Datos recibidos para registrar: QR Code: {qr_data}, Persona: {nombre_tecnico}, Mantenimiento: {ultimo_mantenimiento}, Acción: {accion}")

        if qr_data and registrar_salida_regreso(qr_data, nombre_tecnico, ultimo_mantenimiento, accion):
            return redirect(url_for('confirmacion', qr_data=qr_data, nombre_tecnico=nombre_tecnico, accion=accion))
        else:
            print("Error en el registro. Datos: ", qr_data, nombre_tecnico, ultimo_mantenimiento, accion)
            return "Error en el registro"

    return render_template('index.html', registros=registros)

@app.route('/lista')
def lista():
    registros = []
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query_view = "SELECT id, qr_code, nombre_tecnico, ultimo_mantenimiento, salida, regreso FROM RegistrosAutos"
        cursor.execute(query_view)
        registros = cursor.fetchall()
        print("Registros obtenidos:", registros)
    except Exception as e:
        print(f"Error al conectar o consultar la base de datos en lista: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

    return render_template('lista.html', registros=registros)

@app.route('/confirmacion')
def confirmacion():
    qr_data = request.args.get('qr_data')
    nombre_tecnico = request.args.get('nombre_tecnico')
    accion = request.args.get('accion')
    return render_template('confirmacion.html', qr_data=qr_data, nombre_tecnico=nombre_tecnico, accion=accion)

@app.route('/escaneo_qr', methods=['POST'])
def escaneo_qr():
    data = request.json
    image_base64 = data['image']
    qr_data = procesar_imagen_qr(image_base64)

    if qr_data:
        return jsonify({'success': True, 'qr_data': qr_data})
    else:
        return jsonify({'success': False, 'message': 'No se detectó ningún QR'})

def procesar_imagen_qr(image_base64):
    image_data = base64.b64decode(image_base64)
    np_arr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    decoded_objects = decode(img)
    for obj in decoded_objects:
        qr_data = obj.data.decode('utf-8')
        return qr_data
    return None

@app.route('/verificar_qr', methods=['POST'])
def verificar_qr():
    data = request.json
    qr_code = data['qr_data']
    
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        query = "SELECT nombre_tecnico, ultimo_mantenimiento FROM RegistrosAutos WHERE qr_code = ?"
        cursor.execute(query, (qr_code,))
        resultado = cursor.fetchone()

        if resultado:
            nombre_tecnico, ultimo_mantenimiento = resultado
            return jsonify({
                'exists': True,
                'nombre_tecnico': nombre_tecnico,
                'ultimo_mantenimiento': ultimo_mantenimiento.isoformat() if ultimo_mantenimiento else None
            })
        else:
            return jsonify({'exists': False})

    except Exception as e:
        print(f"Error al verificar QR en la base de datos: {e}")
        return jsonify({'error': 'Error al verificar QR'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/checklist', methods=['GET', 'POST'])
def checklist():
    if request.method == 'POST':
        numero_coche = request.form['numero_coche']
        kilometraje = request.form['kilometraje']
        estado_llantas = request.form['estado_llantas']
        estado_rines = request.form['estado_rines']
        detalles_raspones = request.form['detalles_raspones']
        estado_faros = request.form['estado_faros']
        otros_detalles = request.form['otros_detalles']
        
        try:
            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()
            
            query = """
            IF EXISTS (SELECT 1 FROM CheckListAutos WHERE numero_coche = ?)
                UPDATE CheckListAutos 
                SET kilometraje = ?, estado_llantas = ?, estado_rines = ?, 
                    detalles_raspones = ?, estado_faros = ?, otros_detalles = ?,
                    ultima_actualizacion = GETDATE()
                WHERE numero_coche = ?
            ELSE
                INSERT INTO CheckListAutos (numero_coche, kilometraje, estado_llantas, estado_rines, 
                                            detalles_raspones, estado_faros, otros_detalles)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (numero_coche, kilometraje, estado_llantas, estado_rines, 
                                   detalles_raspones, estado_faros, otros_detalles, 
                                   numero_coche, numero_coche, kilometraje, estado_llantas, estado_rines, 
                                   detalles_raspones, estado_faros, otros_detalles))
            conn.commit()
            return redirect(url_for('checklist', message="Checklist actualizado correctamente"))
        except Exception as e:
            print(f"Error al actualizar el checklist: {e}")
            return redirect(url_for('checklist', error="Error al actualizar el checklist"))
        finally:
            if 'conn' in locals():
                conn.close()
    
    coches = []
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        query = "SELECT numero_coche FROM CheckListAutos"
        cursor.execute(query)
        coches = [row.numero_coche for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error al obtener la lista de coches: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
    
    return render_template('checklist.html', coches=coches, message=request.args.get('message'), error=request.args.get('error'))

@app.route('/get_car_details/<string:numero_coche>')
def get_car_details(numero_coche):
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        query = """
        SELECT numero_coche, kilometraje, estado_llantas, estado_rines, 
               detalles_raspones, estado_faros, otros_detalles, ultima_actualizacion 
        FROM CheckListAutos 
        WHERE numero_coche = ?
        """
        cursor.execute(query, (numero_coche,))
        car = cursor.fetchone()
        if car:
            return jsonify({
                "numero_coche": car.numero_coche,
                "kilometraje": car.kilometraje or "",
                "estado_llantas": car.estado_llantas or "",
                "estado_rines": car.estado_rines or "",
                "detalles_raspones": car.detalles_raspones or "",
                "estado_faros": car.estado_faros or "",
                "otros_detalles": car.otros_detalles or "",
                "ultima_actualizacion": car.ultima_actualizacion.isoformat() if car.ultima_actualizacion else ""
            })
        else:
            return jsonify({"error": "Coche no encontrado"}), 404
    except Exception as e:
        print(f"Error al obtener detalles del coche: {e}")
        return jsonify({"error": "Error al obtener detalles del coche"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(port=5000)