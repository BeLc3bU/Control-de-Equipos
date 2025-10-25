# pyqt_windows.py
import os
import json
import textwrap
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QComboBox, QTextEdit, QPushButton, QLabel,
    QFileDialog, QMessageBox, QTabWidget, QWidget, QListWidget, QStatusBar, QDateEdit, QMenu,
    QTableView, QAbstractItemView, QHeaderView, QCheckBox, QDialogButtonBox
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal, QDate

# --- IMPORTACIONES DE LÓGICA ---
from config import Config
from logger import logger
from validators import Validator
from file_utils import copy_document, open_file
from email_utils import send_email_notification

# --- IMPORTACIONES PARA GRÁFICOS (con verificación) ---
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# =================================================================================
# DIÁLOGO DE ENTRADA DE NUEVO EQUIPO
# =================================================================================
class EntryDialog(QDialog):
    """Ventana de diálogo para registrar un nuevo equipo."""
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Registrar Nuevo Equipo")
        self.setMinimumWidth(500)
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.entries = {}
        self.entries["nombre_equipo"] = QComboBox()
        self.entries["nombre_equipo"].setEditable(True)
        self.load_existing_equipment_names()
        form_layout.addRow("Nombre Equipo:", self.entries["nombre_equipo"])

        line_edit_fields = {
            "PN (Part Number):": "pn", "SN (Serial Number):": "sn",
            "Nº OT (Orden Técnica):": "numero_ot", "Nº DR (Defect Report):": "defect_report"
        }
        for label_text, key in line_edit_fields.items():
            self.entries[key] = QLineEdit()
            form_layout.addRow(label_text, self.entries[key])

        self.estado_entrada_combo = QComboBox()
        self.estado_entrada_combo.addItems(["Útil", "Reparable", "Litigio", "Baja"])
        self.estado_entrada_combo.setCurrentText("Reparable")
        form_layout.addRow("Estado de Entrada:", self.estado_entrada_combo)

        self.obs_entrada_text = QTextEdit()
        self.obs_entrada_text.setFixedHeight(80)
        form_layout.addRow("Observaciones Entrada:", self.obs_entrada_text)

        doc_layout = QHBoxLayout()
        self.doc_path_label = QLineEdit()
        self.doc_path_label.setReadOnly(True)
        self.doc_path_label.setPlaceholderText("Ningún archivo seleccionado")
        doc_button = QPushButton("...")
        doc_button.setFixedWidth(30)
        doc_button.clicked.connect(self.select_document)
        doc_layout.addWidget(self.doc_path_label)
        doc_layout.addWidget(doc_button)
        form_layout.addRow("Documento SL2000:", doc_layout)
        main_layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_entry)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar Entrada")
        main_layout.addWidget(button_box)
        self.save_button = button_box.button(QDialogButtonBox.StandardButton.Save)


        self.entries["pn"].textChanged.connect(self.validate_form)
        self.entries["sn"].textChanged.connect(self.validate_form)
        self.entries["numero_ot"].textChanged.connect(self.validate_form)
        self.entries["pn"].editingFinished.connect(self.autocomplete_from_pn)
        self.validate_form()
        self.entries["nombre_equipo"].lineEdit().setFocus()

    def load_existing_equipment_names(self):
        query = "SELECT DISTINCT nombre_equipo FROM equipos ORDER BY nombre_equipo"
        records = self.db.fetch_query(query)
        if records:
            self.entries["nombre_equipo"].addItems([r['nombre_equipo'] for r in records])

    def autocomplete_from_pn(self):
        pn = self.entries["pn"].text().strip()
        if pn:
            result = self.db.fetch_query("SELECT nombre_equipo FROM equipos WHERE pn = ? ORDER BY fecha_entrada DESC LIMIT 1", (pn,), one=True)
            if result:
                self.entries["nombre_equipo"].setCurrentText(result['nombre_equipo'])

    def validate_form(self):
        pn_valid, _ = Validator.validate_pn(self.entries["pn"].text())
        sn_valid, _ = Validator.validate_sn(self.entries["sn"].text())
        ot_valid, _ = Validator.validate_ot(self.entries["numero_ot"].text())
        all_valid = pn_valid and sn_valid and ot_valid
        self.save_button.setEnabled(all_valid)
        self.entries["pn"].setStyleSheet("border: 1px solid red;" if not pn_valid and self.entries["pn"].text() else "")
        self.entries["sn"].setStyleSheet("border: 1px solid red;" if not sn_valid and self.entries["sn"].text() else "")
        self.entries["numero_ot"].setStyleSheet("border: 1px solid red;" if not ot_valid and self.entries["numero_ot"].text() else "")

    def select_document(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar documento SL2000")
        if path: self.doc_path_label.setText(path)

    def save_entry(self):
        data = {k: e.text().strip() if isinstance(e, QLineEdit) else e.currentText().strip() for k, e in self.entries.items()}
        if self.db.fetch_query("SELECT id FROM equipos WHERE numero_ot = ?", (data["numero_ot"],), one=True):
            QMessageBox.critical(self, "Error de Duplicado", f"La Orden Técnica '{data['numero_ot']}' ya existe.")
            return

        arising_count_row = self.db.fetch_query("SELECT COUNT(*) FROM equipos WHERE pn = ? AND sn = ?", (data["pn"], data["sn"]), one=True)
        arising_count = arising_count_row[0] if arising_count_row else 0
        safe_name = "".join(c for c in data["nombre_equipo"] if c.isalnum() or c in (' ', '_')).rstrip()
        doc_folder_path = os.path.join(Config.DOCS_BASE_DIR, safe_name, data["sn"], f"Arising{arising_count:02d}")
        doc_target_path = copy_document(self.doc_path_label.text(), doc_folder_path)

        query = """INSERT INTO equipos (nombre_equipo, pn, sn, numero_ot, defect_report, estado_entrada, obs_entrada, doc_entrada, fecha_entrada, cerrado, inventario, doc_folder_path)
                   VALUES (:nombre_equipo, :pn, :sn, :numero_ot, :defect_report, :estado_entrada, :obs_entrada, :doc_entrada, :fecha_entrada, 0, 1, :doc_folder_path)"""
        params = {**data, "estado_entrada": self.estado_entrada_combo.currentText(), "obs_entrada": self.obs_entrada_text.toPlainText().strip(),
                  "doc_entrada": doc_target_path, "fecha_entrada": datetime.now().strftime("%Y-%m-%d %H:%M"), "doc_folder_path": doc_folder_path}

        if self.db.execute_query(query, params) is not None:
            QMessageBox.information(self, "Éxito", "Equipo registrado correctamente.")
            self.accept()
        else:
            logger.error("Falló el registro del equipo.")

# =================================================================================
# DIÁLOGO DE SOLICITUD DE MATERIAL
# =================================================================================
class MaterialRequestDialog(QDialog):
    """Diálogo para generar un correo de solicitud de material."""
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setWindowTitle("Solicitud de Material")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Se abrirá la aplicación de correo para enviar la solicitud."))
        
        self.material_text = QTextEdit()
        self.material_text.setPlaceholderText("Introduce aquí la lista de material necesario...")
        layout.addWidget(self.material_text)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.generate_email)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def generate_email(self):
        material_list = self.material_text.toPlainText().strip()
        if not material_list:
            QMessageBox.warning(self, "Campo Vacío", "Por favor, introduce el material requerido.")
            return

        subject = f"Solicitud de Material para OT: {self.data.get('numero_ot', 'N/A')}"
        body = (
            f"Estimados,\n\n"
            f"Se solicita el siguiente material para el equipo:\n"
            f"  - Nombre: {self.data.get('nombre_equipo', 'N/A')}\n"
            f"  - PN: {self.data.get('pn', 'N/A')}\n"
            f"  - SN: {self.data.get('sn', 'N/A')}\n"
            f"  - OT: {self.data.get('numero_ot', 'N/A')}\n\n"
            f"Material Requerido:\n"
            f"-------------------\n"
            f"{material_list}\n\n"
            f"Gracias y un saludo."
        )
        
        send_email_notification(subject, body, Config.EMAIL_RECIPIENT)
        self.accept()


