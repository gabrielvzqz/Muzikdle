from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from config import Config
from models import ImagenModel
import uuid

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://www.muzikdle.com",
            "https://muzikdle.com",
            "http://localhost:5000",  # Para desarrollo local
            "http://127.0.0.1:5000"   # Para desarrollo local
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
app.config.from_object(Config)

# Crear carpeta de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
@app.route('/robots.txt')
def robots():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'robots.txt',
        mimetype='text/plain'
    )

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'sitemap.xml',
        mimetype='application/xml'
    )

# Instancia del modelo
imagen_model = ImagenModel()
@app.route('/api/get-user-id', methods=['GET'])
def api_get_user_id():
    try:
        user_id = get_or_create_user_id()
        print(f"📤 Enviando user_id al frontend: {user_id}")
        return jsonify({
            'success': True,
            'user_id': user_id,
            'first_visit': session.get('first_visit')
        })
    except Exception as e:
        print(f"Error en get-user-id: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'user_id': 'error_' + str(uuid.uuid4())[:8]
        }), 500

def get_or_create_user_id():
    """Genera o recupera un ID único para el usuario"""
    print("=" * 60)
    print("🔍 DEBUG get_or_create_user_id()")
    
    # PRIMERA prioridad: user_id del frontend (localStorage)
    user_id_from_frontend = request.headers.get('X-User-ID')
    
    print(f"   X-User-ID en headers: {user_id_from_frontend}")
    
    # Si el frontend envía un user_id, USAR ESE SIEMPRE
    if user_id_from_frontend:
        print(f"   ✅ USER ID DEL FRONTEND (localStorage): {user_id_from_frontend}")
        
        # Guardar en sesión por compatibilidad
        session['user_id'] = user_id_from_frontend
        
        # Registrar primera visita si no existe
        if 'first_visit' not in session:
            session['first_visit'] = datetime.now().isoformat()
            print(f"   📅 Primera visita registrada: {session['first_visit']}")
        
        print(f"   🎯 User ID final (usando frontend): {user_id_from_frontend}")
        print("=" * 60)
        return user_id_from_frontend
    
    # Si no hay user_id del frontend (primera carga sin JS ejecutado)
    # Usar sesión existente o crear nueva
    if 'user_id' in session:
        print(f"   🔄 Usando sesión existente: {session['user_id']}")
        return session['user_id']
    else:
        # Crear nuevo user_id temporal
        nuevo_id = str(uuid.uuid4())[:12]
        session['user_id'] = nuevo_id
        session['first_visit'] = datetime.now().isoformat()
        print(f"   🔴 NUEVO TEMPORAL (sin frontend): {nuevo_id}")
        print("=" * 60)
        return nuevo_id
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

