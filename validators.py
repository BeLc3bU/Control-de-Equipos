"""
Validadores para campos críticos de la aplicación.
"""
import re
from datetime import datetime
from typing import Tuple

class Validator:
    """Validadores para diferentes tipos de datos."""
    
    @staticmethod
    def validate_pn(pn: str) -> Tuple[bool, str]:
        """
        Valida el formato del Part Number.
        Acepta alfanuméricos, guiones y espacios, longitud entre 5 y 30.
        """
        if not pn or not pn.strip():
            return False, "El PN no puede estar vacío"
        
        pn = pn.strip()
        
        if len(pn) < 3:
            return False, "El PN debe tener al menos 3 caracteres"
        
        if len(pn) > 30:
            return False, "El PN no puede exceder 30 caracteres"
        
        # Solo alfanuméricos, guiones y espacios
        if not re.match(r'^[A-Za-z0-9\-\s\.,/_]+$', pn):
            return False, "El PN solo puede contener letras, números, espacios y los símbolos: - . , / _"
        
        return True, ""
    
    @staticmethod
    def validate_sn(sn: str) -> Tuple[bool, str]:
        """
        Valida el formato del Serial Number.
        Acepta alfanuméricos, guiones, longitud entre 3 y 30.
        """
        if not sn or not sn.strip():
            return False, "El SN no puede estar vacío"
        
        sn = sn.strip()
        
        if len(sn) < 3:
            return False, "El SN debe tener al menos 3 caracteres"
        
        if len(sn) > 30:
            return False, "El SN no puede exceder 30 caracteres"
        
        if not re.match(r'^[A-Za-z0-9\-\.,/_]+$', sn):
            return False, "El SN solo puede contener letras, números y los símbolos: - . , / _"
        
        return True, ""
    
    @staticmethod
    def validate_ot(ot: str) -> Tuple[bool, str]:
        """
        Valida el formato del Número de Orden Técnica.
        Debe ser obligatorio y tener un formato específico.
        """
        if not ot or not ot.strip():
            return False, "El Nº OT es un campo obligatorio"
        
        ot = ot.strip()
        
        if len(ot) < 3:
            return False, "El Nº OT debe tener al menos 3 caracteres"
        
        if len(ot) > 30:
            return False, "El Nº OT no puede exceder 30 caracteres"
        
        # Acepta alfanuméricos, guiones, barras y espacios
        if not re.match(r'^[A-Za-z0-9\-\s/]+$', ot):
            return False, "El Nº OT solo puede contener letras, números, guiones, barras y espacios"
        
        return True, ""
    
    @staticmethod
    def validate_hours(hours_str: str) -> Tuple[bool, str]:
        """Valida que las horas sean un número positivo."""
        if not hours_str or not hours_str.strip():
            return True, ""  # Las horas son opcionales
        
        try:
            hours = float(hours_str.strip())
            if hours < 0:
                return False, "Las horas no pueden ser negativas"
            if hours > 10000:
                return False, "Las horas parecen excesivas (máximo 10000)"
            return True, ""
        except ValueError:
            return False, "Las horas deben ser un número válido"
    
    @staticmethod
    def validate_date(date_str: str, date_format: str = "%Y-%m-%d %H:%M") -> Tuple[bool, str]:
        """Valida que una fecha tenga el formato correcto."""
        if not date_str or not date_str.strip():
            return True, ""  # Las fechas pueden ser opcionales
        
        try:
            datetime.strptime(date_str.strip(), date_format)
            return True, ""
        except ValueError:
            return False, f"La fecha debe tener el formato: {date_format}"
    
    @staticmethod
    def validate_file_size(file_path: str, max_mb: int = 50) -> Tuple[bool, str]:
        """Valida que el archivo no exceda un tamaño máximo."""
        try:
            import os
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > max_mb:
                return False, f"El archivo excede el tamaño máximo de {max_mb}MB (actual: {size_mb:.1f}MB)"
            return True, ""
        except Exception as e:
            return False, f"Error al verificar tamaño del archivo: {e}"
    
    @staticmethod
    def validate_duplicate_ot(db_session, ot: str, exclude_id: int = None) -> Tuple[bool, str]:
        """Valida que el número de OT no esté duplicado."""
        if not ot or not ot.strip():
            return True, ""
        
        query = "SELECT id FROM equipos WHERE numero_ot = ?"
        params = (ot.strip(),)
        
        if exclude_id:
            query += " AND id != ?"
            params = (ot.strip(), exclude_id)
        
        existing = db_session.fetch_query(query, params, one=True)
        if existing:
            return False, f"La Orden Técnica '{ot}' ya existe en el sistema"
        
        return True, ""