# =================================================================================
# PESTAÑAS PARA EL DIÁLOGO DE GESTIÓN
# =================================================================================

class InfoTab(QWidget):
    """Pestaña de Información General y Documentos."""
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        fields = [
            ("ID:", self.data.get('id')),
            ("Nombre:", self.data.get('nombre_equipo')),
            ("PN / SN:", f"{self.data.get('pn')} / {self.data.get('sn')}"),
            ("Estado Entrada:", self.data.get('estado_entrada')),
            ("Fecha Entrada:", self.data.get('fecha_entrada')),
            ("Nº OT / Nº DR:", f"{self.data.get('numero_ot')} / {self.data.get('defect_report') or 'N/A'}")
        ]
        for label, value in fields:
            form_layout.addRow(QLabel(f"<b>{label}</b>"), QLabel(str(value or '')))

        obs_entrada = QTextEdit(self.data.get('obs_entrada', ''))
        obs_entrada.setReadOnly(True)
        form_layout.addRow(QLabel("<b>Obs. Entrada:</b>"), obs_entrada)

        vale_status = "✅ Disponible" if self.data.get('vale_devolucion') == "1" else "❌ No disponible"
        form_layout.addRow(QLabel("<b>Vale de Devolución:</b>"), QLabel(vale_status))
        layout.addLayout(form_layout)

        layout.addWidget(QLabel("<b>Documentos (doble clic para abrir):</b>"))
        self.docs_list = QListWidget()
        self.docs_list.doubleClicked.connect(self.open_selected_document)
        self.docs_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.docs_list.customContextMenuRequested.connect(self.show_docs_menu)
        layout.addWidget(self.docs_list)
        self.refresh_docs_list()

    def show_docs_menu(self, position):
        item = self.docs_list.itemAt(position)
        if not item: return
        menu = QMenu()
        open_action = menu.addAction("Abrir Archivo")
        open_folder_action = menu.addAction("Abrir Carpeta Contenedora")
        action = menu.exec(self.docs_list.mapToGlobal(position))
        if action == open_action: open_file(item.text())
        elif action == open_folder_action: open_file(os.path.dirname(item.text()))

    def refresh_docs_list(self):
        self.docs_list.clear()
        doc_keys = ['doc_entrada', 'certificado_cat', 'defect_report_final']
        all_docs = [self.data[key] for key in doc_keys if self.data.get(key)]
        all_docs.extend(json.loads(self.data.get('fotos') or '[]'))
        for doc_path in all_docs:
            if doc_path: self.docs_list.addItem(doc_path)

    def open_selected_document(self):
        if item := self.docs_list.currentItem(): open_file(item.text())

    def update_data(self, new_data):
        self.data = new_data
        # Simple refresh by recreating UI
        while self.layout().count():
            child = self.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.init_ui()


