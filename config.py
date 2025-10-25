"""
Configuración centralizada de la aplicación.
Crea un archivo .env con tus credenciales reales.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # --- General App Info ---
    COMPANY_NAME = "AvionicaTaller"
    APP_NAME = "ControlEquipos"

    # --- Paths ---
    DB_NAME = "control_equipos.db"
    DOCS_BASE_DIR = "docs"
    BACKUP_DIR = "backups"
    
    # --- Logging ---
    LOG_FILE = "control_equipos.log"
    LOG_LEVEL = "INFO"

    # --- SMTP (Opcional, cargado desde .env) ---
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.example.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', 'user@example.com')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT', 'recipient@example.com')
    
    @classmethod
    def is_smtp_configured(cls):
        """Verifica si SMTP está configurado correctamente."""
        return (cls.SMTP_SERVER != 'smtp.example.com' and 
                cls.SMTP_PASSWORD != '' and
                cls.SMTP_USER != 'user@example.com')
