"""
Utilidades mejoradas para manejo de archivos.
"""
import os
import shutil
import subprocess
import sys
from datetime import datetime
import zipfile
from logger import logger
from validators import Validator
from ui_utils import show_error, show_warning, show_info

def copy_document(source_path: str, base_target_dir: str) -> str:
    """
    Copia un documento a la carpeta organizada con validaciones mejoradas.
    
    Args:
        source_path: Ruta del archivo origen
        base_target_dir: Ruta de la carpeta de destino (ej: 'docs/Equipo/SN/Arising00')
    
    Returns:
        Ruta del archivo copiado o cadena vacía si falla
    """
    if not source_path:
        return ""
    
    try:
        # Validar que el archivo existe
        if not os.path.exists(source_path):
            logger.error(f"Archivo no encontrado: {source_path}")
            show_error("Error", "El archivo seleccionado no existe")
            return ""
        
        # Validar tamaño del archivo
        valid, msg = Validator.validate_file_size(source_path)
        if not valid:
            logger.warning(f"Archivo demasiado grande: {source_path} - {msg}")
            show_warning("Archivo Grande", msg)
            return ""
        
        filename = os.path.basename(source_path)
        
        # Crear directorio si no existe
        os.makedirs(base_target_dir, exist_ok=True)
        
        target_path = os.path.join(base_target_dir, filename)
        
        # Si el archivo ya existe, agregar sufijo numérico
        if os.path.exists(target_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(target_path):
                new_filename = f"{base}_{counter}{ext}"
                target_path = os.path.join(base_target_dir, new_filename)
                counter += 1
            logger.info(f"Archivo renombrado para evitar duplicado: {target_path}")
        
        # Copiar archivo
        shutil.copy2(source_path, target_path)
        logger.info(f"Archivo copiado exitosamente: {source_path} -> {target_path}")
        
        return target_path
        
    except PermissionError as e:
        logger.error(f"Error de permisos al copiar archivo: {e}")
        show_error("Error de Permisos", "No tienes permisos para copiar este archivo")
        return ""
    except OSError as e:
        logger.error(f"Error de sistema al copiar archivo: {e}")
        show_error("Error", f"No se pudo copiar el archivo: {e}")
        return ""
    except Exception as e:
        logger.exception(f"Error inesperado al copiar archivo: {e}")
        show_error("Error Inesperado", f"Error al copiar el archivo: {e}")
        return ""


def open_file(path: str):
    """Abre un archivo con validaciones mejoradas."""
    if not path:
        logger.warning("Intento de abrir archivo con ruta vacía")
        show_warning("Sin archivo", "No hay ningún archivo seleccionado")
        return
    
    if not os.path.exists(path):
        logger.warning(f"Intento de abrir archivo inexistente: {path}")
        show_warning("Archivo no encontrado", f"El archivo no existe:\n{path}")
        return
    
    try:
        logger.info(f"Abriendo archivo: {path}")
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        logger.error(f"Error al abrir archivo {path}: {e}")
        show_error("Error al abrir", f"No se pudo abrir el archivo:\n{e}")

def create_database_backup(db_path: str, backup_dir: str = "backups") -> str:
    """
    Crea una copia de seguridad comprimida de la base de datos en un archivo .zip.

    Args:
        db_path: Ruta al archivo de la base de datos a respaldar.
        backup_dir: Directorio donde se guardarán las copias.

    Returns:
        La ruta al archivo de copia de seguridad creado.
        
    Raises:
        FileNotFoundError: Si el archivo de la base de datos no existe.
        IOError: Si hay problemas al escribir el archivo de backup.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"El archivo de la base de datos no se encontró en: {db_path}")

    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    db_filename = os.path.basename(db_path)
    backup_filename = f"backup_{db_filename.replace('.db', '')}_{timestamp}.zip"
    backup_filepath = os.path.join(backup_dir, backup_filename)

    with zipfile.ZipFile(backup_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, os.path.basename(db_path))
    
    return backup_filepath

def restore_database_from_backup(zip_path: str, db_path: str):
    """
    Restaura la base de datos desde un archivo .zip de copia de seguridad.

    Args:
        zip_path: Ruta al archivo .zip de la copia de seguridad.
        db_path: Ruta al archivo de la base de datos actual que será reemplazado.

    Raises:
        Exception: Si ocurre algún error durante el proceso de restauración.
    """
    db_old_path = f"{db_path}.old"
    
    # 1. Verificar que el backup existe
    if not os.path.exists(zip_path):
        raise FileNotFoundError("El archivo de copia de seguridad no existe.")

    # 2. Renombrar la base de datos actual como medida de seguridad
    if os.path.exists(db_path):
        try:
            os.rename(db_path, db_old_path)
            logger.info(f"Base de datos actual renombrada a {db_old_path}")
        except OSError as e:
            raise IOError(f"No se pudo renombrar la base de datos actual. Asegúrate de que no esté en uso. Error: {e}")

    # 3. Extraer la base de datos del archivo .zip
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Asumimos que el .zip contiene un solo archivo .db
            db_filename_in_zip = [name for name in zf.namelist() if name.endswith('.db')][0]
            zf.extract(db_filename_in_zip, os.path.dirname(db_path))
            logger.info(f"Base de datos restaurada desde {zip_path}")
    except Exception as e:
        # Si la extracción falla, intentar restaurar la BD original
        if os.path.exists(db_old_path):
            os.rename(db_old_path, db_path)
        raise IOError(f"Error al extraer la copia de seguridad: {e}. Se ha intentado restaurar la BD original.")
