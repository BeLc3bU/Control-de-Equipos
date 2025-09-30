# Control de Equipos de Aviónica

Una aplicación de escritorio simple desarrollada en Python para gestionar el flujo de equipos que entran y salen de un banco de pruebas de aviónica.

 
*(Nota: Reemplaza la URL de arriba con una captura de pantalla real de tu aplicación para una mejor presentación)*

---

## 📋 Características Principales

*   **Registro de Entrada:** Guarda nuevos equipos con su Part Number (PN), Serial Number (SN), estado, observaciones y un documento adjunto (PDF, imagen, etc.).
*   **Registro de Salida:** Busca un equipo por su SN y registra su estado de salida, observaciones y documento asociado.
*   **Base de Datos Local:** Utiliza **SQLite** para almacenar todos los datos de forma persistente y segura. El SN es único para evitar duplicados.
*   **Gestión de Documentos:** Almacena automáticamente los documentos de entrada y salida en una estructura de carpetas organizada (`docs/PN_SN/`).
*   **Visualización y Búsqueda:** Muestra un listado completo de los equipos en una tabla. Incluye una barra de búsqueda en tiempo real por PN o SN.
*   **Acceso a Documentos:** Permite abrir los documentos adjuntos directamente desde la interfaz haciendo doble clic en un registro.
*   **Exportación de Datos:** Exporta la vista actual de la tabla a un archivo **Excel** (`.xlsx`) con un solo clic.
*   **Estadísticas Básicas:** Muestra un resumen de la cantidad de equipos por estado de entrada.

---

## 🛠️ Tecnologías Utilizadas

*   **Lenguaje:** Python 3
*   **Interfaz Gráfica (GUI):** Tkinter (la librería estándar de Python para GUI).
*   **Base de Datos:** SQLite3
*   **Exportación a Excel:** Pandas y Openpyxl

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

La aplicación requiere las librerías `pandas` y `openpyxl` para la funcionalidad de exportación a Excel. Instálalas usando pip:

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