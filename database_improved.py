"""
Versión mejorada de la clase Database con mejor manejo de errores.
"""
import sqlite3
from typing import Optional, List, Any
from logger import logger
from ui_utils import show_error

class Database:
    """Clase mejorada para gestionar operaciones con SQLite."""
    
    def __init__(self, db_name: str):
        self.db_name = db_name
        logger.info(f"Inicializando base de datos: {db_name}")
    
    def _get_connection(self):
        """Retorna una conexión a la base de datos."""
        try:
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Error al conectar con la base de datos: {e}")
            raise
    
    def execute_query(self, query: str, params=()) -> Optional[int]:
        """
        Ejecuta una consulta de modificación (INSERT, UPDATE, DELETE).
        Retorna el lastrowid o None si hay error.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                logger.debug(f"Query ejecutada exitosamente: {query[:50]}...")
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.warning(f"Error de integridad en BD: {e}")
            show_error("Error de Duplicado", "Este registro ya existe o viola una restricción única.")
            return None
        except sqlite3.Error as e:
            logger.error(f"Error en execute_query: {e}\nQuery: {query}\nParams: {params}")
            show_error("Error de Base de Datos", f"No se pudo ejecutar la operación.\n\nError: {e}")
            return None
    
    def fetch_query(self, query: str, params=(), one: bool = False) -> Any:
        """
        Ejecuta una consulta de selección (SELECT).
        Retorna una fila (si one=True) o lista de filas.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone() if one else cursor.fetchall()
                logger.debug(f"Fetch ejecutado: {query[:50]}... | Resultados: {len(result) if not one and result else 'one' if one else 0}")
                return result
        except sqlite3.Error as e:
            logger.error(f"Error en fetch_query: {e}\nQuery: {query}\nParams: {params}")
            return None if one else []
    
    def setup(self):
        """Crea las tablas si no existen."""
        query = """
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_equipo TEXT,
            pn TEXT NOT NULL,
            sn TEXT NOT NULL,
            estado_entrada TEXT,
            numero_ot TEXT NOT NULL UNIQUE,
            defect_report TEXT,
            obs_entrada TEXT,
            fecha_entrada TEXT,
            doc_entrada TEXT,
            fotos TEXT,
            estado_salida TEXT,
            log_trabajo TEXT,
            obs_salida TEXT,
            cerrado INTEGER DEFAULT 0,
            fecha_cierre TEXT,
            contenedor INTEGER,
            destino TEXT,
            horas_trabajo REAL,
            obs_cierre TEXT,
            certificado_cat TEXT,
            defect_report_final TEXT,
            fecha_salida TEXT,
            inventario INTEGER DEFAULT 1,
            doc_folder_path TEXT
        );
        """
        try:
            self.execute_query(query)
            logger.info("Estructura de base de datos verificada/creada")
        except Exception as e:
            logger.critical(f"Error crítico al crear estructura de BD: {e}")
            raise