class WorkTab(QWidget):
    """Pestaña de Trabajo, Historial y Archivos."""
    data_saved = pyqtSignal()
    ALLOWED_COLUMNS_TO_UPDATE = ['estado_salida', 'obs_salida', 'fotos', 'log_trabajo']

    def __init__(self, db_session, data, parent=None):
        super().__init__(parent)
        self.db, self.data = db_session, data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Historial de Intervenciones:</b>"))
        self.log_model = QStandardItemModel()
        self.log_view = QTableView()
        self.log_view.setModel(self.log_model)
        self.log_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.log_view.horizontalHeader().setStretchLastSection(True)
        self.log_view.verticalHeader().setVisible(False)
        layout.addWidget(self.log_view)
        self.refresh_log_table()

        log_entry_layout = QHBoxLayout()
        self.new_log_entry = QTextEdit()
        self.new_log_entry.setPlaceholderText("Escribe una nueva intervención...")
        self.new_log_entry.setFixedHeight(60)
        add_log_button = QPushButton("Añadir al Historial")
        add_log_button.clicked.connect(self.save_log_entry)
        log_entry_layout.addWidget(self.new_log_entry)
        log_entry_layout.addWidget(add_log_button)
        layout.addLayout(log_entry_layout)

        work_form = QFormLayout()
        self.estado_salida_combo = QComboBox()
        self.estado_salida_combo.addItems(["", "Útil", "Reparable", "Stamby", "Falto de material", "Baja", "Incompleto"])
        self.estado_salida_combo.setCurrentText(self.data.get('estado_salida', ''))
        work_form.addRow("Estado de Salida:", self.estado_salida_combo)
        self.obs_salida_text = QTextEdit(self.data.get('obs_salida', ''))
        work_form.addRow("Obs. de Salida:", self.obs_salida_text)
        layout.addLayout(work_form)

        bottom_layout = QHBoxLayout()
        btn_fotos = QPushButton("Añadir Fotos")
        btn_fotos.clicked.connect(self.add_photos)
        material_button = QPushButton("Solicitar Material")
        material_button.clicked.connect(self.open_material_request)
        save_work_button = QPushButton("Guardar Cambios")
        save_work_button.clicked.connect(self.save_work_changes)
        
        bottom_layout.addWidget(btn_fotos)
        bottom_layout.addWidget(material_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(save_work_button)
        layout.addLayout(bottom_layout)

    def add_photos(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Seleccionar Fotos", filter="Imágenes (*.jpg *.jpeg *.png)")
        if not paths: return
        current_files = json.loads(self.data.get('fotos') or '[]')
        folder_path = self.data.get('doc_folder_path')
        if not folder_path:
             QMessageBox.warning(self, "Error", "La carpeta de documentos para este registro no existe.")
             return
        for path in paths:
            if new_path := copy_document(path, folder_path):
                if new_path not in current_files:
                    current_files.append(new_path)
        self.update_fields_in_db(['fotos'], [json.dumps(current_files)])

    def refresh_log_table(self):
        self.log_model.clear()
        self.log_model.setHorizontalHeaderLabels(["Fecha", "Intervención"])
        try:
            log_entries = json.loads(self.data.get('log_trabajo') or '[]')
            for entry in log_entries:
                self.log_model.appendRow([QStandardItem(entry.get("timestamp", "")), QStandardItem(entry.get("entry", ""))])
        except (json.JSONDecodeError, TypeError):
            if log := self.data.get('log_trabajo'):
                self.log_model.appendRow([QStandardItem("Historial Antiguo"), QStandardItem(log)])
        self.log_view.resizeColumnsToContents()

    def save_work_changes(self):
        self.update_fields_in_db(['estado_salida', 'obs_salida'], [self.estado_salida_combo.currentText(), self.obs_salida_text.toPlainText().strip()])

    def save_log_entry(self):
        if not (new_entry := self.new_log_entry.toHtml().strip()): return # Guardar como HTML
        try:
            log_list = json.loads(self.data.get('log_trabajo') or '[]')
        except (json.JSONDecodeError, TypeError):
            log_list = [{"timestamp": "Historial Antiguo", "entry": self.data.get('log_trabajo', '')}] if self.data.get('log_trabajo') else []
        log_list.insert(0, {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "entry": new_entry})
        self.update_fields_in_db(['log_trabajo'], [json.dumps(log_list, indent=2)])
        self.new_log_entry.clear()

    def open_material_request(self):
        dialog = MaterialRequestDialog(self.data, self)
        dialog.exec()

    def update_fields_in_db(self, fields, values):
        """Función de actualización segura con validación de columnas."""
        for f in fields:
            if f not in self.ALLOWED_COLUMNS_TO_UPDATE:
                QMessageBox.critical(self, "Error de Seguridad", f"Intento de modificar columna no permitida: {f}")
                return
        set_clause = ", ".join([f"{f} = ?" for f in fields])
        query = f"UPDATE equipos SET {set_clause} WHERE id = ?"
        if self.db.execute_query(query, tuple(values) + (self.data['id'],)):
            self.data_saved.emit() # Notificar que los datos se han guardado

    def update_data(self, new_data):
        self.data = new_data
        self.estado_salida_combo.setCurrentText(self.data.get('estado_salida', ''))
        self.obs_salida_text.setPlainText(self.data.get('obs_salida', ''))
        self.refresh_log_table()


class CloseTab(QWidget):
    """Pestaña para el cierre del equipo."""
    data_changed = pyqtSignal()
    def __init__(self, db_session, data, parent=None):
        super().__init__(parent)
        self.db, self.data = db_session, data
        self.init_ui()

    def init_ui(self):
        self.setLayout(QVBoxLayout())
        self.setup_ui_for_state()

    def setup_ui_for_state(self):
        is_closed = bool(self.data.get('cerrado'))
        while self.layout().count():
            child = self.layout().takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        if is_closed:
            self.layout().addWidget(QLabel(f"<b>Equipo cerrado el {self.data.get('fecha_cierre', 'N/A')}</b>"))
            reopen_button = QPushButton("Reabrir Equipo")
            reopen_button.clicked.connect(self.reopen_equipment)
            self.layout().addWidget(reopen_button)
        else:
            form_layout = QFormLayout()
            self.close_entries = { "destino": QLineEdit(self.data.get('destino', '')), "horas_trabajo": QLineEdit(str(self.data.get('horas_trabajo', ''))) }
            form_layout.addRow("Destino:", self.close_entries["destino"])
            form_layout.addRow("Horas de Trabajo:", self.close_entries["horas_trabajo"])
            self.contenedor_check = QCheckBox("Sí")
            self.contenedor_check.setChecked(bool(self.data.get('contenedor')))
            form_layout.addRow("Contenedor:", self.contenedor_check)
            self.obs_cierre_text = QTextEdit(self.data.get('obs_cierre', ''))
            form_layout.addRow("Obs. Cierre:", self.obs_cierre_text)
            self.layout().addLayout(form_layout)
            
            save_close_button = QPushButton("Guardar y Cerrar Equipo")
            save_close_button.clicked.connect(self.save_and_close)
            self.layout().addWidget(save_close_button)

    def save_and_close(self):
        query = "UPDATE equipos SET cerrado = 1, fecha_cierre = ?, destino = ?, horas_trabajo = ?, obs_cierre = ?, contenedor = ? WHERE id = ?"
        params = (datetime.now().strftime("%Y-%m-%d %H:%M"), self.close_entries['destino'].text(), self.close_entries['horas_trabajo'].text(),
                  self.obs_cierre_text.toPlainText(), self.contenedor_check.isChecked(), self.data['id'])
        if self.db.execute_query(query, params):
            self.data_changed.emit()

    def reopen_equipment(self):
        if self.db.execute_query("UPDATE equipos SET cerrado = 0, fecha_cierre = NULL WHERE id = ?", (self.data['id'],)):
            self.data_changed.emit()

    def update_data(self, new_data):
        self.data = new_data
        self.setup_ui_for_state()


# =================================================================================
# DIÁLOGO PRINCIPAL DE GESTIÓN
# =================================================================================
class ManageEquipmentDialog(QDialog):
    """Diálogo principal para gestionar un equipo existente, con pestañas."""
    data_changed = pyqtSignal()

    def __init__(self, db_session, record_id, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.record_id = record_id
        
        self.load_data()
        self.setWindowTitle(f"Gestionar: {self.data.get('nombre_equipo', 'N/A')} (ID: {self.record_id})")
        self.setMinimumSize(800, 600)

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # Crear e añadir pestañas
        self.info_tab = InfoTab(self.data)
        self.work_tab = WorkTab(self.db, self.data)
        self.close_tab = CloseTab(self.db, self.data)
        self.tabs.addTab(self.info_tab, "Información y Documentos")
        self.tabs.addTab(self.work_tab, "Trabajo e Historial")
        self.tabs.addTab(self.close_tab, "Cierre y Salida")
        main_layout.addWidget(self.tabs)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        # Conectar señales
        self.work_tab.data_saved.connect(self.refresh_all_tabs)
        self.close_tab.data_changed.connect(self.refresh_all_tabs)
        if parent: self.data_changed.connect(parent.refresh_table)

    def load_data(self):
        """Carga/Recarga los datos del equipo desde la BD."""
        data = self.db.fetch_query("SELECT * FROM equipos WHERE id = ?", (self.record_id,), one=True)
        if not data:
            QMessageBox.critical(self, "Error", "El registro ya no existe.")
            self.reject()
            return
        self.data = dict(data) # Convertir a dict para poder modificarlo

    def refresh_all_tabs(self):
        """Recarga los datos y notifica a todas las pestañas para que se actualicen."""
        logger.info(f"Refrescando datos para el equipo ID: {self.record_id}")
        self.load_data()
        self.info_tab.update_data(self.data)
        self.work_tab.update_data(self.data)
        self.close_tab.update_data(self.data)
        self.data_changed.emit()


# =================================================================================
# DIÁLOGO DE GRÁFICOS DE PRODUCTIVIDAD
# =================================================================================
class ProductivityChartDialog(QDialog):
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Gráficos de Productividad")
        self.setMinimumSize(1000, 700)

        if not MATPLOTLIB_AVAILABLE:
            self.setLayout(QVBoxLayout())
            self.layout().addWidget(QLabel("Error: Matplotlib no está instalado.\nPor favor, ejecute: pip install matplotlib pandas"))
            return

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.figure = plt.figure(figsize=(15, 10), constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        toolbar = NavigationToolbar(self.canvas, self)

        # Controles de Fecha
        date_filter_layout = QHBoxLayout()
        self.start_date_edit = QDateEdit(QDate.currentDate().addMonths(-6))
        self.end_date_edit = QDateEdit(QDate.currentDate())
        self.start_date_edit.setCalendarPopup(True)
        self.end_date_edit.setCalendarPopup(True)
        plot_button = QPushButton("Actualizar Gráficos")
        plot_button.clicked.connect(self.plot_charts)

        date_filter_layout.addWidget(QLabel("Desde:"))
        date_filter_layout.addWidget(self.start_date_edit)
        date_filter_layout.addWidget(QLabel("Hasta:"))
        date_filter_layout.addWidget(self.end_date_edit)
        date_filter_layout.addWidget(plot_button)
        date_filter_layout.addStretch()

        layout.addLayout(date_filter_layout)
        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)
        
        self.plot_charts()

    def plot_charts(self):
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        query = "SELECT fecha_entrada, fecha_cierre, horas_trabajo, estado_salida FROM equipos WHERE cerrado = 1 AND fecha_cierre BETWEEN ? AND ?"
        records = self.db.fetch_query(query, (start_date, end_date))
        if not records:
            self.figure.clear()
            self.figure.text(0.5, 0.5, 'No hay datos de equipos cerrados en el rango de fechas seleccionado.', ha='center', va='center')
            self.canvas.draw()
            return

        df = pd.DataFrame(records)
        df['fecha_cierre'] = pd.to_datetime(df['fecha_cierre'])
        df['fecha_entrada'] = pd.to_datetime(df['fecha_entrada'])
        df['horas_trabajo'] = pd.to_numeric(df['horas_trabajo'], errors='coerce').fillna(0)

        self.figure.clear()
        
        # 1. Equipos cerrados por mes
        ax1 = self.figure.add_subplot(2, 2, 1)
        df.set_index('fecha_cierre').resample('M').size().plot(kind='bar', ax=ax1, rot=45)
        ax1.set_title('Rendimiento: Equipos Cerrados por Mes')
        ax1.set_xlabel('Mes')
        ax1.set_ylabel('Nº de Equipos')

        # 2. Distribución de estados de salida
        ax2 = self.figure.add_subplot(2, 2, 2)
        df['estado_salida'].value_counts().plot(kind='pie', ax=ax2, autopct='%1.1f%%', startangle=90)
        ax2.set_title('Resultados: Distribución de Estados de Salida')
        ax2.set_ylabel('') # Ocultar ylabel para tartas

        # 3. Tiempo de Ciclo (Turnaround Time)
        ax3 = self.figure.add_subplot(2, 2, 3)
        df['turnaround_days'] = (df['fecha_cierre'] - df['fecha_entrada']).dt.days
        avg_turnaround = df['turnaround_days'].mean()
        ax3.bar(['Promedio'], [avg_turnaround])
        ax3.set_title(f'Tiempo de Ciclo (Promedio: {avg_turnaround:.1f} días)')
        ax3.set_ylabel('Días')
        
        # 4. Histograma de horas de trabajo
        ax4 = self.figure.add_subplot(2, 2, 4)
        df[df['horas_trabajo'] > 0]['horas_trabajo'].plot(kind='hist', bins=15, ax=ax4)
        ax4.set_title('Complejidad: Horas de Trabajo por Reparación')
        ax4.set_xlabel('Horas')
        ax4.set_ylabel('Frecuencia')
        
        self.canvas.draw()
