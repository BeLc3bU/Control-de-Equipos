"""
Sistema de logging centralizado para toda la aplicación.
"""
import logging
import os
from datetime import datetime
from config import Config

def setup_logger():
    """Configura el logger de la aplicación."""
    logger = logging.getLogger('ControlEquipos')
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    # Evitar duplicar handlers si ya existen
    if logger.handlers:
        return logger
    
    # Crear directorio de logs si no existe
    log_dir = os.path.dirname(Config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Handler para archivo con rotación
    file_handler = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # Formato mejorado
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log de inicio de sesión
    logger.info(f"Iniciando sesión de logging - PID: {os.getpid()}")
    
    return logger

def log_performance(func):
    """Decorator para medir el rendimiento de funciones."""
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        result = func(*args, **kwargs)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.debug(f"Función {func.__name__} ejecutada en {duration:.3f} segundos")
        return result
    return wrapper

logger = setup_logger()