@app.route('/api/todos-titulos-y-descripciones', methods=['GET'])
def get_todos_titulos_y_descripciones():
    try:
        # Obtener títulos únicos
        query_titulos = """
        SELECT DISTINCT titulo 
        FROM imagenes 
        WHERE activa = TRUE 
          AND titulo IS NOT NULL 
          AND titulo != ''
          AND LENGTH(titulo) > 1
        ORDER BY titulo
        """
        
        # Obtener pares (descripción → título) para búsqueda
        query_descripciones = """
        SELECT DISTINCT 
            descripcion,
            titulo
        FROM imagenes 
        WHERE activa = TRUE 
          AND descripcion IS NOT NULL 
          AND descripcion != '' 
          AND LENGTH(descripcion) > 1
          AND descripcion NOT LIKE '%http%'
          AND descripcion NOT LIKE '%.jpg%'
          AND descripcion NOT LIKE '%.png%'
          AND descripcion NOT LIKE '%.jpeg%'
          AND descripcion NOT LIKE '%.gif%'
          AND descripcion NOT REGEXP '^[0-9]+$'
        ORDER BY descripcion
        """

        from database import Database
        db = Database()
        db.connect()
        cursor = db.connection.cursor(dictionary=True)
        
        # Ejecutar consulta de títulos
        cursor.execute(query_titulos)
        titulos_result = cursor.fetchall()
        
        # Ejecutar consulta de descripciones
        cursor.execute(query_descripciones)
        descripciones_result = cursor.fetchall()
        
        cursor.close()
        db.connection.close()

        # Preparar respuesta
        resultados = {
            'titulos': [],
            'descripciones_titulos': []  # Pares para búsqueda
        }
        
        # Agregar títulos directos
        if titulos_result:
            resultados['titulos'] = [row['titulo'].strip() for row in titulos_result if row['titulo']]
        
        # Agregar pares descripción → título
        if descripciones_result:
            for row in descripciones_result:
                if row['descripcion'] and row['titulo']:
                    resultados['descripciones_titulos'].append({
                        'descripcion': row['descripcion'].strip(),
                        'titulo': row['titulo'].strip()
                    })
        
        # Eliminar duplicados en títulos
        titulos_unicos = []
        titulos_vistos = set()
        for titulo in resultados['titulos']:
            titulo_lower = titulo.lower()
            if titulo_lower not in titulos_vistos:
                titulos_vistos.add(titulo_lower)
                titulos_unicos.append(titulo)
        
        return jsonify({
            'success': True,
            'titulos': titulos_unicos,
            'descripciones_titulos': resultados['descripciones_titulos'],
            'total_titulos': len(titulos_unicos),
            'total_descripciones': len(resultados['descripciones_titulos'])
        })

    except Exception as e:
        print(f"Error en todos-titulos-y-descripciones: {str(e)}")
        
        return jsonify({
            'success': True,
            'titulos': [
                "Lindo M El Indomable",
                "La Vendicion Vol. 2 Summer Edition",
                "Freemolly",
                "HyperPopular"
            ],
            'descripciones_titulos': [],
            'total_titulos': 4,
            'total_descripciones': 0,
            'mensaje': 'Usando datos de respaldo'
        })
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

