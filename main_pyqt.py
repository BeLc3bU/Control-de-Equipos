# main_pyqt.py
import sys
import traceback
import re
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTableView, QAbstractItemView, QHeaderView, QComboBox, 
    QLineEdit, QLabel, QStatusBar, QMessageBox, QFileDialog
)
from PyQt6.QtGui import QAction, QStandardItemModel, QStandardItem, QColor, QIcon
from PyQt6.QtCore import Qt, QSettings, QRunnable, QThreadPool, QObject, pyqtSignal

# --- IMPORTACIONES DE TU LÓGICA EXISTENTE ---\
from config import Config
from logger import logger
from validators import Validator
from database_improved import Database
from file_utils import open_file, create_database_backup, restore_database_from_backup
from pyqt_windows import EntryDialog, ManageEquipmentDialog, ProductivityChartDialog

# --- INICIALIZACIÓN DEL ENTORNO (igual que antes) ---\
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
    progress = pyqtSignal(int) # Señal para el progreso (0-100)

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
            result = self.fn(*self.args, signals=self.signals, **self.kwargs)
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
            "Reparable": (QColor("#d1e7dd"), QColor("black")),
            "Baja": (QColor("#f8d7da"), QColor("black")),
            "Stamby": (QColor("#343a40"), QColor("white")),
            "Litigio": (QColor("white"), QColor("black")),
            "Falto de material": (QColor("#cce5ff"), QColor("black")),
            "Incompleto": (QColor("#fdebd0"), QColor("black")),
            # Nuevo estado visual
            "Cerrado en Inventario": (QColor("#e2e3e5"), QColor("black"))
        }
        
        self.HEADERS = ["Estado", "OT", "Nombre", "PN", "SN", "Estado Entrada", "Obs. Entrada", "Fecha Entrada",
                        "Estado Salida", "Obs. Salida", "Fecha Cierre", "Inventario", "ID"]


        # --- Icono de la Aplicación ---\
        app_icon_path = os.path.join('icons', 'app_icon.png')
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))

        # --- Barra de Herramientas (Toolbar) ---\
        toolbar = self.addToolBar("Acciones Principales")
        
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
        action_report.setShortcut("Ctrl+P")
        action_report.setToolTip("Generar un informe PDF del inventario (Ctrl+P)")
        action_report.triggered.connect(self.generate_inventory_report)
        toolbar.addAction(action_report)

        action_charts = QAction(QIcon(os.path.join('icons', 'graficos.png')), "Generar Gráficos de Productividad", self)
        action_charts.setShortcut("Ctrl+G")
        action_charts.setToolTip("Generar gráficos de productividad (Ctrl+G)")
        action_charts.triggered.connect(self.generate_productivity_charts)
        toolbar.addAction(action_charts)

        action_backup = QAction(QIcon(os.path.join('icons', 'backup.png')), "Crear Copia de Seguridad", self)
        action_backup.setShortcut("Ctrl+B")
        action_backup.setToolTip("Crear una copia de seguridad de la base de datos (Ctrl+B)")
        action_backup.triggered.connect(self.create_backup)
        toolbar.addAction(action_backup)

        action_restore = QAction(QIcon(os.path.join('icons', 'restore.png')), "Restaurar Copia de Seguridad", self)
        action_restore.setShortcut("Ctrl+R")
        action_restore.setToolTip("Restaurar la base de datos desde una copia de seguridad (Ctrl+R)")
        action_restore.triggered.connect(self.restore_from_backup)
        toolbar.addAction(action_restore)

        # --- Widget Central y Layouts ---\
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Filtros y Búsqueda ---\
        filter_layout = QHBoxLayout()
        
        filter_layout.addStretch()
        
        filter_layout.addWidget(QLabel("Filtro Inventario:"))
        self.inventory_filter = QComboBox()
        self.inventory_filter.addItems(["Todos", "En Inventario", "Fuera de Inventario"])
        self.inventory_filter.setCurrentText("En Inventario")
        self.inventory_filter.currentTextChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.inventory_filter)

        filter_layout.addWidget(QLabel("Buscar por:"))
        self.search_criteria = QComboBox()
        self.SEARCH_CRITERIA_MAP = {
            "Todo": ["numero_ot", "nombre_equipo", "pn", "sn"],
            "OT": ["numero_ot"], "Nombre": ["nombre_equipo"], "PN": ["pn"], "SN": ["sn"]
        }
        self.search_criteria.addItems(self.SEARCH_CRITERIA_MAP.keys())
        self.search_criteria.currentTextChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.search_criteria)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Escribe para buscar...")
        self.search_input.textChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.search_input)

        main_layout.addLayout(filter_layout)

        # --- Tabla de Equipos ---\
        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(self.HEADERS)
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        
        header = self.table_view.horizontalHeader()
        for i in range(len(self.HEADERS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        self.table_view.setSortingEnabled(True)
        
        self.table_model.setSortRole(Qt.ItemDataRole.UserRole)
        self.table_view.sortByColumn(5, Qt.SortOrder.DescendingOrder)

        self.table_view.doubleClicked.connect(self.on_double_click)

        main_layout.addWidget(self.table_view)

        # --- Barra de Estado ---\
        self.setStatusBar(QStatusBar(self))

        self.refresh_table()
        self.load_settings()

    def load_settings(self):
        """Carga la geometría de la ventana y el estado de la tabla."""
        # REFACTOR: Usamos constantes desde config.py
        settings = QSettings(Config.COMPANY_NAME, Config.APP_NAME)
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        table_state = settings.value("main_table_state")
        if table_state:
            self.table_view.horizontalHeader().restoreState(table_state)

    def closeEvent(self, event):
        """Guarda la configuración al cerrar la aplicación."""
        # REFACTOR: Usamos constantes desde config.py
        settings = QSettings(Config.COMPANY_NAME, Config.APP_NAME)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("main_table_state", self.table_view.horizontalHeader().saveState())
        super().closeEvent(event)

    def refresh_table(self):
        """Limpia y recarga la tabla con datos de la BD, aplicando filtros."""
        self.table_model.removeRows(0, self.table_model.rowCount())
        
        search_term = self.search_input.text().strip()
        inv_filter = self.inventory_filter.currentText()
        criteria_key = self.search_criteria.currentText()

        query = """SELECT id, numero_ot, nombre_equipo, pn, sn, estado_entrada, cerrado,
                   fecha_entrada, estado_salida, fecha_cierre, inventario, obs_entrada, 
                   obs_salida FROM equipos"""
        conditions = []
        params = []

        if search_term:
            search_columns = self.SEARCH_CRITERIA_MAP.get(criteria_key, [])
            search_conditions = [f"{col} LIKE ?" for col in search_columns]
            if search_conditions:
                conditions.append(f"({' OR '.join(search_conditions)})")
                params.extend([f"%{search_term}%"] * len(search_conditions))
        
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
            status_icon_item = QStandardItem()
            status = row_data['estado_salida'] or row_data['estado_entrada']
            icon_path = self.get_icon_for_status(status, row_data)
            if icon_path and os.path.exists(icon_path):
                status_icon_item.setIcon(QIcon(icon_path))
            
            tooltip_text = self.create_tooltip_for_row(row_data)
            status_icon_item.setToolTip(tooltip_text)

            row_items = [
                status_icon_item,
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
                QStandardItem(str(row_data['id']))
            ]
            
            for i, item in enumerate(row_items):
                sort_key = self.natural_sort_key(item.text())
                item.setToolTip(tooltip_text)
                item.setData(sort_key, Qt.ItemDataRole.UserRole)

            background_color, foreground_color = self.get_color_for_status(row_data)
            if background_color:
                for item in row_items:
                    item.setBackground(background_color)
                    if foreground_color:
                        item.setForeground(foreground_color)

            self.table_model.appendRow(row_items)

        self.table_view.setColumnHidden(self.HEADERS.index("ID"), True)
        
        self.update_stats(len(records))

    def get_icon_for_status(self, status, row_data):
        """Devuelve la ruta del icono según el estado."""
        if not row_data['inventario']:
            return os.path.join('icons', 'out_of_stock.png')
        if row_data['cerrado']:
            return os.path.join('icons', 'closed_in_stock.png')

        icon_map = {
            "Útil": os.path.join('icons', 'util.png'),
            "Reparable": os.path.join('icons', 'reparable.png'),
            "Baja": os.path.join('icons', 'baja.png'),
            "Stamby": os.path.join('icons', 'standby.png'),
            "Falto de material": os.path.join('icons', 'missing_parts.png'),
            "Incompleto": os.path.join('icons', 'incomplete.png'),
            "Litigio": os.path.join('icons', 'litigio.png'),
        }
        return icon_map.get(status, os.path.join('icons', 'default.png'))

    def create_tooltip_for_row(self, row_data):
        """Crea un texto de tooltip detallado para una fila."""
        return (
            f"<b>{row_data['nombre_equipo']}</b><br>"
            f"<b>PN/SN:</b> {row_data['pn']} / {row_data['sn']}<br>"
            f"<b>OT:</b> {row_data['numero_ot']}<br>"
            f"<b>Fecha Entrada:</b> {row_data['fecha_entrada']}<br>"
            f"<b>Estado Actual:</b> {row_data['estado_salida'] or row_data['estado_entrada']}<br>"
            f"<b>Inventario:</b> {'Dentro' if row_data['inventario'] else 'Fuera'}"
        )

    def get_color_for_status(self, row_data):
        """Determina el color de la fila según el estado del equipo."""
        if not row_data['inventario']:
            return QColor("#f0f0f0"), QColor("black")
        
        if row_data['cerrado'] and row_data['inventario']:
            return self.STATUS_COLORS.get("Cerrado en Inventario")

        status = row_data['estado_salida'] or row_data['estado_entrada']
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

    def on_double_click(self, index):
        id_item = self.table_model.item(index.row(), self.HEADERS.index("ID"))
        record_id = int(id_item.text())
        dialog = ManageEquipmentDialog(db, record_id, self)
        dialog.data_changed.connect(self.refresh_table)
        dialog.exec()

    def open_entry_window(self):
        """Abre el diálogo para registrar un nuevo equipo."""
        dialog = EntryDialog(db, self)
        if dialog.exec():
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
            QMessageBox.critical(self, "Librería no encontrada", "Se necesita 'pandas' y 'openpyxl'.\\nInstala con: py -m pip install pandas openpyxl")
            return

        if self.table_model.rowCount() == 0:
            QMessageBox.information(self, "Sin datos", "No hay datos en la tabla para exportar.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Guardar como Excel", "", "Archivos de Excel (*.xlsx)")
        if not filepath:
            return

        headers = [self.table_model.horizontalHeaderItem(i).text() for i in range(self.table_model.columnCount()) if not self.table_view.isColumnHidden(i)]
        data = []
        for row in range(self.table_model.rowCount()):
            row_data = [self.table_model.item(row, col).text() for col in range(self.table_model.columnCount()) if not self.table_view.isColumnHidden(col)]
            data.append(row_data)

        def do_export(data, headers, filepath, signals):
            df = pd.DataFrame(data, columns=headers)
            for i in range(5):
                signals.progress.emit(int((i + 1) / 5 * 100))
            
            df.to_excel(filepath, index=False)

        def on_export_complete():
            QMessageBox.information(self, "Exportación Exitosa", f"Datos exportados a {os.path.basename(filepath)}")

        def on_export_error(err):
            exctype, value, _ = err
            if isinstance(value, PermissionError):
                QMessageBox.critical(self, "Error de Permisos", "No se pudo guardar el archivo. Asegúrate de que no esté abierto en otro programa.")
            else:
                QMessageBox.critical(self, "Error de Exportación", f"No se pudo guardar el archivo Excel: {value}")

        worker = Worker(do_export, data, headers, filepath)
        worker.signals.progress.connect(lambda p: self.statusBar().showMessage(f"Exportando... {p}%"))
        worker.signals.finished.connect(on_export_complete)
        worker.signals.error.connect(on_export_error)
        worker.signals.finished.connect(lambda: self.statusBar().showMessage("Listo.", 3000))
        self.threadpool.start(worker)

    def generate_inventory_report(self):
        # ... (El resto del código para generar reportes y otras funciones permanece igual)
        pass

    def generate_productivity_charts(self):
        """Muestra un diálogo para los futuros gráficos de productividad."""
        dialog = ProductivityChartDialog(db, self)
        dialog.exec()

    def create_backup(self):
        """Crea una copia de seguridad de la base de datos en un hilo secundario."""
        
        def do_backup(db_path, signals):
            backup_path = create_database_backup(db_path, Config.BACKUP_DIR)
            return backup_path

        def on_backup_complete(backup_path):
            QMessageBox.information(
                self, 
                "Copia de Seguridad Creada", 
                f"Se ha creado una copia de seguridad en:\\n{backup_path}"
            )

        def on_backup_error(err):
            _, value, _ = err
            QMessageBox.critical(
                self, 
                "Error al Crear Copia de Seguridad", 
                f"No se pudo crear la copia de seguridad:\\n{value}"
            )

        self.start_long_running_task(do_backup, on_backup_complete, on_backup_error, Config.DB_NAME)

    def restore_from_backup(self):
        # ... (El resto del código para restaurar backups permanece igual)
        pass

if __name__ == "__main__":
    setup_environment()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
