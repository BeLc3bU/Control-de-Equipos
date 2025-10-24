"""
Versión mejorada de la clase Database con mejor manejo de errores y paginación.
"""
import sqlite3
from typing import Optional, List, Any, Dict
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
            # Habilitar foreign keys para integridad referencial
            conn.execute("PRAGMA foreign_keys = ON")
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
    
    def fetch_query_paginated(self, query: str, params=(), page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        Ejecuta una consulta con paginación.
        Retorna un diccionario con los datos y metadatos de paginación.
        """
        try:
            # Contar total de registros
            count_query = f"SELECT COUNT(*) FROM ({query})"
            total_count = self.fetch_query(count_query, params, one=True)[0]
            
            # Calcular offset
            offset = (page - 1) * page_size
            
            # Agregar LIMIT y OFFSET a la consulta
            paginated_query = f"{query} LIMIT {page_size} OFFSET {offset}"
            records = self.fetch_query(paginated_query, params)
            
            # Calcular metadatos de paginación
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1
            
            return {
                'records': records,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev
            }
        except sqlite3.Error as e:
            logger.error(f"Error en fetch_query_paginated: {e}")
            return {
                'records': [],
                'total_count': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0,
                'has_next': False,
                'has_prev': False
            }
    
    def setup(self):
        """Crea las tablas si no existen."""
        # Crear tabla principal
        table_query = """
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
            vale_devolucion TEXT,
            fecha_salida TEXT,
            inventario INTEGER DEFAULT 1,
            doc_folder_path TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Crear índices por separado
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_equipos_numero_ot ON equipos(numero_ot);",
            "CREATE INDEX IF NOT EXISTS idx_equipos_pn_sn ON equipos(pn, sn);",
            "CREATE INDEX IF NOT EXISTS idx_equipos_inventario ON equipos(inventario);",
            "CREATE INDEX IF NOT EXISTS idx_equipos_fecha_entrada ON equipos(fecha_entrada);",
            "CREATE INDEX IF NOT EXISTS idx_equipos_fecha_cierre ON equipos(fecha_cierre);"
        ]
        
        try:
            # Crear tabla
            self.execute_query(table_query)
            
            # Crear índices
            for index_query in indexes:
                self.execute_query(index_query)
            
            # Migración: Añadir campo vale_devolucion si no existe
            self._migrate_add_vale_devolucion()
            
            logger.info("Estructura de base de datos verificada/creada")
        except Exception as e:
            logger.critical(f"Error crítico al crear estructura de BD: {e}")
            raise
    
    def _migrate_add_vale_devolucion(self):
        """Migración para añadir el campo vale_devolucion a tablas existentes."""
        try:
            # Verificar si el campo ya existe
            cursor = self._get_connection().cursor()
            cursor.execute("PRAGMA table_info(equipos)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'vale_devolucion' not in columns:
                logger.info("Añadiendo campo 'vale_devolucion' a la tabla equipos...")
                self.execute_query("ALTER TABLE equipos ADD COLUMN vale_devolucion TEXT")
                logger.info("Campo 'vale_devolucion' añadido exitosamente")
            else:
                logger.debug("Campo 'vale_devolucion' ya existe")
        except Exception as e:
            logger.warning(f"Error en migración de vale_devolucion: {e}")
            # No lanzar excepción para no romper la aplicación
