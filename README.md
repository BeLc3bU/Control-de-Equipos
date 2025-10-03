# Control de Equipos de Aviónica (Versión PyQt)

Una aplicación de escritorio moderna desarrollada en Python y **PyQt6** para gestionar el flujo de trabajo completo de los equipos que pasan por un banco de pruebas de aviónica, desde la entrada hasta la salida final. Esta versión migra la interfaz de Tkinter a PyQt6, ofreciendo una experiencia de usuario más rica y profesional.


*(Nota: Reemplaza la URL de arriba con una captura de pantalla real de tu aplicación para una mejor presentación).*

---

## 📋 Características Principales

*   **Interfaz Moderna y Fluida:** Desarrollada con PyQt6 para una experiencia de usuario profesional y agradable.
*   **Flujo de Trabajo Completo:** Gestiona el ciclo de vida de un equipo a través de múltiples etapas: **Entrada**, **Trabajo**, **Cierre** y **Salida**.
*   **Registro de Entrada Detallado:** Captura `nombre`, `PN`, `SN`, `estado`, `Nº OT`, `Nº DR`, `observaciones` y documentos adjuntos.
*   **Panel de Gestión Centralizado:** Al hacer doble clic en un equipo, se abre una ventana con pestañas para:
    *   **Pestaña de Trabajo:** Permite actualizar el estado de salida (`Útil`, `Reparable`, `Stamby`, etc.), añadir observaciones, subir múltiples tipos de archivos (`tarjetas`, `cartillas`, `DRs`, `fotos`), registrar un **historial cronológico de intervenciones** y abrir un formulario para **solicitar material** por correo.
    *   **Pestaña de Cierre:** Rellenar un formulario de cierre con `destino`, `horas de trabajo`, etc., y marcar el equipo como "cerrado".
    *   **Notificación por Correo Simplificada:** Abre la aplicación web de Gmail con un borrador de correo listo para enviar, sin necesidad de configurar SMTP.
    *   **Documentación Final:** Subir el `Certificado CAT` (para equipos 'Útiles') o el `DR Final` (para equipos 'Reparables') desde la pestaña de cierre.
    *   **Salida de Inventario:** Marcar el equipo como fuera de inventario, registrando la fecha de salida.
*   **Base de Datos Robusta:** Utiliza **SQLite** con un esquema que permite registrar múltiples ciclos de mantenimiento para un mismo equipo, usando la **Orden Técnica (OT)** como identificador único por ciclo.
*   **Gestión de Archivos Organizada:** Guarda todos los documentos en una estructura de carpetas jerárquica y versionada: `docs/NombreDelEquipo/SN/ArisingXX/`, evitando colisiones de nombres.
*   **Consultas y Reportes Avanzados:**
    *   Filtra la vista principal por estado de inventario (`En Inventario`, `Fuera de Inventario`, `Todos`).
    *   Búsqueda en tiempo real por `OT`, `Nombre`, `PN` o `SN`.
    *   **Coloreado de Filas:** La tabla principal resalta las filas con colores según el estado del equipo para una identificación visual rápida.
    *   Exporta la vista actual de la tabla a un archivo **Excel** (`.xlsx`).
    *   Genera un **informe detallado en PDF** de todos los equipos en inventario, incluyendo su historial de intervenciones.
*   **Validaciones y Alertas:** El sistema avisa al usuario si intenta realizar acciones fuera de orden (ej. dar salida sin la documentación final requerida).
*   **Logging Centralizado:** Registra eventos importantes y errores en un archivo `app.log` para facilitar la depuración.
*   **Mejoras de Calidad de Vida (QoL):**
    *   La aplicación recuerda el tamaño y la posición de la ventana, así como el ancho de las columnas.
    *   Avisa al usuario si intenta cerrar una ventana con cambios sin guardar.
    *   El cursor se posiciona automáticamente en los campos de entrada para un flujo de trabajo más rápido.
    *   Ordenamiento natural en las columnas de la tabla (entiende los números dentro del texto).
---

## 🛠️ Tecnologías Utilizadas

*   **Lenguaje:** Python 3
*   **Interfaz Gráfica (GUI):** PyQt6
*   **Base de Datos:** SQLite3
*   **Exportación a Excel:** Pandas & Openpyxl
*   **Generación de PDF:** ReportLab

---

## 🚀 Cómo Empezar

Sigue estos pasos para poner en marcha la aplicación en tu máquina local.

### 1. Prerrequisitos y Configuración Inicial

Asegúrate de tener **Python 3** instalado en tu sistema. Si no lo tienes, puedes descargarlo desde python.org.

> **Importante:** Durante la instalación en Windows, asegúrate de marcar la casilla que dice **"Add Python to PATH"**.

### 2. Clonar el Repositorio

Abre una terminal y clona este repositorio en tu máquina:

```bash
git clone https://github.com/tu-usuario/control-equipos-pyqt.git
cd control-equipos-pyqt
```
*(Reemplaza `tu-usuario/tu-repositorio` con tu URL real de GitHub)*

### 3. Instalar Dependencias

La aplicación utiliza librerías adicionales para ciertas funcionalidades. Instálalas usando pip:

```bash
# En Windows
py -m pip install pandas openpyxl reportlab

# En macOS / Linux
python3 -m pip install pandas openpyxl reportlab
```

### 4. Ejecutar la Aplicación

Una vez instaladas las dependencias, puedes iniciar el programa con el siguiente comando:

```bash
# En Windows
py control_equipos.py

# En macOS / Linux
python3 control_equipos.py
```

Al ejecutarse por primera vez, la aplicación creará automáticamente el archivo de base de datos `control_equipos.db` y la carpeta `docs/` para los documentos.

---

## 📂 Estructura del Proyecto

```
tu-repositorio/
├── docs/                  # Carpeta generada para almacenar documentos
│   └── PN_SN/
│       ├── entrada/
│       └── salida/
├── control_equipos.py     # Script principal de la aplicación
├── control_equipos.db     # Base de datos SQLite (generada automáticamente)
└── README.md              # Este archivo
```