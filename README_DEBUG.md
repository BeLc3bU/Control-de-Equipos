# Control de Equipos - Sistema de Gestión de Banco de Pruebas

## 🚀 Descripción

Sistema de gestión completo para el control de equipos aviónicos en un banco de pruebas. Permite registrar, gestionar y hacer seguimiento del flujo de trabajo de equipos desde su entrada hasta su salida del inventario.

## ✨ Características Principales

- **Registro de Equipos**: Entrada de nuevos equipos con validación completa
- **Gestión de Trabajo**: Seguimiento de intervenciones y estados
- **Documentación**: Gestión de documentos y certificados
- **Reportes**: Generación de informes PDF y exportación a Excel
- **Gráficos de Productividad**: Análisis visual del rendimiento del taller
- **Notificaciones**: Sistema de correo electrónico integrado
- **Base de Datos**: SQLite con índices optimizados para rendimiento

## 🔧 Mejoras Implementadas (Debug 2025-10-20)

### ✅ Correcciones de Errores
- **Codificación de emails**: Corregido error de codificación UTF-8 en notificaciones
- **Base de datos**: Separación de statements SQL para evitar errores de ejecución
- **Validaciones**: Mejoradas con validación de fechas y duplicados
- **Logging**: Sistema mejorado con información de función y línea

### 🚀 Nuevas Funcionalidades
- **Paginación**: Sistema de paginación para consultas grandes
- **Índices de BD**: Optimización de rendimiento con índices estratégicos
- **Validación de duplicados**: Prevención de OTs duplicadas
- **Decorador de rendimiento**: Medición automática de tiempo de ejecución
- **Archivo de configuración**: Ejemplo de configuración con variables de entorno

### 📦 Dependencias Actualizadas
- `matplotlib>=3.5.0` - Para gráficos avanzados
- `seaborn>=0.11.0` - Para estilos de gráficos profesionales
- Todas las dependencias existentes mantenidas

## 🛠️ Instalación

### Requisitos Previos
- Python 3.8 o superior
- PyQt6

### Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### Configuración
1. Copia `env.example` a `.env`
2. Configura las variables de entorno según tus necesidades
3. Ejecuta el sistema

## 🚀 Uso

### Ejecución Principal
```bash
py main_pyqt.py
```

### Pruebas del Sistema
```bash
py test_system.py
```

## 📁 Estructura del Proyecto

```
Control de Equipos/
├── main_pyqt.py              # Aplicación principal PyQt6
├── pyqt_windows.py           # Ventanas y diálogos
├── database_improved.py      # Gestión de base de datos
├── validators.py             # Validaciones de datos
├── file_utils.py             # Utilidades de archivos
├── email_utils.py            # Sistema de correo
├── ui_utils.py               # Utilidades de interfaz
├── config.py                 # Configuración centralizada
├── logger.py                 # Sistema de logging
├── test_system.py            # Pruebas del sistema
├── requirements.txt          # Dependencias
├── env.example               # Ejemplo de configuración
├── icons/                    # Iconos de la aplicación
├── docs/                     # Documentos de equipos
└── control_equipos.db        # Base de datos SQLite
```

## 🔍 Flujo de Trabajo

1. **Entrada**: Registro de nuevo equipo con documentos
2. **Trabajo**: Seguimiento de intervenciones y estados
3. **Cierre**: Documentación final y certificados
4. **Salida**: Marcado como fuera de inventario

## 📊 Características Avanzadas

### Gráficos de Productividad
- Rendimiento del taller por mes
- Distribución de resultados
- Tiempo de ciclo (turnaround)
- Complejidad de reparaciones

### Sistema de Validaciones
- Part Numbers y Serial Numbers
- Números de Orden Técnica
- Horas de trabajo
- Fechas y formatos
- Tamaño de archivos

### Optimizaciones de Rendimiento
- Índices de base de datos
- Paginación de consultas
- Multithreading para operaciones pesadas
- Logging de rendimiento

## 🐛 Debug y Mantenimiento

### Logs
Los logs se guardan en `control_equipos.log` con información detallada de:
- Operaciones de base de datos
- Errores y excepciones
- Rendimiento de funciones
- Actividad del usuario

### Pruebas
El archivo `test_system.py` incluye pruebas para:
- Importaciones de módulos
- Operaciones de base de datos
- Validaciones
- Dependencias opcionales

## 📝 Notas de Desarrollo

- **PyQt6**: Interfaz moderna y responsive
- **SQLite**: Base de datos ligera y confiable
- **Multithreading**: Operaciones no bloqueantes
- **Validación robusta**: Prevención de errores de datos
- **Logging completo**: Trazabilidad de operaciones

## 🔄 Actualizaciones Futuras

- [ ] Sistema de respaldos automáticos
- [ ] Integración con APIs externas
- [ ] Dashboard web complementario
- [ ] Sistema de usuarios y permisos
- [ ] Notificaciones push

---

**Desarrollado para gestión eficiente de equipos aviónicos en banco de pruebas**
