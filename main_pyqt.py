# main_pyqt.py
import sys
import traceback
import re
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTableView, QAbstractItemView, QHeaderView, QComboBox, 
    QLineEdit, QLabel, QStatusBar, QMessageBox, QFileDialog
)
from PyQt6.QtGui import QAction, QStandardItemModel, QStandardItem, QColor, QIcon
from PyQt6.QtCore import Qt, QSettings, QRunnable, QThreadPool, QObject, pyqtSignal

# --- IMPORTACIONES DE TU LÓGICA EXISTENTE ---
# ¡La gran ventaja es que podemos reutilizar todo esto!
from config import Config
from logger import logger
from validators import Validator
from database_improved import Database
from file_utils import open_file
from pyqt_windows import EntryDialog, ManageEquipmentDialog, ProductivityChartDialog

# --- INICIALIZACIÓN DEL ENTORNO (igual que antes) ---
db = None

def setup_environment():
    """Inicializa el entorno de la aplicación (BD, carpetas)."""
    global db
    db = Database(Config.DB_NAME)
    db.setup()
    logger.info("Entorno configurado correctamente para PyQt.")

# =================================================================================
# Worker para Tareas en Segundo Plano (Rendimiento)
# =================================================================================

class WorkerSignals(QObject):
    """Define las señales disponibles para un hilo de trabajo."""
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)

