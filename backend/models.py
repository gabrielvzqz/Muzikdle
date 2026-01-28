from database import Database
from datetime import datetime, date

class ImagenModel:
    def __init__(self):
        self.db = Database()
    
    def get_imagenes_del_dia(self):
        """Obtiene las 5 imágenes programadas para hoy"""
        hoy = date.today().isoformat()
        
        query = """
        SELECT * FROM imagenes 
        WHERE fecha_programada = %s AND activa = TRUE
        ORDER BY orden_dia
        """
        
        result = self.db.execute_query(query, (hoy,), fetch=True)
        return result if result else []
    
    def get_total_imagenes_hoy(self):
        """Cuántas imágenes hay para hoy"""
        hoy = date.today().isoformat()
        
        query = """
        SELECT COUNT(*) as total FROM imagenes 
        WHERE fecha_programada = %s AND activa = TRUE
        """
        
        result = self.db.execute_query(query, (hoy,), fetch=True)
        return result[0]['total'] if result else 0
    
    def get_imagen_aleatoria(self):
        """Obtiene una imagen aleatoria si no hay programada para hoy"""
        query = """
        SELECT * FROM imagenes 
        WHERE activa = TRUE 
        ORDER BY RAND() 
        LIMIT 1
        """
        
        result = self.db.execute_query(query, fetch=True)
        return result[0] if result else None
    
    def registrar_visualizacion(self, imagen_id):
        """Registra cuándo se mostró una imagen"""
        query = """
        INSERT INTO historial_imagenes (imagen_id, fecha_mostrada)
        VALUES (%s, %s)
        """
        
        hoy = date.today().isoformat()
        self.db.execute_query(query, (imagen_id, hoy))
    
    def subir_imagen(self, nombre_archivo, ruta_archivo, titulo, descripcion, fecha_programada=None):
        """Sube una nueva imagen a la base de datos"""
        query = """
        INSERT INTO imagenes (nombre_archivo, ruta_archivo, titulo, descripcion, fecha_programada)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        params = (nombre_archivo, ruta_archivo, titulo, descripcion, fecha_programada)
        return self.db.execute_query(query, params)
    
    def get_todas_imagenes(self):
        """Obtiene todas las imágenes"""
        query = "SELECT * FROM imagenes WHERE activa = TRUE ORDER BY fecha_programada DESC"
        return self.db.execute_query(query, fetch=True)
    
    def programar_imagen(self, imagen_id, fecha):
        """Programa una imagen para una fecha específica"""
        query = """
        UPDATE imagenes 
        SET fecha_programada = %s 
        WHERE id = %s
        """
        
        return self.db.execute_query(query, (fecha, imagen_id))