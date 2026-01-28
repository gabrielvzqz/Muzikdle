from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from config import Config
from models import ImagenModel

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Instancia del modelo
imagen_model = ImagenModel()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Ruta para obtener la imagen del día
@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

# Ruta para archivos estáticos del frontend (CSS, JS)
@app.route('/<path:filename>')
def serve_frontend_files(filename):
    return send_from_directory('../frontend', filename)

# Ruta para archivos dentro de carpetas (css/, js/)
@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('../frontend/css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('../frontend/js', filename)
@app.route('/api/imagen-del-dia', methods=['GET'])
def get_imagen_del_dia():
    try:
        imagen = imagen_model.get_imagen_del_dia()
        
        if imagen:
            # Construir URL completa de la imagen
            imagen_url = f"{app.config['BASE_URL']}/uploads/{os.path.basename(imagen['ruta_archivo'])}"
            
            return jsonify({
                'success': True,
                'imagen': {
                    'id': imagen['id'],
                    'titulo': imagen['titulo'],
                    'descripcion': imagen['descripcion'],
                    'url': imagen_url,
                    'fecha_programada': imagen['fecha_programada'].isoformat() if imagen['fecha_programada'] else None
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No hay imágenes disponibles'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# Ruta para subir nuevas imágenes
@app.route('/api/subir-imagen', methods=['POST'])
def subir_imagen():
    try:
        # Verificar si se envió el archivo
        if 'imagen' not in request.files:
            return jsonify({'success': False, 'message': 'No se encontró la imagen'}), 400
        
        file = request.files['imagen']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nombre de archivo vacío'}), 400
        
        if file and allowed_file(file.filename):
            # Obtener datos del formulario
            titulo = request.form.get('titulo', 'Sin título')
            descripcion = request.form.get('descripcion', '')
            fecha_programada = request.form.get('fecha_programada')
            
            # Guardar archivo
            filename = secure_filename(file.filename)
            # Agregar timestamp para evitar duplicados
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Guardar en base de datos
            imagen_id = imagen_model.subir_imagen(
                nombre_archivo=filename,
                ruta_archivo=unique_filename,
                titulo=titulo,
                descripcion=descripcion,
                fecha_programada=fecha_programada
            )
            
            return jsonify({
                'success': True,
                'message': 'Imagen subida correctamente',
                'imagen_id': imagen_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Tipo de archivo no permitido'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al subir imagen: {str(e)}'
        }), 500

# Ruta para servir archivos estáticos (imágenes)
@app.route('/uploads/<filename>')
def servir_imagen(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# Nueva ruta para obtener TODAS las imágenes del día
# En la función get_imagenes_del_dia() y similares:
@app.route('/api/imagenes-del-dia', methods=['GET'])
def get_imagenes_del_dia():
    try:
        imagenes = imagen_model.get_imagenes_del_dia()
        
        if imagenes:
            # CAMBIA ESTO:
            for imagen in imagenes:
                # En lugar de localhost, usa la URL base de la solicitud
                imagen['url'] = f"{request.host_url}uploads/{os.path.basename(imagen['ruta_archivo'])}"
                # O mejor aún:
                imagen['url'] = f"/uploads/{os.path.basename(imagen['ruta_archivo'])}"  # URL relativa
            
            return jsonify({
                'success': True,
                'imagenes': imagenes,
                'total': len(imagenes)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No hay imágenes para hoy'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
# Ruta para obtener todas las imágenes
@app.route('/api/imagenes', methods=['GET'])
def get_todas_imagenes():
    try:
        imagenes = imagen_model.get_todas_imagenes()
        
        # Añadir URL completa a cada imagen
        for imagen in imagenes:
            imagen['url'] = f"{app.config['BASE_URL']}/uploads/{os.path.basename(imagen['ruta_archivo'])}"
        
        return jsonify({
            'success': True,
            'imagenes': imagenes
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# Ruta para programar imagen
@app.route('/api/programar-imagen', methods=['POST'])
def programar_imagen():
    try:
        data = request.get_json()
        imagen_id = data.get('imagen_id')
        fecha = data.get('fecha')
        
        if not imagen_id or not fecha:
            return jsonify({
                'success': False,
                'message': 'Se requiere imagen_id y fecha'
            }), 400
        
        resultado = imagen_model.programar_imagen(imagen_id, fecha)
        
        return jsonify({
            'success': True,
            'message': 'Imagen programada correctamente'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
@app.route('/api/todos-titulos', methods=['GET'])
def get_todos_titulos():
    try:
        # Obtener todos los títulos de imágenes activas
        query = "SELECT DISTINCT titulo FROM imagenes WHERE activa = TRUE"
        
        # Necesitas modificar tu models.py para ejecutar esta query
        # O hacerlo directamente:
        from database import Database
        db = Database()
        result = db.execute_query(query, fetch=True)
        
        titulos = [row['titulo'] for row in result] if result else []
        
        return jsonify({
            'success': True,
            'titulos': titulos
        })
            
    except Exception as e:
        # Lista de respaldo si hay error
        titulos_respaldo = [
            "parís", "londres", "roma", "berlín", "madrid", 
            "barcelona", "nueva york", "tokio", "sídney", "moscú"
        ]
        
        return jsonify({
            'success': True,
            'titulos': titulos_respaldo
        })
# Ruta para obtener el historial completo
@app.route('/api/historial-completo', methods=['GET'])
def get_historial_completo():
    try:
        # Intento 1: Query optimizada
        query = """
        SELECT 
            fecha_programada,
            COUNT(*) as total_imagenes
        FROM imagenes 
        WHERE activa = TRUE 
        AND fecha_programada IS NOT NULL
        GROUP BY fecha_programada
        ORDER BY fecha_programada DESC
        """
        
        from database import Database
        db = Database()
        db.connect()
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute(query)
        resultados = cursor.fetchall()
        cursor.close()
        db.connection.close()
        
        if not resultados:
            # Si no hay datos, genera algunos
            return jsonify({
                'success': True,
                'albumes': generar_albumes_ejemplo(30),
                'total': 30,
                'mensaje': 'Base de datos vacía - datos de ejemplo'
            })
        
        # Formatear resultados
        albumes = []
        for row in resultados:
            # Asegurar formato de fecha
            fecha = row['fecha_programada']
            if hasattr(fecha, 'isoformat'):
                fecha_str = fecha.isoformat()
            elif isinstance(fecha, str):
                fecha_str = fecha.split()[0]  # Si tiene hora, toma solo fecha
            else:
                fecha_str = str(fecha)
            
            albumes.append({
                'fecha_programada': fecha_str,
                'total_imagenes': row['total_imagenes'],
                'primer_titulo': f'Álbum del {fecha_str}',
                'completado': row['total_imagenes'] >= 6
            })
        
        return jsonify({
            'success': True,
            'albumes': albumes,
            'total': len(albumes)
        })
        
    except Exception as e:
        print(f"Error en historial: {str(e)}")
        # En caso de error grave, devuelve datos de ejemplo
        return jsonify({
            'success': True,
            'albumes': generar_albumes_ejemplo(15),
            'total': 15,
            'error': str(e),
            'mensaje': 'Usando datos de ejemplo debido a error'
        })

def generar_albumes_ejemplo(cantidad=30):
    from datetime import datetime, timedelta
    
    albumes = []
    hoy = datetime.now().date()
    
    for i in range(cantidad):
        fecha = hoy - timedelta(days=i)
        albumes.append({
            'fecha_programada': fecha.isoformat(),
            'total_imagenes': 6,
            'primer_titulo': f'Álbum del {fecha.strftime("%d/%m/%Y")}',
            'completado': True
        })
    
    return albumes
# Ruta para obtener un álbum específico por fecha
@app.route('/api/album/<fecha>', methods=['GET'])
def get_album_por_fecha(fecha):
    try:
        # Obtener imágenes para una fecha específica
        query = """
        SELECT * FROM imagenes 
        WHERE fecha_programada = %s AND activa = TRUE
        ORDER BY orden_dia
        """
        
        from database import Database
        db = Database()
        db.connect()
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute(query, (fecha,))
        imagenes = cursor.fetchall()
        cursor.close()
        
        if not imagenes:
            return jsonify({
                'success': False,
                'message': 'No se encontró el álbum'
            }), 404
        
        # Añadir URLs
        for imagen in imagenes:
            imagen['url'] = f"/uploads/{os.path.basename(imagen['ruta_archivo'])}"
        
        return jsonify({
            'success': True,
            'fecha': fecha,
            'imagenes': imagenes,
            'total': len(imagenes),
            'titulo_final': imagenes[-1]['titulo'] if imagenes else None
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)