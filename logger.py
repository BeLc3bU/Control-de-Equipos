"""
Sistema de logging centralizado para toda la aplicación.
"""
import logging
from config import Config

def setup_logger():
    """Configura el logger de la aplicación."""
    logger = logging.getLogger('ControlEquipos')
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    # Handler para archivo
    file_handler = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # Formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()
