"""
Utilidades mejoradas para manejo de archivos.
"""
import os
import shutil
import subprocess
import sys
from typing import Optional
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
