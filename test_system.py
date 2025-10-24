#!/usr/bin/env python3
"""
Script de pruebas para verificar el funcionamiento del sistema Control de Equipos.
"""
import sys
import os
import traceback

def test_imports():
    """Prueba que todas las importaciones funcionen correctamente."""
    print("🔍 Probando importaciones...")
    
    try:
        from config import Config
        print("✅ Config importado correctamente")
    except Exception as e:
        print(f"❌ Error importando Config: {e}")
        return False
    
    try:
        from logger import logger
        print("✅ Logger importado correctamente")
    except Exception as e:
        print(f"❌ Error importando Logger: {e}")
        return False
    
    try:
        from database_improved import Database
        print("✅ Database importado correctamente")
    except Exception as e:
        print(f"❌ Error importando Database: {e}")
        return False
    
    try:
        from validators import Validator
        print("✅ Validator importado correctamente")
    except Exception as e:
        print(f"❌ Error importando Validator: {e}")
        return False
    
    try:
        from file_utils import copy_document, open_file
        print("✅ File utils importado correctamente")
    except Exception as e:
        print(f"❌ Error importando File utils: {e}")
        return False
    
    try:
        from email_utils import send_email_notification
        print("✅ Email utils importado correctamente")
    except Exception as e:
        print(f"❌ Error importando Email utils: {e}")
        return False
    
    try:
        from ui_utils import show_error, show_warning, show_info
        print("✅ UI utils importado correctamente")
    except Exception as e:
        print(f"❌ Error importando UI utils: {e}")
        return False
    
    return True

def test_database():
    """Prueba la conexión y operaciones básicas de la base de datos."""
    print("\n🔍 Probando base de datos...")
    
    try:
        from database_improved import Database
        from config import Config
        
        # Crear una base de datos de prueba
        test_db = Database("test_control_equipos.db")
        test_db.setup()
        print("✅ Base de datos de prueba creada")
        
        # Probar inserción
        query = "INSERT INTO equipos (nombre_equipo, pn, sn, numero_ot) VALUES (?, ?, ?, ?)"
        result = test_db.execute_query(query, ("Test Equipo", "TEST-PN", "TEST-SN", "TEST-OT-001"))
        if result:
            print("✅ Inserción de prueba exitosa")
        else:
            print("⚠️ Inserción falló (posible duplicado), continuando con pruebas")
        
        # Probar consulta
        records = test_db.fetch_query("SELECT * FROM equipos WHERE numero_ot = ?", ("TEST-OT-001",))
        if records:
            print("✅ Consulta de prueba exitosa")
        else:
            print("❌ Error en consulta de prueba")
            return False
        
        # Limpiar base de datos de prueba
        try:
            # Cerrar todas las conexiones antes de eliminar
            import gc
            gc.collect()
            os.remove("test_control_equipos.db")
            print("✅ Base de datos de prueba eliminada")
        except PermissionError:
            print("⚠️ No se pudo eliminar la BD de prueba (está en uso), pero las pruebas pasaron")
        except Exception as e:
            print(f"⚠️ Error eliminando BD de prueba: {e}, pero las pruebas pasaron")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en pruebas de base de datos: {e}")
        traceback.print_exc()
        return False

def test_validators():
    """Prueba los validadores."""
    print("\n🔍 Probando validadores...")
    
    try:
        from validators import Validator
        
        # Probar validación de PN
        valid, msg = Validator.validate_pn("TEST-PN-123")
        if valid:
            print("✅ Validación de PN exitosa")
        else:
            print(f"❌ Error en validación de PN: {msg}")
            return False
        
        # Probar validación de SN
        valid, msg = Validator.validate_sn("SN123456")
        if valid:
            print("✅ Validación de SN exitosa")
        else:
            print(f"❌ Error en validación de SN: {msg}")
            return False
        
        # Probar validación de OT
        valid, msg = Validator.validate_ot("OT-2024-001")
        if valid:
            print("✅ Validación de OT exitosa")
        else:
            print(f"❌ Error en validación de OT: {msg}")
            return False
        
        # Probar validación de horas
        valid, msg = Validator.validate_hours("8.5")
        if valid:
            print("✅ Validación de horas exitosa")
        else:
            print(f"❌ Error en validación de horas: {msg}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error en pruebas de validadores: {e}")
        traceback.print_exc()
        return False

def test_pyqt_imports():
    """Prueba las importaciones de PyQt6."""
    print("\n🔍 Probando importaciones de PyQt6...")
    
    try:
        from PyQt6.QtWidgets import QApplication, QMainWindow
        print("✅ PyQt6.QtWidgets importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando PyQt6.QtWidgets: {e}")
        return False
    
    try:
        from PyQt6.QtCore import Qt, QSettings
        print("✅ PyQt6.QtCore importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando PyQt6.QtCore: {e}")
        return False
    
    try:
        from PyQt6.QtGui import QIcon, QColor
        print("✅ PyQt6.QtGui importado correctamente")
    except ImportError as e:
        print(f"❌ Error importando PyQt6.QtGui: {e}")
        return False
    
    # Probar que se puede crear una aplicación (sin mostrarla)
    try:
        app = QApplication([])
        app.quit()
        print("✅ QApplication creada correctamente")
    except Exception as e:
        print(f"❌ Error creando QApplication: {e}")
        return False
    
    return True

def test_optional_dependencies():
    """Prueba las dependencias opcionales."""
    print("\n🔍 Probando dependencias opcionales...")
    
    # Probar pandas
    try:
        import pandas as pd
        print("✅ Pandas disponible")
    except ImportError:
        print("⚠️ Pandas no disponible (opcional)")
    
    # Probar matplotlib
    try:
        import matplotlib.pyplot as plt
        print("✅ Matplotlib disponible")
    except ImportError:
        print("⚠️ Matplotlib no disponible (opcional)")
    
    # Probar seaborn
    try:
        import seaborn as sns
        print("✅ Seaborn disponible")
    except ImportError:
        print("⚠️ Seaborn no disponible (opcional)")
    
    # Probar reportlab
    try:
        from reportlab.platypus import SimpleDocTemplate
        print("✅ ReportLab disponible")
    except ImportError:
        print("⚠️ ReportLab no disponible (opcional)")
    
    return True

def main():
    """Función principal de pruebas."""
    print("🚀 Iniciando pruebas del sistema Control de Equipos")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Ejecutar todas las pruebas
    tests = [
        test_imports,
        test_database,
        test_validators,
        test_pyqt_imports,
        test_optional_dependencies
    ]
    
    for test in tests:
        try:
            if not test():
                all_tests_passed = False
        except Exception as e:
            print(f"❌ Error inesperado en {test.__name__}: {e}")
            all_tests_passed = False
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("✅ El sistema está listo para usar")
    else:
        print("❌ Algunas pruebas fallaron")
        print("⚠️ Revisa los errores anteriores")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