# Ruta para registrar intento por álbum específico
@app.route('/api/registrar-intento-album', methods=['POST'])
def registrar_intento_album():
    try:
        data = request.get_json()
        user_id = get_or_create_user_id()
        
        fecha_album = data.get('fecha_album')
        numero_album = data.get('numero_album')
        acierto = data.get('acierto', False)
        intentos_usuario = data.get('intentos', 1)
        
        if not fecha_album or not numero_album:
            return jsonify({
                'success': False,
                'message': 'Se requiere fecha_album y numero_album'
            }), 400
        
        # Calcular intentos a guardar
        if acierto:
            intentos_guardar = min(int(intentos_usuario), 5)  # 1-5 si acertó
        else:
            intentos_guardar = 6  # 6 si falló
        
        from database import Database
        db = Database()
        db.connect()
        cursor = db.connection.cursor()
        
        # Verificar si es la PRIMERA vez que juega este álbum
        cursor.execute('''
            SELECT veces_jugado 
            FROM intentos_usuario_album 
            WHERE user_id_hash = MD5(%s) 
              AND fecha_album = %s 
              AND numero_album = %s
        ''', (user_id, fecha_album, int(numero_album)))
        
        resultado = cursor.fetchone()
        
        es_primera_vez = False
        veces_jugado = 1
        
        if resultado:
            # Ya ha jugado antes - NO actualizar estadísticas
            veces_jugado = resultado[0] + 1
            es_primera_vez = False
            
            cursor.execute('''
                UPDATE intentos_usuario_album 
                SET veces_jugado = veces_jugado + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id_hash = MD5(%s) 
                  AND fecha_album = %s 
                  AND numero_album = %s
            ''', (user_id, fecha_album, numero_album))
            
        else:
            # Es primera vez - SÍ actualizar estadísticas
            veces_jugado = 1
            es_primera_vez = True
            
            # Insertar registro del usuario
            cursor.execute('''
                INSERT INTO intentos_usuario_album 
                (user_id_hash, fecha_album, numero_album, acierto, intentos_necesarios, veces_jugado)
                VALUES (MD5(%s), %s, %s, %s, %s, 1)
            ''', (user_id, fecha_album, numero_album, acierto, intentos_guardar))
            
            # Actualizar estadísticas del álbum SOLO si es acierto
            if acierto:
                # Construir la consulta dinámicamente según el intento
                columna_intento = f"aciertos_intento_{intentos_guardar}"
                
                cursor.execute(f'''
                    INSERT INTO estadisticas_album 
                    (fecha_album, numero_album, total_jugadores, aciertos, fallos, total_intentos, {columna_intento})
                    VALUES (%s, %s, 1, 1, 0, %s, 1)
                    ON DUPLICATE KEY UPDATE
                        total_jugadores = total_jugadores + 1,
                        aciertos = aciertos + 1,
                        {columna_intento} = {columna_intento} + 1,
                        total_intentos = total_intentos + %s
                ''', (fecha_album, numero_album, intentos_guardar, intentos_guardar))
            else:
                # Si es fallo
                cursor.execute('''
                    INSERT INTO estadisticas_album 
                    (fecha_album, numero_album, total_jugadores, aciertos, fallos, total_intentos)
                    VALUES (%s, %s, 1, 0, 1, %s)
                    ON DUPLICATE KEY UPDATE
                        total_jugadores = total_jugadores + 1,
                        fallos = fallos + 1,
                        total_intentos = total_intentos + %s
                ''', (fecha_album, numero_album, intentos_guardar, intentos_guardar))
        
        # Obtener estadísticas COMPLETAS del álbum
        cursor.execute('''
            SELECT 
                total_jugadores,
                aciertos,
                fallos,
                total_intentos,
                aciertos_intento_1,
                aciertos_intento_2,
                aciertos_intento_3,
                aciertos_intento_4,
                aciertos_intento_5
            FROM estadisticas_album 
            WHERE fecha_album = %s AND numero_album = %s
        ''', (fecha_album, int(numero_album)))
        
        stats = cursor.fetchone()
        
        # Calcular porcentaje y distribuciones
        porcentaje_acierto = 0
        if stats and stats[0] and stats[0] > 0:
            porcentaje_acierto = (stats[1] / stats[0]) * 100 if stats[1] else 0
        
        # Crear objeto con estadísticas detalladas
        estadisticas_detalladas = {
            'total_jugadores': stats[0] if stats and stats[0] else 0,
            'aciertos': stats[1] if stats and stats[1] else 0,
            'fallos': stats[2] if stats and stats[2] else 0,
            'total_intentos': stats[3] if stats and stats[3] else 0,
            'porcentaje_acierto': round(porcentaje_acierto, 1),
            'distribucion_aciertos': {
                'intento_1': stats[4] if stats and len(stats) > 4 and stats[4] else 0,
                'intento_2': stats[5] if stats and len(stats) > 5 and stats[5] else 0,
                'intento_3': stats[6] if stats and len(stats) > 6 and stats[6] else 0,
                'intento_4': stats[7] if stats and len(stats) > 7 and stats[7] else 0,
                'intento_5': stats[8] if stats and len(stats) > 8 and stats[8] else 0
            }
        }
        
        db.connection.commit()
        cursor.close()
        db.connection.close()
        
        return jsonify({
            'success': True,
            'message': 'Intento registrado',
            'es_primera_vez': es_primera_vez,
            'veces_jugado': veces_jugado,
            'estadisticas': estadisticas_detalladas
        })
        
    except Exception as e:
        print(f"Error registrar intento álbum: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
        
# Ruta para obtener estadísticas de UN álbum específico
@app.route('/api/estadisticas-album', methods=['GET'])
def get_estadisticas_album():
    try:
        fecha_album = request.args.get('fecha')
        numero_album = request.args.get('numero')
        
        if not fecha_album or not numero_album:
            return jsonify({
                'success': False,
                'message': 'Se requiere fecha y número del álbum'
            }), 400
        
        from database import Database
        db = Database()
        db.connect()
        cursor = db.connection.cursor(dictionary=True)
        
        # Obtener estadísticas completas
        cursor.execute('''
            SELECT 
                total_jugadores,
                aciertos,
                fallos,
                total_intentos,
                COALESCE(aciertos_intento_1, 0) as aciertos_intento_1,
                COALESCE(aciertos_intento_2, 0) as aciertos_intento_2,
                COALESCE(aciertos_intento_3, 0) as aciertos_intento_3,
                COALESCE(aciertos_intento_4, 0) as aciertos_intento_4,
                COALESCE(aciertos_intento_5, 0) as aciertos_intento_5
            FROM estadisticas_album 
            WHERE fecha_album = %s AND numero_album = %s
        ''', (fecha_album, int(numero_album)))
        
        stats = cursor.fetchone()
        
        if not stats:
            stats = {
                'total_jugadores': 0,
                'aciertos': 0,
                'fallos': 0,
                'total_intentos': 0,
                'aciertos_intento_1': 0,
                'aciertos_intento_2': 0,
                'aciertos_intento_3': 0,
                'aciertos_intento_4': 0,
                'aciertos_intento_5': 0
            }
        
        # Calcular porcentaje
        porcentaje_acierto = 0
        if stats['total_jugadores'] > 0:
            porcentaje_acierto = (stats['aciertos'] / stats['total_jugadores']) * 100
        
        cursor.close()
        db.connection.close()
        
        return jsonify({
            'success': True,
            'fecha_album': fecha_album,
            'numero_album': numero_album,
            'estadisticas': {
                'total_jugadores': stats['total_jugadores'],
                'aciertos': stats['aciertos'],
                'fallos': stats['fallos'],
                'total_intentos': stats['total_intentos'],
                'porcentaje_acierto': round(porcentaje_acierto, 1),
                'distribucion_aciertos': {
                    'intento_1': stats['aciertos_intento_1'],
                    'intento_2': stats['aciertos_intento_2'],
                    'intento_3': stats['aciertos_intento_3'],
                    'intento_4': stats['aciertos_intento_4'],
                    'intento_5': stats['aciertos_intento_5']
                }
            }
        })
        
    except Exception as e:
        print(f"Error estadísticas álbum: {str(e)}")
        return jsonify({
            'success': True,
            'fecha_album': fecha_album,
            'numero_album': numero_album,
            'estadisticas': {
                'total_jugadores': 0,
                'aciertos': 0,
                'fallos': 0,
                'total_intentos': 0,
                'porcentaje_acierto': 0,
                'distribucion_aciertos': {
                    'intento_1': 0,
                    'intento_2': 0,
                    'intento_3': 0,
                    'intento_4': 0,
                    'intento_5': 0
                }
            }
        })

# Ruta para ver si el usuario YA jugó este álbum específico
@app.route('/api/mi-intento-album', methods=['GET'])
def get_mi_intento_album():
    try:
        user_id = get_or_create_user_id()
        fecha_album = request.args.get('fecha')
        numero_album = request.args.get('numero')
        
        if not fecha_album or not numero_album:
            return jsonify({
                'success': False,
                'message': 'Se requiere fecha y número del álbum'
            }), 400
        
        from database import Database
        db = Database()
        db.connect()
        cursor = db.connection.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT 
                acierto,
                intentos_necesarios,
                veces_jugado,
                es_primera_vez,
                created_at,
                updated_at
            FROM intentos_usuario_album 
            WHERE user_id_hash = MD5(%s) 
              AND fecha_album = %s 
              AND numero_album = %s
        ''', (user_id, fecha_album, int(numero_album)))
        
        mi_intento = cursor.fetchone()
        
        cursor.close()
        db.connection.close()
        
        if mi_intento:
            # Formatear intentos para mostrar
            if mi_intento['acierto']:
                texto_intentos = f"en {mi_intento['intentos_necesarios']} intento{'s' if mi_intento['intentos_necesarios'] > 1 else ''}"
            else:
                texto_intentos = "no acertaste"
            
            return jsonify({
                'success': True,
                'ya_jugo': True,
                'veces_jugado': mi_intento['veces_jugado'],
                'es_primera_vez': mi_intento['es_primera_vez'],
                'resultado': {
                    'acierto': mi_intento['acierto'],
                    'intentos': mi_intento['intentos_necesarios'],
                    'texto_intentos': texto_intentos,
                    'primera_vez': mi_intento['created_at'].isoformat() if mi_intento['created_at'] else None,
                    'ultima_vez': mi_intento['updated_at'].isoformat() if mi_intento['updated_at'] else None
                }
            })
        else:
            return jsonify({
                'success': True,
                'ya_jugo': False,
                'veces_jugado': 0,
                'es_primera_vez': True,
                'resultado': None
            })
            
    except Exception as e:
        print(f"Error mi intento álbum: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
        
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)