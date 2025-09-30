# Control de Equipos de Aviónica

Una aplicación de escritorio desarrollada en Python para gestionar el flujo de trabajo completo de los equipos que pasan por un banco de pruebas de aviónica, desde la entrada hasta la salida final.

 
*(Nota: Reemplaza la URL de arriba con una captura de pantalla real de tu aplicación para una mejor presentación)*

---

## 📋 Características Principales
*   **Flujo de Trabajo Completo:** Gestiona el ciclo de vida de un equipo a través de 4 etapas: **Entrada**, **Trabajo**, **Cierre** y **Salida**.
*   **Registro de Entrada Detallado:** Captura `nombre`, `PN`, `SN`, `estado`, `Nº OT`, `Nº DR`, `observaciones` y el documento `SL2000`.
*   **Panel de Gestión Centralizado:** Al hacer doble clic en un equipo, se abre una ventana con pestañas para:
    *   **Trabajo y Fotos:** Actualizar el estado de salida (`Útil`/`Reparable`), añadir observaciones y subir múltiples fotos del trabajo realizado.
    *   **Cierre de Equipo:** Rellenar un formulario de cierre con `destino`, `horas de trabajo`, etc., y marcar el equipo como "cerrado".
    *   **Notificación por Correo:** Enviar automáticamente un resumen del formulario de cierre por email (configurable vía SMTP).
    *   **Documentación Final:** Adjuntar el `Certificado CAT` (para equipos 'Útiles') o el `DR Final` (para equipos 'Reparables').
    *   **Salida de Inventario:** Marcar el equipo como fuera de inventario, registrando la fecha de salida.
*   **Base de Datos Robusta:** Utiliza **SQLite** con un esquema ampliado para almacenar todos los detalles del proceso. El SN es único para evitar duplicados.
*   **Gestión de Archivos Organizada:** Guarda todos los documentos (SL2000, fotos, CAT, DR) en una estructura de carpetas dedicada: `docs/PN_SN/[entrada|trabajo|cierre]/`.
*   **Consultas y Reportes:**
    *   Filtra la vista principal por estado de inventario (`En Inventario`, `Fuera de Inventario`, `Todos`).
    *   Búsqueda en tiempo real por `PN` o `SN`.
    *   Exporta la vista actual de la tabla a un archivo **Excel** (`.xlsx`).
*   **Validaciones y Alertas:** El sistema avisa al usuario si intenta realizar acciones fuera de orden (ej. dar salida sin la documentación final requerida).
*   **Estadísticas Rápidas:** Muestra un conteo de equipos totales y en inventario.

---

## 🛠️ Tecnologías Utilizadas

*   **Lenguaje:** Python 3
*   **Interfaz Gráfica (GUI):** Tkinter (la librería estándar de Python para GUI).
*   **Base de Datos:** SQLite3
*   **Exportación a Excel:** Pandas & Openpyxl
*   **Envío de Correo:** smtplib
*   **Gestión de Datos:** json

---

## 🚀 Cómo Empezar

Sigue estos pasos para poner en marcha la aplicación en tu máquina local.

### 1. Prerrequisitos

Asegúrate de tener **Python 3** instalado en tu sistema. Si no lo tienes, puedes descargarlo desde python.org.

> **Importante:** Durante la instalación en Windows, asegúrate de marcar la casilla que dice **"Add Python to PATH"**.

### 2. Clonar el Repositorio

Abre una terminal y clona este repositorio en tu máquina:

```bash
git clone https://github.com/tu-usuario/tu-repositorio.git
cd tu-repositorio
```
*(Reemplaza `tu-usuario/tu-repositorio` con tu URL real de GitHub)*

### 3. Instalar Dependencias

La aplicación utiliza `pandas` y `openpyxl` para la funcionalidad de exportación a Excel. Instálalas usando pip:

```bash
# En Windows
py -m pip install pandas openpyxl

# En macOS / Linux
python3 -m pip install pandas openpyxl
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