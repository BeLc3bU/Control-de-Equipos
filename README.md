# Control de Equipos de Aviónica (Versión PyQt6)

Una aplicación de escritorio moderna desarrollada en Python y **PyQt6** para gestionar el flujo de trabajo completo de los equipos que pasan por un banco de pruebas de aviónica, desde la entrada hasta la salida final. Esta versión migra la interfaz de Tkinter a PyQt6, ofreciendo una experiencia de usuario más rica y profesional.


*(Nota: Reemplaza la URL de arriba con una captura de pantalla real de tu aplicación para una mejor presentación).*

---

## 🎥 Demo en Video

[![Ver en YouTube](https://img.youtube.com/vi/Ij5PyH-BzMI/0.jpg)](https://youtu.be/Ij5PyH-BzMI)

---

## 📋 Características Principales

*   **Interfaz Moderna y Fluida:** Desarrollada con PyQt6 para una experiencia de usuario profesional y agradable.
*   **Mejoras de UI/UX Avanzadas:**
    *   **Validación en Tiempo Real:** Los formularios marcan los campos inválidos con un borde rojo y deshabilitan el botón de guardar hasta que todo sea correcto.
    *   **Autocompletado Inteligente:** El campo "Nombre Equipo" es un combo editable que sugiere nombres existentes. Al introducir un PN, autocompleta el nombre del equipo.
    *   **Feedback Visual Mejorado:** La tabla principal usa iconos de estado para una identificación rápida, tooltips detallados al pasar el ratón y coloreado de filas distintivo.
    *   **Historial Enriquecido:** El historial de intervenciones ahora soporta texto enriquecido (negrita, listas, etc.).
    *   **Menús Contextuales:** Acceso rápido a acciones como "Abrir Archivo" o "Abrir Carpeta Contenedora" con un clic derecho.
*   **Copias de Seguridad y Restauración:** Funciones integradas para crear copias de seguridad comprimidas de la base de datos y restaurarlas de forma segura, con advertencias claras al usuario.
*   **Flujo de Trabajo Completo:** Gestiona el ciclo de vida de un equipo a través de múltiples etapas: **Entrada**, **Trabajo**, **Cierre** y **Salida**.
*   **Registro de Entrada Detallado:** Captura `nombre`, `PN`, `SN`, `estado`, `Nº OT`, `Nº DR`, `observaciones` y documentos adjuntos.
*   **Panel de Gestión Centralizado:** Al hacer doble clic en un equipo, se abre una ventana con pestañas para:
    *   **Pestaña de Trabajo:** Permite actualizar el estado de salida, añadir observaciones, subir múltiples tipos de archivos, registrar un **historial cronológico de intervenciones** y abrir un formulario para **solicitar material**.
    *   **Pestaña de Cierre:** Rellenar un formulario de cierre con `destino`, `horas de trabajo`, etc., y marcar el equipo como "cerrado".
    *   **Notificación por Correo Simplificada:** Abre la aplicación web de Gmail con un borrador de correo listo para enviar, sin necesidad de configurar SMTP.
    *   **Documentación Final:** Subir el `Certificado CAT` (para equipos 'Útiles') o el `DR Final` (para equipos 'Reparables') desde la pestaña de cierre.
    *   **Salida de Inventario:** Marcar el equipo como fuera de inventario, registrando la fecha de salida.
*   **Base de Datos Robusta:** Utiliza **SQLite** con un esquema que permite registrar múltiples ciclos de mantenimiento para un mismo equipo, usando la **Orden Técnica (OT)** como identificador único por ciclo.
*   **Gestión de Archivos Organizada:** Guarda todos los documentos en una estructura de carpetas jerárquica y versionada: `docs/NombreDelEquipo/SN/ArisingXX/`, evitando colisiones de nombres.
*   **Análisis y Reportes Avanzados:**
    *   Filtra la vista principal por estado de inventario (`En Inventario`, `Fuera de Inventario`, `Todos`).
    *   Búsqueda en tiempo real por `OT`, `Nombre`, `PN` o `SN`.
    *   **Coloreado de Filas:** La tabla principal resalta las filas con colores según el estado del equipo para una identificación visual rápida.
    *   Exporta la vista actual de la tabla a un archivo **Excel** (`.xlsx`).
    *   Genera un **informe detallado en PDF** de todos los equipos en inventario, incluyendo su historial de intervenciones.
    *   **Gráficos de Productividad:** Genera visualizaciones dinámicas con filtro por fecha para analizar:
        *   **Rendimiento del Taller:** Equipos cerrados por mes.
        *   **Distribución de Resultados:** Gráfico circular de estados de salida.
        *   **Tiempo de Ciclo (Turnaround):** Días promedio desde la entrada hasta el cierre.
        *   **Complejidad de Reparaciones:** Histograma de horas de trabajo.
*   **Rendimiento Optimizado:** Las operaciones lentas como la exportación a Excel y la generación de PDF se ejecutan en **hilos de trabajo separados** para no congelar la interfaz.
*   **Validaciones y Alertas:** El sistema avisa al usuario si intenta realizar acciones fuera de orden (ej. dar salida sin la documentación final requerida).
*   **Logging Centralizado:** Registra eventos importantes y errores en un archivo `control_equipos.log` para facilitar la depuración.
*   **Mejoras de Accesibilidad y QoL:**
    *   La aplicación recuerda el tamaño y la posición de la ventana, así como el ancho de las columnas.
    *   Atajos de teclado (`Ctrl+N`, `Ctrl+E`, etc.) para acciones comunes.
    *   Descripciones emergentes (Tooltips) en los botones.
    *   Ordenamiento natural en las columnas de la tabla (entiende los números dentro del texto).
---

## 🛠️ Tecnologías Utilizadas

*   **Lenguaje:** Python 3
*   **Interfaz Gráfica (GUI):** PyQt6
*   **Base de Datos:** SQLite3
*   **Gráficos y Datos:** Pandas & Matplotlib
*   **Exportación a Excel:** Openpyxl
*   **Generación de PDF:** ReportLab

---

## 🚀 Cómo Empezar

Sigue estos pasos para poner en marcha la aplicación en tu máquina local.

### 1. Prerrequisitos y Configuración Inicial

Asegúrate de tener **Python 3** instalado en tu sistema. Si no lo tienes, puedes descargarlo desde python.org.

> **Importante:** Durante la instalación en Windows, asegúrate de marcar la casilla que dice **"Add Python to PATH"**.

### 2. Clonar el Repositorio

Abre una terminal o `Git Bash` y clona este repositorio en tu máquina:

```bash
git clone https://github.com/pablo-ma/Control-de-Equipos.git
cd Control-de-Equipos
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
py main_pyqt.py

# En macOS / Linux
python3 main_pyqt.py
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

---

## 🗺️ Roadmap de Futuras Mejoras

Esta es una lista de las próximas características y mejoras planificadas para la aplicación:

*   **Integración de Captura por Cámara:** Añadir una función que permita abrir una cámara web para tomar fotos directamente desde la aplicación y adjuntarlas al equipo.
*   **Sistema de Autenticación y Roles:** Implementar un sistema de login para controlar el acceso. Se definirán roles (ej. `Técnico`, `Administrador`) con diferentes niveles de permisos.
*   **Panel de Administración Web:** Desarrollar una interfaz web de administración (`backend`) que permita a los usuarios con rol de `Administrador` realizar operaciones de mantenimiento directamente sobre la base de datos (editar o eliminar registros de forma segura).
*   **Automatismo de Copia de Seguridad:** Configurar un sistema para que la aplicación realice copias de seguridad de la base de datos de forma automática y periódica.
---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.
```