class Worker(QRunnable):
    """
    Worker thread
    Hereda de QRunnable para poder ser ejecutado en un QThreadPool.
    """
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        """Ejecuta la tarea en segundo plano."""
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control de Equipos - Banco de Pruebas")
        self.setGeometry(100, 100, 1400, 750)

        # Pool de hilos para tareas en segundo plano
        self.threadpool = QThreadPool()
        logger.info(f"Multithreading con un máximo de {self.threadpool.maxThreadCount()} hilos.")

        # Constantes de la clase
        self.STATUS_COLORS = {
            "Útil": (QColor("#fff3cd"), QColor("black")),
            "Reparable": (QColor("#d4edda"), QColor("black")),
            "Baja": (QColor("#f8d7da"), QColor("black")),
            "Stamby": (QColor("#343a40"), QColor("white")),
            "Litigio": (QColor("white"), QColor("black")),
            "Falto de material": (QColor("#cce5ff"), QColor("black")),
            "Incompleto": (QColor("#fdebd0"), QColor("black"))
        }
        
        # Definir las cabeceras como una constante de la clase para fácil acceso
        self.HEADERS = ["OT", "Nombre", "PN", "SN", "Estado Entrada", "Obs. Entrada", "Fecha Entrada",
                        "Estado Salida", "Obs. Salida", "Fecha Cierre", "Inventario", "ID"]


        # --- Icono de la Aplicación ---
        app_icon_path = os.path.join('icons', 'app_icon.png')
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))

        # --- Barra de Herramientas (Toolbar) ---
        toolbar = self.addToolBar("Acciones Principales")
        
        # Acciones para la barra de herramientas
        action_new = QAction(QIcon(os.path.join('icons', 'new.png')), "Registrar Nuevo Equipo", self)
        action_new.setShortcut("Ctrl+N")
        action_new.setToolTip("Registrar un nuevo equipo en el sistema (Ctrl+N)")
        action_new.triggered.connect(self.open_entry_window)
        toolbar.addAction(action_new)

        action_export = QAction(QIcon(os.path.join('icons', 'excel.png')), "Exportar a Excel", self)
        action_export.setShortcut("Ctrl+E")
        action_export.setToolTip("Exportar la vista actual a un archivo Excel (Ctrl+E)")
        action_export.triggered.connect(self.export_to_excel)
        toolbar.addAction(action_export)

        action_report = QAction(QIcon(os.path.join('icons', 'pdf.png')), "Generar Informe", self)
        action_report.setShortcut("Ctrl+P") # P de "Print" o "PDF"
        action_report.setToolTip("Generar un informe PDF del inventario (Ctrl+P)")
        action_report.triggered.connect(self.generate_inventory_report)
        toolbar.addAction(action_report)

        action_charts = QAction(QIcon(os.path.join('icons', 'graficos.png')), "Generar Gráficos de Productividad", self)
        action_charts.setShortcut("Ctrl+G")
        action_charts.setToolTip("Generar gráficos de productividad (Ctrl+G)")
        action_charts.triggered.connect(self.generate_productivity_charts)
        toolbar.addAction(action_charts)

        # --- Widget Central y Layouts ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Filtros y Búsqueda ---
        filter_layout = QHBoxLayout()
        
        filter_layout.addStretch() # Empuja los widgets hacia la derecha
        
        filter_layout.addWidget(QLabel("Filtro Inventario:"))
        self.inventory_filter = QComboBox()
        self.inventory_filter.addItems(["Todos", "En Inventario", "Fuera de Inventario"])
        self.inventory_filter.setCurrentText("En Inventario")
        self.inventory_filter.currentTextChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.inventory_filter)

        filter_layout.addWidget(QLabel("Buscar (OT/Nombre/PN/SN):"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Escribe para buscar...")
        self.search_input.setAccessibleName("Campo de búsqueda") # Para lectores de pantalla
        self.search_input.textChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.search_input)

        main_layout.addLayout(filter_layout)

        # --- Tabla de Equipos ---
        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(self.HEADERS)
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        
        # Configuración de la apariencia de la tabla
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # No editable
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # Seleccionar filas completas
        self.table_view.setAlternatingRowColors(True)
        
        # --- Política de Redimensionamiento de Columnas ---
        header = self.table_view.horizontalHeader()
        
        # Permitir que el usuario ajuste todas las columnas manualmente.
        for i in range(len(self.HEADERS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        self.table_view.setSortingEnabled(True)
        
        # Permitir que el modelo maneje el ordenamiento para un control más fino
        self.table_model.setSortRole(Qt.ItemDataRole.UserRole)
        self.table_view.sortByColumn(5, Qt.SortOrder.DescendingOrder) # Ordenar por fecha de entrada por defecto

        # Conectar doble clic
        self.table_view.doubleClicked.connect(self.on_double_click)

        main_layout.addWidget(self.table_view)

        # --- Barra de Estado ---
        self.setStatusBar(QStatusBar(self))

        # Cargar la configuración de la ventana (geometría y estado de la tabla)
        # Se llama aquí, después de que todos los widgets han sido creados.
        self.refresh_table()
        self.load_settings()

    def load_settings(self):
        """Carga la geometría de la ventana y el estado de la tabla."""
        settings = QSettings("YourCompany", "ControlEquipos")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        table_state = settings.value("main_table_state")
        if table_state:
            self.table_view.horizontalHeader().restoreState(table_state)
        else:
            pass # No hacemos nada, el usuario ajustará y se guardará al cerrar.

    def closeEvent(self, event):
        """Guarda la configuración al cerrar la aplicación."""
        settings = QSettings("YourCompany", "ControlEquipos")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("main_table_state", self.table_view.horizontalHeader().saveState())
        super().closeEvent(event)

    def refresh_table(self):
        """Limpia y recarga la tabla con datos de la BD, aplicando filtros."""
        self.table_model.removeRows(0, self.table_model.rowCount())
        
        search_term = self.search_input.text().strip()
        inv_filter = self.inventory_filter.currentText()

        # La misma consulta que ya tenías, ¡perfecto!
        query = """SELECT id, numero_ot, nombre_equipo, pn, sn, estado_entrada, 
                   fecha_entrada, estado_salida, fecha_cierre, inventario, obs_entrada, 
                   obs_salida FROM equipos"""
        conditions = []
        params = []

        if search_term:
            conditions.append("(numero_ot LIKE ? OR nombre_equipo LIKE ? OR pn LIKE ? OR sn LIKE ?)")
            params.extend([f"%{search_term}%"] * 4)
        
        if inv_filter == "En Inventario":
            conditions.append("inventario = 1")
        elif inv_filter == "Fuera de Inventario":
            conditions.append("inventario = 0")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY fecha_entrada DESC"

        records = db.fetch_query(query, tuple(params))
        if records is None:
            QMessageBox.critical(self, "Error de Base de Datos", "No se pudieron cargar los datos.")
            return

        for row_data in records:
            row_items = [
                QStandardItem(str(row_data['numero_ot'] or "")),
                QStandardItem(str(row_data['nombre_equipo'] or "")),
                QStandardItem(str(row_data['pn'] or "")),
                QStandardItem(str(row_data['sn'] or "")),
                QStandardItem(str(row_data['estado_entrada'] or "")),
                QStandardItem(str(row_data['obs_entrada'] or "")),
                QStandardItem(str(row_data['fecha_entrada'] or "")),
                QStandardItem(str(row_data['estado_salida'] or "")),
                QStandardItem(str(row_data['obs_salida'] or "")),
                QStandardItem(str(row_data['fecha_cierre'] or "")),
                QStandardItem("Dentro" if row_data['inventario'] else "Fuera"),
                QStandardItem(str(row_data['id'])) # Guardamos el ID en una columna oculta
            ]
            
            # --- ROL DE ORDENAMIENTO PARA ORDEN NATURAL ---
            # Para cada celda, guardamos una versión "ordenable" del dato
            for i, item in enumerate(row_items):
                # Intentamos convertir a número para un ordenamiento numérico correcto
                sort_key = self.natural_sort_key(item.text())
                item.setData(sort_key, Qt.ItemDataRole.UserRole)

            # --- LÓGICA DE COLOREADO DE FILAS ---
            background_color, foreground_color = self.get_color_for_status(row_data)
            if background_color:
                for item in row_items:
                    item.setBackground(background_color)
                    if foreground_color:
                        item.setForeground(foreground_color)

            self.table_model.appendRow(row_items)

        # Ocultar la columna de ID
        self.table_view.setColumnHidden(self.HEADERS.index("ID"), True)
        
        self.update_stats(len(records))

    def get_color_for_status(self, row_data):
        """Determina el color de la fila según el estado del equipo."""
        if not row_data['inventario']:
            # Para filas fuera de inventario, un fondo gris claro con texto negro es seguro.
            return QColor("#f0f0f0"), QColor("black")

        status = row_data['estado_salida'] or row_data['estado_entrada']
        
        # Usamos la constante de la clase
        bg_color, fg_color = self.STATUS_COLORS.get(status, (None, None))
        
        return bg_color, fg_color

    def natural_sort_key(self, s):
        """Clave para un ordenamiento natural (maneja números correctamente)."""
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', s)]

    def update_stats(self, displayed_count):
        """Calcula y muestra estadísticas en la barra de estado."""
        total_row = db.fetch_query("SELECT COUNT(*) FROM equipos", one=True)
        total = total_row[0] if total_row else 0
        
        inventario_row = db.fetch_query("SELECT COUNT(*) FROM equipos WHERE inventario = 1", one=True)
        en_inventario = inventario_row[0] if inventario_row else 0

        stats_text = f"Total: {total} | En Inventario: {en_inventario} | Mostrando: {displayed_count}"
        self.statusBar().showMessage(stats_text)

    # --- FUNCIONES A IMPLEMENTAR ---
    def on_double_click(self, index):
        # La columna 9 es donde guardamos el ID
        id_item = self.table_model.item(index.row(), self.HEADERS.index("ID"))
        record_id = int(id_item.text())
        dialog = ManageEquipmentDialog(db, record_id, self)
        dialog.data_changed.connect(self.refresh_table) # Si algo cambia, refresca la tabla
        dialog.exec()

    def open_entry_window(self):
        """Abre el diálogo para registrar un nuevo equipo."""
        dialog = EntryDialog(db, self) # Pasamos la sesión de BD y el parent
        if dialog.exec(): # .exec() retorna True si se llamó a .accept()
            self.refresh_table()

    def start_long_running_task(self, task_function, on_finish, on_error, *args):
        """Inicia una tarea en un hilo separado."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.statusBar().showMessage(f"Procesando: {task_function.__name__}...")

        worker = Worker(task_function, *args)
        worker.signals.finished.connect(lambda: self.on_task_finished(on_finish))
        worker.signals.error.connect(on_error)
        self.threadpool.start(worker)

    def on_task_finished(self, callback):
        """Se ejecuta cuando una tarea en segundo plano finaliza."""
        QApplication.restoreOverrideCursor()
        self.statusBar().showMessage("Listo.", 3000)
        callback()

    def export_to_excel(self):
        """Exporta los datos actualmente visibles en la tabla a un archivo Excel."""
        try:
            import pandas as pd
        except ImportError:
            QMessageBox.critical(self, "Librería no encontrada", "Se necesita 'pandas' y 'openpyxl'.\nInstala con: py -m pip install pandas openpyxl")
            return

        if self.table_model.rowCount() == 0:
            QMessageBox.information(self, "Sin datos", "No hay datos en la tabla para exportar.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Guardar como Excel", "", "Archivos de Excel (*.xlsx)")
        if not filepath:
            return

        # Extraer datos en el hilo principal (es rápido)
        # Extraer datos del modelo de la tabla
        headers = [self.table_model.horizontalHeaderItem(i).text() for i in range(self.table_model.columnCount()) if not self.table_view.isColumnHidden(i)]
        data = []
        for row in range(self.table_model.rowCount()):
            row_data = [self.table_model.item(row, col).text() for col in range(self.table_model.columnCount()) if not self.table_view.isColumnHidden(col)]
            data.append(row_data)

        # La escritura a disco se hace en un hilo secundario
        def do_export(data, headers, filepath):
            df = pd.DataFrame(data, columns=headers)
            df.to_excel(filepath, index=False)

        def on_export_complete():
            QMessageBox.information(self, "Exportación Exitosa", f"Datos exportados a {os.path.basename(filepath)}")

        def on_export_error(err):
            exctype, value, _ = err
            if isinstance(value, PermissionError):
                QMessageBox.critical(self, "Error de Permisos", "No se pudo guardar el archivo. Asegúrate de que no esté abierto en otro programa.")
            else:
                QMessageBox.critical(self, "Error de Exportación", f"No se pudo guardar el archivo Excel: {value}")

        self.start_long_running_task(do_export, on_export_complete, on_export_error, data, headers, filepath)

    def generate_inventory_report(self):
        """Inicia la generación de un informe en PDF en un hilo secundario."""
        try:
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_LEFT
        except ImportError:
            QMessageBox.critical(self, "Librería no encontrada", "Se necesita 'reportlab' para generar informes.\nInstala con: py -m pip install reportlab")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Guardar Informe PDF", "", "Archivos PDF (*.pdf)")
        if not filepath:
            return

        # La generación del PDF se hace en un hilo secundario
        def do_report_generation(filepath):
            records = db.fetch_query("""
                SELECT numero_ot, nombre_equipo, pn, sn, estado_salida, log_trabajo 
                FROM equipos WHERE inventario = 1 ORDER BY fecha_entrada DESC
            """)
            if not records:
                return "No hay equipos en inventario para generar un informe."

            doc = SimpleDocTemplate(filepath)
            styles = getSampleStyleSheet()
            log_style = ParagraphStyle(name='LogStyle', parent=styles['Normal'], alignment=TA_LEFT, leftIndent=15)
            story = [Paragraph("Informe de Equipos en Inventario", styles['h1']), Spacer(1, 0.2 * inch)]

            for i, record in enumerate(records):
                story.append(Paragraph(f"<b>Orden Técnica:</b> {record['numero_ot'] or 'N/A'}", styles['Normal']))
                story.append(Paragraph(f"<b>Nombre del Equipo:</b> {record['nombre_equipo'] or 'N/A'}", styles['Normal']))
                story.append(Paragraph(f"<b>PN / SN:</b> {record['pn']} / {record['sn']}", styles['Normal']))
                story.append(Paragraph(f"<b>Estado Actual:</b> {record['estado_salida'] or 'Pendiente'}", styles['Normal']))
                story.append(Spacer(1, 0.1 * inch))
                story.append(Paragraph("<b>Historial de Intervenciones:</b>", styles['h3']))
                try:
                    log_entries = json.loads(record['log_trabajo'] or '[]')
                    for entry in log_entries:
                        story.append(Paragraph(f"- ({entry.get('timestamp', '')}) {entry.get('entry', '')}", log_style))
                except (json.JSONDecodeError, TypeError):
                    story.append(Paragraph(f"- {record['log_trabajo'] or 'Sin intervenciones.'}", log_style))
                if i < len(records) - 1: story.append(PageBreak())

            doc.build(story)
            return None # Éxito

        def on_report_complete():
            QMessageBox.information(self, "Informe Generado", f"El informe ha sido guardado en:\n{os.path.basename(filepath)}")

        def on_report_error(err):
            _, value, _ = err
            QMessageBox.critical(self, "Error de Generación", f"No se pudo generar el informe PDF: {value}")

        self.start_long_running_task(do_report_generation, on_report_complete, on_report_error, filepath)

    def generate_productivity_charts(self):
        """Muestra un diálogo para los futuros gráficos de productividad."""
        dialog = ProductivityChartDialog(db, self)
        dialog.exec()


if __name__ == "__main__":
    # Configurar el entorno antes de crear la aplicación
    setup_environment()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())