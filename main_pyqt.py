# main_pyqt.py
import sys
import re
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTableView, QAbstractItemView, QHeaderView, QComboBox, 
    QLineEdit, QLabel, QStatusBar, QMessageBox, QFileDialog
)
from PyQt6.QtGui import QAction, QStandardItemModel, QStandardItem, QColor, QIcon
from PyQt6.QtCore import Qt, QSettings

# --- IMPORTACIONES DE TU LÓGICA EXISTENTE ---
# ¡La gran ventaja es que podemos reutilizar todo esto!
from config import Config
from logger import logger
from validators import Validator
from database_improved import Database
from file_utils import open_file
from pyqt_windows import EntryDialog, ManageEquipmentDialog

# --- INICIALIZACIÓN DEL ENTORNO (igual que antes) ---
db = None

def setup_environment():
    """Inicializa el entorno de la aplicación (BD, carpetas)."""
    global db
    db = Database(Config.DB_NAME)
    db.setup()
    logger.info("Entorno configurado correctamente para PyQt.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control de Equipos - Banco de Pruebas (PyQt)")
        self.setGeometry(100, 100, 1400, 750)

        # Cargar la configuración de la ventana
        self.load_settings()

        # --- Icono de la Aplicación ---
        app_icon_path = os.path.join('icons', 'app_icon.png')
        if os.path.exists(app_icon_path):
            self.setWindowIcon(QIcon(app_icon_path))

        # --- Barra de Herramientas (Toolbar) ---
        toolbar = self.addToolBar("Acciones Principales")
        
        # Acciones para la barra de herramientas
        action_new = QAction(QIcon(os.path.join('icons', 'new.png')), "Registrar Nuevo Equipo", self)
        action_new.triggered.connect(self.open_entry_window)
        toolbar.addAction(action_new)

        action_export = QAction(QIcon(os.path.join('icons', 'excel.png')), "Exportar a Excel", self)
        action_export.triggered.connect(self.export_to_excel)
        toolbar.addAction(action_export)

        action_report = QAction(QIcon(os.path.join('icons', 'pdf.png')), "Generar Informe", self)
        action_report.triggered.connect(self.generate_inventory_report)
        toolbar.addAction(action_report)

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
        self.search_input.textChanged.connect(self.refresh_table)
        filter_layout.addWidget(self.search_input)

        main_layout.addLayout(filter_layout)

        # --- Tabla de Equipos ---
        self.table_model = QStandardItemModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        
        # Configuración de la apariencia de la tabla
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # No editable
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # Seleccionar filas completas
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSortingEnabled(True)
        
        # Permitir que el modelo maneje el ordenamiento para un control más fino
        self.table_model.setSortRole(Qt.ItemDataRole.UserRole)
        self.table_view.sortByColumn(5, Qt.SortOrder.DescendingOrder) # Ordenar por fecha de entrada por defecto

        # Conectar doble clic
        self.table_view.doubleClicked.connect(self.on_double_click)

        main_layout.addWidget(self.table_view)

        # --- Barra de Estado ---
        self.setStatusBar(QStatusBar(self))

        self.refresh_table()

    def load_settings(self):
        """Carga la geometría de la ventana y el estado de la tabla."""
        settings = QSettings("YourCompany", "ControlEquipos")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        table_state = settings.value("main_table_state")
        if table_state:
            self.table_view.horizontalHeader().restoreState(table_state)

    def closeEvent(self, event):
        """Guarda la configuración al cerrar la aplicación."""
        settings = QSettings("YourCompany", "ControlEquipos")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("main_table_state", self.table_view.horizontalHeader().saveState())
        super().closeEvent(event)

    def refresh_table(self):
        """Limpia y recarga la tabla con datos de la BD, aplicando filtros."""
        self.table_model.clear()
        
        # Definir las cabeceras
        headers = ["OT", "Nombre", "PN", "SN", "Estado Entrada", "Fecha Entrada", "Estado Salida", "Fecha Cierre", "Inventario", "ID"]
        self.table_model.setHorizontalHeaderLabels(headers)
        
        search_term = self.search_input.text().strip()
        inv_filter = self.inventory_filter.currentText()

        # La misma consulta que ya tenías, ¡perfecto!
        query = """SELECT id, numero_ot, nombre_equipo, pn, sn, estado_entrada, 
                   fecha_entrada, estado_salida, fecha_cierre, inventario 
                   FROM equipos"""
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
                QStandardItem(str(row_data['fecha_entrada'] or "")),
                QStandardItem(str(row_data['estado_salida'] or "")),
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
        self.table_view.setColumnHidden(headers.index("ID"), True)
        
        # Ajustar el tamaño de las columnas al contenido antes de estirar la última
        self.table_view.resizeColumnsToContents()
        
        self.update_stats(len(records))

    def get_color_for_status(self, row_data):
        """Determina el color de la fila según el estado del equipo."""
        # Mapa de colores por estado: (background, foreground). Foreground es None para usar el color por defecto.
        STATUS_COLORS = {
            "Útil": (QColor("#fff3cd"), None),      # Amarillo claro
            "Reparable": (QColor("#d4edda"), None), # Verde claro
            "Baja": (QColor("#f8d7da"), None),      # Rojo claro
            "Stamby": (QColor("black"), QColor("white")), # Fondo negro, texto blanco
            "Litigio": (QColor("white"), None),     # Fondo blanco
            "Falto de material": (QColor("#cce5ff"), None), # Azul claro (mantenido)
            "Incompleto": (QColor("#fdebd0"), None) # Naranja claro (mantenido)
        }
        
        if not row_data['inventario']:
            return QColor("#f0f0f0"), None # Gris muy claro para fuera de inventario

        status = row_data['estado_salida'] or row_data['estado_entrada']
        
        # .get(status, (None, None)) para devolver colores nulos si el estado no está en el mapa
        bg_color, fg_color = STATUS_COLORS.get(status, (None, None))
        
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
        id_item = self.table_model.item(index.row(), 9)
        record_id = int(id_item.text())
        dialog = ManageEquipmentDialog(db, record_id, self)
        dialog.data_changed.connect(self.refresh_table) # Si algo cambia, refresca la tabla
        dialog.exec()

    def open_entry_window(self):
        """Abre el diálogo para registrar un nuevo equipo."""
        dialog = EntryDialog(db, self) # Pasamos la sesión de BD y el parent
        if dialog.exec(): # .exec() retorna True si se llamó a .accept()
            self.refresh_table()

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

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        # Extraer datos del modelo de la tabla
        headers = [self.table_model.horizontalHeaderItem(i).text() for i in range(self.table_model.columnCount()) if not self.table_view.isColumnHidden(i)]
        data = []
        for row in range(self.table_model.rowCount()):
            row_data = [self.table_model.item(row, col).text() for col in range(self.table_model.columnCount()) if not self.table_view.isColumnHidden(col)]
            data.append(row_data)

        df = pd.DataFrame(data, columns=headers)

        try:
            df.to_excel(filepath, index=False)
            QMessageBox.information(self, "Exportación Exitosa", f"Datos exportados a {os.path.basename(filepath)}")
        except PermissionError:
            QMessageBox.critical(self, "Error de Permisos", f"No se pudo guardar el archivo. Asegúrate de que no esté abierto en otro programa.")
        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo guardar el archivo Excel: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def generate_inventory_report(self):
        """Genera un informe en PDF de los equipos en inventario."""
        try:
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_LEFT
            import json
        except ImportError:
            QMessageBox.critical(self, "Librería no encontrada", "Se necesita 'reportlab' para generar informes.\nInstala con: py -m pip install reportlab")
            return

        records = db.fetch_query("""
            SELECT numero_ot, nombre_equipo, pn, sn, estado_salida, log_trabajo 
            FROM equipos WHERE inventario = 1 ORDER BY fecha_entrada DESC
        """)

        if not records:
            QMessageBox.information(self, "Sin datos", "No hay equipos en inventario para generar un informe.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Guardar Informe PDF", "", "Archivos PDF (*.pdf)")
        if not filepath:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

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

        try:
            doc.build(story)
            QMessageBox.information(self, "Informe Generado", f"El informe ha sido guardado en:\n{os.path.basename(filepath)}")
        finally:
            QApplication.restoreOverrideCursor()


if __name__ == "__main__":
    # Configurar el entorno antes de crear la aplicación
    setup_environment()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())