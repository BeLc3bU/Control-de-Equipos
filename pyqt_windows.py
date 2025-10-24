# pyqt_windows.py
import os
import json
import textwrap
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QComboBox, QTextEdit, QPushButton, QLabel,
    QFileDialog, QMessageBox, QTabWidget, QWidget, QListWidget, QStatusBar, QDateEdit, QMenu,
    QTableView, QAbstractItemView, QHeaderView, QCheckBox
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal

# --- IMPORTACIONES DE TU LÓGICA EXISTENTE ---
from config import Config
from PyQt6.QtCore import QDate
from logger import logger
from validators import Validator
from file_utils import copy_document, open_file
from email_utils import send_email_notification

# --- Importaciones para Gráficos ---
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# La variable 'db' se pasará desde la ventana principal

class EntryDialog(QDialog):
    """Ventana de diálogo para registrar un nuevo equipo."""
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Registrar Nuevo Equipo")
        self.setMinimumWidth(500)
        self.setModal(True) # Bloquea la ventana principal mientras está abierta

        # --- Layouts ---
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Widgets del Formulario ---
        self.entries = {}
        
        # Mejora: QComboBox editable para Nombre Equipo
        self.entries["nombre_equipo"] = QComboBox()
        self.entries["nombre_equipo"].setEditable(True)
        self.load_existing_equipment_names()
        form_layout.addRow("Nombre Equipo:", self.entries["nombre_equipo"])

        line_edit_fields = {
            "PN (Part Number):": "pn",
            "SN (Serial Number):": "sn",
            "Nº OT (Orden Técnica):": "numero_ot",
            "Nº DR (Defect Report):": "defect_report"
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

        # Widget para seleccionar documento
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

        # --- Botones de Acción (Guardar/Cancelar) ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_button = QPushButton("Cancelar")
        cancel_button.setMinimumWidth(120)
        cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("Guardar Entrada")
        self.save_button.setDefault(True)
        self.save_button.setMinimumWidth(120)
        self.save_button.clicked.connect(self.save_entry)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)

        # --- Orden de Tabulación (Accesibilidad) ---
        self.setTabOrder(self.entries["nombre_equipo"], self.entries["pn"])
        self.setTabOrder(self.entries["pn"], self.entries["sn"])
        self.setTabOrder(self.entries["sn"], self.entries["numero_ot"])
        self.setTabOrder(self.entries["numero_ot"], self.entries["defect_report"])
        self.setTabOrder(self.entries["defect_report"], self.estado_entrada_combo)
        self.setTabOrder(self.estado_entrada_combo, self.obs_entrada_text)
        self.setTabOrder(self.obs_entrada_text, doc_button)
        self.setTabOrder(doc_button, self.save_button)
        self.setTabOrder(self.save_button, cancel_button)

        # --- Conexiones para Validación en Tiempo Real ---
        self.entries["pn"].textChanged.connect(self.validate_form)
        self.entries["sn"].textChanged.connect(self.validate_form)
        self.entries["numero_ot"].textChanged.connect(self.validate_form)
        self.entries["pn"].editingFinished.connect(self.autocomplete_from_pn)

        self.validate_form() # Llamada inicial para deshabilitar el botón

        # QoL: Poner el foco en el primer campo
        self.entries["nombre_equipo"].lineEdit().setFocus()

    def load_existing_equipment_names(self):
        """Carga nombres de equipo únicos desde la BD al QComboBox."""
        query = "SELECT DISTINCT nombre_equipo FROM equipos ORDER BY nombre_equipo"
        records = self.db.fetch_query(query)
        if records:
            names = [record['nombre_equipo'] for record in records]
            self.entries["nombre_equipo"].addItems(names)

    def autocomplete_from_pn(self):
        """Autocompleta el nombre del equipo basado en el PN introducido."""
        pn = self.entries["pn"].text().strip()
        if not pn:
            return
        
        query = "SELECT nombre_equipo FROM equipos WHERE pn = ? ORDER BY fecha_entrada DESC LIMIT 1"
        result = self.db.fetch_query(query, (pn,), one=True)
        
        if result:
            self.entries["nombre_equipo"].setCurrentText(result['nombre_equipo'])

    def validate_form(self):
        """Valida los campos obligatorios y actualiza la UI."""
        pn_valid, _ = Validator.validate_pn(self.entries["pn"].text())
        sn_valid, _ = Validator.validate_sn(self.entries["sn"].text())
        ot_valid, _ = Validator.validate_ot(self.entries["numero_ot"].text())

        # Estilo para PN
        self.entries["pn"].setStyleSheet("border: 1px solid red;" if not pn_valid and self.entries["pn"].text() else "")
        # Estilo para SN
        self.entries["sn"].setStyleSheet("border: 1px solid red;" if not sn_valid and self.entries["sn"].text() else "")
        # Estilo para OT
        self.entries["numero_ot"].setStyleSheet("border: 1px solid red;" if not ot_valid and self.entries["numero_ot"].text() else "")

        # Habilitar o deshabilitar el botón de guardar
        all_valid = pn_valid and sn_valid and ot_valid
        self.save_button.setEnabled(all_valid)

    def select_document(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar documento SL2000")
        if path:
            self.doc_path_label.setText(path)

    def save_entry(self):
        data = {key: entry.text().strip() if isinstance(entry, QLineEdit) else entry.currentText().strip() for key, entry in self.entries.items()}

        # --- VALIDACIÓN (reutilizando tu lógica) ---
        validations = {
            "pn": (Validator.validate_pn, data["pn"]),
            "sn": (Validator.validate_sn, data["sn"]),
            "numero_ot": (Validator.validate_ot, data["numero_ot"]),
        }

        for field, (validator, value) in validations.items():
            is_valid, error_msg = validator(value)
            if not is_valid:
                QMessageBox.critical(self, f"Error de Validación - {field.upper()}", error_msg)
                self.entries[field].setFocus()
                return

        if self.db.fetch_query("SELECT id FROM equipos WHERE numero_ot = ?", (data["numero_ot"],), one=True):
            QMessageBox.critical(self, "Error de Duplicado", f"La Orden Técnica '{data['numero_ot']}' ya existe.")
            self.entries["numero_ot"].setFocus()
            return

        # --- LÓGICA DE CARPETAS Y ARCHIVOS (reutilizando tu lógica) ---
        arising_count_row = self.db.fetch_query("SELECT COUNT(*) FROM equipos WHERE pn = ? AND sn = ?", (data["pn"], data["sn"]), one=True)
        arising_number = arising_count_row[0] if arising_count_row else 0
        
        arising_folder = f"Arising{arising_number:02d}"
        safe_equipo_nombre = "".join(c for c in data["nombre_equipo"] if c.isalnum() or c in (' ', '_')).rstrip()
        doc_folder_path = os.path.join(Config.DOCS_BASE_DIR, safe_equipo_nombre, data["sn"], arising_folder)

        doc_target_path = copy_document(self.doc_path_label.text(), doc_folder_path)

        # --- INSERCIÓN EN BASE DE DATOS (reutilizando tu lógica) ---
        query = """
        INSERT INTO equipos (
            nombre_equipo, pn, sn, numero_ot, defect_report, estado_entrada,
            obs_entrada, doc_entrada, fecha_entrada, cerrado, inventario, doc_folder_path
        )
        VALUES (:nombre_equipo, :pn, :sn, :numero_ot, :defect_report, :estado_entrada, :obs_entrada, :doc_entrada, :fecha_entrada, :cerrado, :inventario, :doc_folder_path)
        """
        params = {
            **data,
            "estado_entrada": self.estado_entrada_combo.currentText(),
            "obs_entrada": self.obs_entrada_text.toPlainText().strip(),
            "doc_entrada": doc_target_path,
            "fecha_entrada": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "cerrado": 0,
            "inventario": 1,
            "doc_folder_path": doc_folder_path
        }
        
        # Aquí usamos el objeto 'db' que pasamos al crear el diálogo
        if self.db.execute_query(query, params) is not None:
            QMessageBox.information(self, "Éxito", "Equipo registrado correctamente.")
            self.accept() # Cierra el diálogo y señala que la operación fue exitosa
        else:
            # El método execute_query ya muestra un QMessageBox en caso de error
            logger.error("Falló el registro del equipo, el error fue mostrado al usuario desde la clase Database.")


# =================================================================================
# PESTAÑAS REFACTORIZADAS PARA MANAGEEQUIPMENTDIALOG
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
            ("ID:", self.data['id']), ("Nombre:", self.data['nombre_equipo']),
            ("PN / SN:", f"{self.data['pn']} / {self.data['sn']}"),
            ("Estado Entrada:", self.data['estado_entrada']), ("Fecha Entrada:", self.data['fecha_entrada']),
            ("Nº OT / Nº DR:", f"{self.data['numero_ot']} / {self.data['defect_report'] or 'N/A'}")
        ]
        for label, value in fields:
            form_layout.addRow(QLabel(f"<b>{label}</b>"), QLabel(str(value)))
        
        obs_entrada = QTextEdit(self.data['obs_entrada'] or "")
        obs_entrada.setReadOnly(True)
        form_layout.addRow(QLabel("<b>Obs. Entrada:</b>"), obs_entrada)
        
        # Información del vale de devolución
        vale_status = "✅ Disponible" if self.data['vale_devolucion'] == "1" else "❌ No disponible"
        form_layout.addRow(QLabel("<b>Vale de Devolución:</b>"), QLabel(vale_status))
        
        layout.addLayout(form_layout)

        layout.addWidget(QLabel("<b>Documentos Adjuntos (doble clic para abrir):</b>"))
        self.docs_list = QListWidget()
        self.docs_list.doubleClicked.connect(self.open_selected_document)
        # Mejora: Menú contextual
        self.docs_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.docs_list.customContextMenuRequested.connect(self.show_docs_menu)
        layout.addWidget(self.docs_list)
        
        self.refresh_docs_list()

    def show_docs_menu(self, position):
        item = self.docs_list.itemAt(position)
        if not item:
            return

        menu = QMenu()
        open_action = menu.addAction("Abrir Archivo")
        open_folder_action = menu.addAction("Abrir Carpeta Contenedora")
        
        action = menu.exec(self.docs_list.mapToGlobal(position))

        if action == open_action:
            open_file(item.text())
        elif action == open_folder_action:
            folder_path = os.path.dirname(item.text())
            open_file(folder_path)

    def refresh_docs_list(self):
        self.docs_list.clear()
        all_docs = []
        if self.data['doc_entrada']: all_docs.append(self.data['doc_entrada'])
        all_docs.extend(json.loads(self.data['fotos'] or '[]'))
        if self.data['certificado_cat']: all_docs.append(self.data['certificado_cat'])
        if self.data['defect_report_final']: all_docs.append(self.data['defect_report_final'])
        # Nota: vale_devolucion ya no es un archivo, es un checkbox

        for doc_path in all_docs:
            if doc_path: self.docs_list.addItem(doc_path)

    def open_selected_document(self):
        selected_item = self.docs_list.currentItem()
        if selected_item:
            open_file(selected_item.text())

    def update_data(self, new_data):
        self.data = new_data
        self.refresh_docs_list()


class WorkTab(QWidget):
    """Pestaña de Trabajo, Historial y Archivos."""
    data_saved = pyqtSignal()

    def __init__(self, db_session, data, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.data = data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Historial de Intervenciones (primero)
        layout.addWidget(QLabel("<b>Historial de Intervenciones:</b>"))
        self.log_model = QStandardItemModel()
        self.log_view = QTableView()
        self.log_view.setModel(self.log_model)
        self.log_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.log_view.horizontalHeader().setStretchLastSection(True)
        self.log_view.verticalHeader().setVisible(False)
        layout.addWidget(self.log_view)
        self.refresh_log_table()

        # 2. Añadir nueva entrada al historial (segundo)
        log_entry_layout = QHBoxLayout()
        # Mejora: Permitir texto enriquecido
        self.new_log_entry = QTextEdit()
        self.new_log_entry.setAcceptRichText(True)
        self.new_log_entry.setPlaceholderText("Escribe una nueva intervención aquí...")
        self.new_log_entry.setFixedHeight(60)
        add_log_button = QPushButton("Añadir al Historial")
        add_log_button.clicked.connect(self.save_log_entry)
        log_entry_layout.addWidget(self.new_log_entry)
        log_entry_layout.addWidget(add_log_button)
        layout.addLayout(log_entry_layout)

        # 3 y 4. Estado y Observaciones de Salida
        work_form_layout = QFormLayout()
        self.estado_salida_combo = QComboBox()
        self.estado_salida_combo.addItems(["", "Útil", "Reparable", "Stamby", "Falto de material", "Baja", "Incompleto"])
        self.estado_salida_combo.setCurrentText(self.data['estado_salida'] or "")
        work_form_layout.addRow("Estado de Salida:", self.estado_salida_combo)

        self.obs_salida_text = QTextEdit(self.data['obs_salida'] or "")
        work_form_layout.addRow("Observaciones de Salida:", self.obs_salida_text)
        layout.addLayout(work_form_layout)

        # 5. Botones de acción agrupados al final
        bottom_layout = QHBoxLayout()

        btn_docs = QPushButton("Subir documentos escaneados")
        btn_docs.clicked.connect(lambda: self.add_files("Seleccionar documentos escaneados"))

        btn_fotos = QPushButton("Añadir Fotos")
        btn_fotos.clicked.connect(lambda: self.add_files("Seleccionar Fotos", [("Archivos de Imagen", "*.jpg *.jpeg *.png *.gif")]))

        material_button = QPushButton("Solicitar Material")
        material_button.clicked.connect(self.open_material_request)

        save_work_button = QPushButton("Guardar Cambios de Trabajo")
        save_work_button.clicked.connect(self.save_work_changes)

        bottom_layout.addWidget(btn_docs)
        bottom_layout.addWidget(btn_fotos)
        bottom_layout.addWidget(material_button)
        bottom_layout.addWidget(save_work_button)
        layout.addLayout(bottom_layout)

        # --- Orden de Tabulación ---
        self.setTabOrder(self.new_log_entry, add_log_button)
        self.setTabOrder(add_log_button, self.estado_salida_combo)
        self.setTabOrder(self.estado_salida_combo, self.obs_salida_text)
        self.setTabOrder(self.obs_salida_text, btn_docs)
        self.setTabOrder(btn_docs, btn_fotos)
        self.setTabOrder(btn_fotos, material_button)
        self.setTabOrder(material_button, save_work_button)

    def add_files(self, title, filetypes=None):
        file_filter = "Todos los archivos (*.*)"
        if filetypes:
            file_filter = ";;".join([f[0] + f" ({f[1]})" for f in filetypes])

        paths, _ = QFileDialog.getOpenFileNames(self, title, filter=file_filter)
        if not paths: return

        current_files = json.loads(self.data['fotos'] or '[]')
        for path in paths:
            new_path = copy_document(path, self.data['doc_folder_path'])
            if new_path and new_path not in current_files:
                current_files.append(new_path)
        
        self.update_field_in_db('fotos', json.dumps(current_files))

    def refresh_log_table(self):
        self.log_model.clear()
        self.log_model.setHorizontalHeaderLabels(["Fecha", "Intervención"])
        try:
            log_entries = json.loads(self.data['log_trabajo'] or '[]')
            for entry in log_entries:
                row = [QStandardItem(entry.get("timestamp", "")), QStandardItem(entry.get("entry", ""))]
                self.log_model.appendRow(row)
        except (json.JSONDecodeError, TypeError):
            if self.data['log_trabajo']:
                row = [QStandardItem("Historial Antiguo"), QStandardItem(self.data['log_trabajo'])]
                self.log_model.appendRow(row)
        self.log_view.resizeColumnsToContents()

    def save_work_changes(self):
        estado_salida = self.estado_salida_combo.currentText()
        obs_salida = self.obs_salida_text.toPlainText().strip()
        self.update_field_in_db(['estado_salida', 'obs_salida'], [estado_salida, obs_salida])

    def save_log_entry(self):
        new_entry = self.new_log_entry.toHtml().strip() # Mejora: Guardar como HTML
        if not new_entry: return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            current_log_list = json.loads(self.data['log_trabajo']) if self.data['log_trabajo'] else []
        except (json.JSONDecodeError, TypeError):
            current_log_list = [{"timestamp": "Fecha Antigua", "entry": self.data['log_trabajo'] or ""}]

        current_log_list.insert(0, {"timestamp": timestamp, "entry": new_entry})
        updated_log_json = json.dumps(current_log_list, indent=2)

        self.update_field_in_db('log_trabajo', updated_log_json)
        self.new_log_entry.clear() # Limpiar el campo después de guardar

    def open_material_request(self):
        dialog = MaterialRequestDialog(self.data, self)
        dialog.exec()

    def update_field_in_db(self, field_name, value):
        if isinstance(field_name, list):
            set_clause = ", ".join([f"{name} = ?" for name in field_name])
            params = (*value, self.data['id'])
        else:
            set_clause = f"{field_name} = ?"
            params = (value, self.data['id'])

        query = f"UPDATE equipos SET {set_clause} WHERE id = ?"
        if self.db.execute_query(query, params) is not None:
            # No mostramos pop-up para cada guardado, la señal es suficiente feedback
            self.data_saved.emit()

    def update_data(self, new_data):
        self.data = new_data
        self.estado_salida_combo.setCurrentText(self.data['estado_salida'] or "")
        self.obs_salida_text.setPlainText(self.data['obs_salida'] or "")
        self.refresh_log_table()


class CloseTab(QWidget):
    """Pestaña para el cierre del equipo y la documentación final."""
    data_changed = pyqtSignal()

    def __init__(self, db_session, data, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.data = data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        is_closed = bool(self.data['cerrado'])

        form_layout = QFormLayout()
        self.close_entries = {}
        fields = {"Destino:": "destino", "Horas de Trabajo:": "horas_trabajo"}
        for label, key in fields.items():
            entry = QLineEdit(str(self.data[key] or ""))
            entry.setDisabled(is_closed)
            self.close_entries[key] = entry
            form_layout.addRow(label, entry)

        self.contenedor_check = QCheckBox("Sí")
        self.contenedor_check.setChecked(bool(self.data['contenedor']))
        self.contenedor_check.setDisabled(is_closed)
        form_layout.addRow("Contenedor:", self.contenedor_check)

        self.obs_cierre_text = QTextEdit(self.data['obs_cierre'] or "")
        self.obs_cierre_text.setDisabled(is_closed)
        form_layout.addRow("Obs. Cierre:", self.obs_cierre_text)

        # Guardar referencia al layout del formulario para poder modificarlo
        self.form_layout = form_layout

        layout.addLayout(form_layout)

        # --- Botones de Acción ---
        action_layout = QHBoxLayout()
        self.closed_label = QLabel()
        layout.addWidget(self.closed_label)

        self.save_close_button = QPushButton("Guardar y Cerrar Equipo")
        self.save_close_button.setMinimumWidth(200)
        self.save_close_button.clicked.connect(self.save_and_close)
        action_layout.addWidget(self.save_close_button)

        self.send_email_button = QPushButton("Enviar Notificación de Cierre")
        self.send_email_button.setMinimumWidth(200)
        self.send_email_button.clicked.connect(lambda: self.send_close_email())
        action_layout.addWidget(self.send_email_button)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Nota informativa sobre documentación final
        info_label = QLabel("<b>Nota:</b> La documentación final (CAT/DR) y el vale de devolución se gestionan en la pestaña 'Salida de Inventario'.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)

        # --- Orden de Tabulación ---
        if not is_closed:
            self.setTabOrder(self.close_entries["destino"], self.close_entries["horas_trabajo"])
            self.setTabOrder(self.close_entries["horas_trabajo"], self.contenedor_check)
            self.setTabOrder(self.contenedor_check, self.obs_cierre_text)
            self.setTabOrder(self.obs_cierre_text, self.save_close_button)
            self.setTabOrder(self.save_close_button, self.send_email_button)

        layout.addStretch()
        
        self.update_ui_state() # Llamada inicial para establecer la visibilidad correcta
        self._update_field_states() # Llamada inicial para el estado de los campos

    def save_and_close(self):
        if not self.data['estado_salida']:
            QMessageBox.critical(self, "Validación Fallida", "Debe definir un 'Estado de Salida' en la pestaña 'Trabajo'.")
            return
        
        data_to_save = {key: entry.text().strip() for key, entry in self.close_entries.items()}
        
        is_valid_hours, hours_error = Validator.validate_hours(data_to_save['horas_trabajo'])
        if not is_valid_hours:
            QMessageBox.critical(self, "Validación Fallida", f"Horas de trabajo no válidas: {hours_error}")
            return
        
        # La conversión se hace después de la validación para evitar errores
        params = {
            "destino": data_to_save['destino'],
            "horas_trabajo": float(data_to_save['horas_trabajo']) if data_to_save['horas_trabajo'] else None,
            "contenedor": 1 if self.contenedor_check.isChecked() else 0,
            "obs_cierre": self.obs_cierre_text.toPlainText().strip(),
            "cerrado": 1,
            "fecha_cierre": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "id": self.data['id']
        }

        query = """UPDATE equipos SET 
                   destino = :destino, horas_trabajo = :horas_trabajo, contenedor = :contenedor, 
                   obs_cierre = :obs_cierre, cerrado = :cerrado, fecha_cierre = :fecha_cierre
                   WHERE id = :id"""

        if self.db.execute_query(query, params) is not None:
            QMessageBox.information(self, "Éxito", "Equipo cerrado correctamente.")
            reply = QMessageBox.question(self, "Enviar Notificación", "¿Desea enviar la notificación de cierre por correo ahora?")
            if reply == QMessageBox.StandardButton.Yes:
                self.send_close_email(updated_data=params) # Pasamos los datos actualizados
            self.data_changed.emit()

    def send_close_email(self, updated_data=None):
        # Si no se pasan datos actualizados, carga los de la BD
        if updated_data is None:
            email_data = self.data
        else:
            email_data = {**dict(self.data), **updated_data}

        if not email_data['cerrado']:
            QMessageBox.warning(self, "Equipo no cerrado", "Debe guardar y cerrar el equipo antes de enviar la notificación.")
            return
        
        subject = f"Cierre de Equipo - OT {email_data['numero_ot']} - SN {email_data['sn']}"
        body = "\n".join([
            "Buenas,", "", "Se adjunta la información referente al cierre del siguiente equipo:", "",
            f"  - Orden Técnica: {email_data['numero_ot']}",
            f"  - Nombre del Equipo: {email_data['nombre_equipo']}",
            f"  - PN / SN: {email_data['pn']} / {email_data['sn']}",
            f"  - Horas de Trabajo: {email_data['horas_trabajo'] or 'N/A'}",
            f"  - Estado de Salida: {email_data['estado_salida']}",
            f"  - Observaciones Cierre: {email_data['obs_cierre'] or 'Ninguna'}",
            (f"  - Destino: {email_data['destino'] or 'No especificado'}" if email_data['estado_salida'] == 'Reparable' else ""),
            "", "Un saludo.", "", "---", "Este es un mensaje generado automáticamente."
        ])
        send_email_notification(subject, body)


    def update_data(self, new_data):
        self.data = new_data
        is_closed = bool(self.data['cerrado'])

        # Actualizar el estado de los widgets existentes en lugar de reconstruir
        for key, entry in self.close_entries.items():
            entry.setText(str(self.data[key] or ""))
            entry.setDisabled(is_closed)

        self.contenedor_check.setChecked(bool(self.data['contenedor']))
        self.contenedor_check.setDisabled(is_closed)
        self.obs_cierre_text.setPlainText(self.data['obs_cierre'] or "")
        self.obs_cierre_text.setDisabled(is_closed)

        self._update_field_states()
        self.update_ui_state()
        
    def update_ui_state(self):
        """Actualiza la visibilidad de los widgets según el estado de cierre."""
        is_closed = bool(self.data['cerrado'])
        self.save_close_button.setVisible(not is_closed)
        self.closed_label.setText(f"<b>Equipo cerrado el: {self.data['fecha_cierre']}</b>" if is_closed else "")
        self.closed_label.setVisible(is_closed)

    def _update_field_states(self):
        """Habilita o deshabilita campos específicos según la lógica de negocio."""
        is_closed = bool(self.data['cerrado'])
        is_reparable = self.data['estado_salida'] == 'Reparable'

        # El campo 'destino' solo es editable si el equipo no está cerrado Y su estado es 'Reparable'
        self.close_entries['destino'].setDisabled(is_closed or not is_reparable)



class ExitTab(QWidget):
    """Pestaña para gestionar la documentación final y salida del equipo del inventario."""
    data_changed = pyqtSignal()

    def __init__(self, db_session, data, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.data = data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Información del estado actual
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        # Sección de documentación final
        doc_group = QWidget()
        doc_layout = QVBoxLayout(doc_group)
        
        doc_title = QLabel("<b>Documentación Final Requerida:</b>")
        doc_layout.addWidget(doc_title)
        
        # Documentos según el estado de salida
        self.doc_buttons_layout = QHBoxLayout()
        doc_layout.addLayout(self.doc_buttons_layout)
        
        # Vale de devolución (checkbox)
        vale_layout = QHBoxLayout()
        self.vale_checkbox = QCheckBox("Vale de Devolución")
        self.vale_checkbox.stateChanged.connect(self.on_vale_changed)
        vale_layout.addWidget(self.vale_checkbox)
        vale_layout.addStretch()
        doc_layout.addLayout(vale_layout)
        
        # Estado actual de documentos
        self.doc_status_layout = QVBoxLayout()
        doc_layout.addWidget(QLabel("<b>Estado de Documentos:</b>"))
        doc_layout.addLayout(self.doc_status_layout)
        
        layout.addWidget(doc_group)
        
        # Separador
        separator = QLabel("─" * 50)
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(separator)
        
        # Botón de salida
        self.exit_button = QPushButton("Confirmar Salida de Inventario")
        self.exit_button.setMinimumWidth(250)
        self.exit_button.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; }")
        self.exit_button.clicked.connect(self.mark_as_exited)
        layout.addWidget(self.exit_button)
        
        layout.addStretch()
        
        self.update_ui_state()

    def on_vale_changed(self, state):
        """Maneja el cambio del checkbox del vale de devolución."""
        vale_disponible = state == Qt.CheckState.Checked.value
        query = "UPDATE equipos SET vale_devolucion = ? WHERE id = ?"
        params = ("1" if vale_disponible else "0", self.data['id'])
        
        if self.db.execute_query(query, params) is not None:
            # Actualizar datos locales
            self.data['vale_devolucion'] = "1" if vale_disponible else "0"
            self._update_document_status()

    def upload_document(self, doc_type):
        """Sube un documento según el tipo especificado."""
        if not self.data['cerrado']:
            QMessageBox.warning(self, "Equipo no cerrado", "Debe cerrar el equipo antes de subir la documentación final.")
            return
        
        estado_salida = self.data['estado_salida']
        
        # Validaciones específicas por tipo de documento
        if doc_type == 'certificado_cat':
            if estado_salida != 'Útil':
                QMessageBox.critical(self, "Validación Fallida", "Solo se puede subir un CAT para equipos con estado 'Útil'.")
                return
            title = "Seleccionar Certificado CAT"
        elif doc_type == 'defect_report_final':
            if estado_salida != 'Reparable':
                QMessageBox.critical(self, "Validación Fallida", "Solo se puede subir un DR Final para equipos con estado 'Reparable'.")
                return
            title = "Seleccionar DR Final"
        elif doc_type == 'vale_devolucion':
            title = "Seleccionar Vale de Devolución"
        else:
            QMessageBox.critical(self, "Error", "Tipo de documento no válido.")
            return

        path, _ = QFileDialog.getOpenFileName(self, title)
        if not path: 
            return
        
        new_path = copy_document(path, self.data['doc_folder_path'])
        if not new_path: 
            return

        query = f"UPDATE equipos SET {doc_type} = ? WHERE id = ?"
        
        if self.db.execute_query(query, (new_path, self.data['id'])) is not None:
            QMessageBox.information(self, "Éxito", f"Documento subido correctamente.")
            self.data_changed.emit()

    def mark_as_exited(self):
        """Marca el equipo como fuera de inventario con todas las validaciones."""
        estado = self.data['estado_salida']
        
        # Validaciones básicas
        if not estado:
            QMessageBox.critical(self, "Validación Fallida", "El equipo no tiene un 'Estado de Salida' definido.")
            return
        
        if not self.data['cerrado']:
            QMessageBox.critical(self, "Validación Fallida", "El equipo debe estar cerrado antes de dar salida.")
            return
        
        # Validaciones de documentos según estado
        missing_docs = []
        
        if estado == 'Útil' and not self.data['certificado_cat']:
            missing_docs.append("Certificado CAT")
        
        if estado == 'Reparable' and not self.data['defect_report_final']:
            missing_docs.append("DR Final")
        
        # Validar vale de devolución (checkbox marcado)
        if not self.vale_checkbox.isChecked():
            missing_docs.append("Vale de Devolución (debe estar marcado)")
        
        if missing_docs:
            QMessageBox.critical(self, "Validación Fallida", 
                f"No se puede dar salida. Faltan los siguientes documentos:\n\n• " + "\n• ".join(missing_docs))
            return

        reply = QMessageBox.question(self, "Confirmar Salida", 
            "¿Está seguro de dar salida al equipo?\n\nEsta acción no se puede deshacer.")
        
        if reply == QMessageBox.StandardButton.Yes:
            query = "UPDATE equipos SET inventario = 0, fecha_salida = ? WHERE id = ?"
            params = (datetime.now().strftime("%Y-%m-%d %H:%M"), self.data['id'])
            if self.db.execute_query(query, params) is not None:
                QMessageBox.information(self, "Éxito", "El equipo ha sido marcado como fuera de inventario.")
                self.data_changed.emit()

    def update_data(self, new_data):
        self.data = new_data
        self.update_ui_state()

    def update_ui_state(self):
        """Actualiza la interfaz según el estado del equipo."""
        is_in_inventory = bool(self.data['inventario'])
        estado_salida = self.data['estado_salida']
        
        # Actualizar botón de salida
        self.exit_button.setVisible(is_in_inventory)
        
        # Actualizar estado general
        if is_in_inventory:
            self.status_label.setText(f"<b>Estado:</b> En inventario - {estado_salida or 'Sin estado de salida'}")
        else:
            self.status_label.setText(f"<b>Este equipo salió del inventario el {self.data['fecha_salida']}.</b>")
        
        # Actualizar checkbox del vale de devolución
        vale_disponible = self.data['vale_devolucion'] == "1"
        self.vale_checkbox.setChecked(vale_disponible)
        
        # Actualizar botones de documentos según estado de salida
        self._update_document_buttons()
        
        # Actualizar estado de documentos
        self._update_document_status()

    def _update_document_buttons(self):
        """Actualiza los botones de documentos según el estado de salida."""
        # Limpiar layout existente
        for i in reversed(range(self.doc_buttons_layout.count())):
            child = self.doc_buttons_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        estado_salida = self.data['estado_salida']
        
        if estado_salida == 'Útil':
            cat_button = QPushButton("Subir Certificado CAT")
            cat_button.setMinimumWidth(200)
            cat_button.clicked.connect(lambda: self.upload_document("certificado_cat"))
            self.doc_buttons_layout.addWidget(cat_button)
        elif estado_salida == 'Reparable':
            dr_button = QPushButton("Subir DR Final")
            dr_button.setMinimumWidth(200)
            dr_button.clicked.connect(lambda: self.upload_document("defect_report_final"))
            self.doc_buttons_layout.addWidget(dr_button)

    def _update_document_status(self):
        """Actualiza el estado visual de los documentos."""
        # Limpiar layout existente
        for i in reversed(range(self.doc_status_layout.count())):
            child = self.doc_status_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        estado_salida = self.data['estado_salida']
        
        # Estado del vale de devolución (siempre requerido)
        vale_status = "✅ Disponible" if self.data['vale_devolucion'] == "1" else "❌ No disponible"
        vale_label = QLabel(f"• Vale de Devolución: {vale_status}")
        self.doc_status_layout.addWidget(vale_label)
        
        # Estado de documentos específicos según estado de salida
        if estado_salida == 'Útil':
            cat_status = "✅ Subido" if self.data['certificado_cat'] else "❌ Pendiente"
            cat_label = QLabel(f"• Certificado CAT: {cat_status}")
            self.doc_status_layout.addWidget(cat_label)
        elif estado_salida == 'Reparable':
            dr_status = "✅ Subido" if self.data['defect_report_final'] else "❌ Pendiente"
            dr_label = QLabel(f"• DR Final: {dr_status}")
            self.doc_status_layout.addWidget(dr_label)


class ManageEquipmentDialog(QDialog):
    """Ventana para gestionar todos los aspectos de un equipo existente."""
    data_changed = pyqtSignal()

    def __init__(self, db_session, record_id, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.record_id = record_id
        
        self.setWindowTitle("Gestionar Equipo")
        self.setMinimumSize(900, 700)
        self.setModal(True)

        self.load_data()

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Barra de estado para feedback no intrusivo
        self.statusBar = QStatusBar()
        main_layout.addWidget(self.statusBar)

        self.create_tabs()

    def load_data(self):
        record = self.db.fetch_query("SELECT * FROM equipos WHERE id = ?", (self.record_id,), one=True)
        if not record:
            QMessageBox.critical(self, "Error", "No se pudo cargar el equipo.")
            # Cierra el diálogo si no hay datos
            self.reject()
            return
        # Convertir sqlite3.Row a un diccionario mutable para poder modificarlo en memoria
        self.data = dict(record)

        self.setWindowTitle(f"Gestionar Equipo - SN: {self.data['sn']} (OT: {self.data['numero_ot']})")

    def create_tabs(self):
        self.info_tab = InfoTab(self.data)
        self.tabs.addTab(self.info_tab, 'Información General')

        self.work_tab = WorkTab(self.db, self.data)
        self.work_tab.data_saved.connect(self.on_child_data_changed)
        self.tabs.addTab(self.work_tab, 'Trabajo')

        self.close_tab = CloseTab(self.db, self.data)
        self.close_tab.data_changed.connect(self.on_child_data_changed)
        self.tabs.addTab(self.close_tab, 'Cierre')

        self.exit_tab = ExitTab(self.db, self.data)
        self.exit_tab.data_changed.connect(self.on_child_data_changed)
        self.tabs.addTab(self.exit_tab, 'Salida de Inventario')

    def on_child_data_changed(self):
        """Se activa cuando una pestaña hija guarda datos."""
        self.load_data() # Recarga los datos del equipo desde la BD
        if not self.data: # Si el equipo fue eliminado o hay un error
            self.accept() # Cierra el diálogo
            return

        # Notifica a todas las pestañas para que actualicen su UI con los nuevos datos
        self.info_tab.update_data(self.data)
        self.work_tab.update_data(self.data)
        self.close_tab.update_data(self.data)
        
        # Para la pestaña de salida, reconstruir la UI es la forma más simple
        # de cambiar entre el botón y el texto de "ya salió".
        # La clave es limpiar el layout antes de llamar a init_ui.
        self.exit_tab.update_data(self.data)
        self.data_changed.emit() # Notifica a la ventana principal para que refresque la tabla
        self.statusBar.showMessage("Datos actualizados correctamente.", 3000) # 3 segundos


class MaterialRequestDialog(QDialog):
    """Ventana para solicitar material por correo electrónico."""
    def __init__(self, equipment_data, parent=None):
        super().__init__(parent)
        self.equipment_data = equipment_data
        self.setWindowTitle("Solicitud de Material")
        self.setModal(True)

        layout = QFormLayout(self)
        self.entries = {}
        fields = {
            "Nombre Pieza:": "nombre_pieza", "PN Pieza:": "pn_pieza",
            "SN Pieza:": "sn_pieza", "Cantidad:": "cantidad"
        }
        for label, key in fields.items():
            self.entries[key] = QLineEdit()
            layout.addRow(label, self.entries[key])

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        send_button = QPushButton("Enviar Petición por Correo")
        send_button.setMinimumWidth(200)
        send_button.clicked.connect(self.send_request)
        button_layout.addWidget(send_button)
        layout.addRow(button_layout)
        
        # --- Orden de Tabulación ---
        self.setTabOrder(self.entries["nombre_pieza"], self.entries["pn_pieza"])
        self.setTabOrder(self.entries["pn_pieza"], self.entries["sn_pieza"])
        self.setTabOrder(self.entries["sn_pieza"], self.entries["cantidad"])
        self.setTabOrder(self.entries["cantidad"], send_button)

    def send_request(self):
        material_data = {key: entry.text().strip() for key, entry in self.entries.items()}

        if not material_data["nombre_pieza"] or not material_data["cantidad"]:
            QMessageBox.critical(self, "Error de Validación", "Nombre de la pieza y Cantidad son obligatorios.")
            return

        subject = f"Solicitud de Material para OT {self.equipment_data['numero_ot']} (SN: {self.equipment_data['sn']})"
        body = textwrap.dedent(f"""
            Buenas,

            Se solicita el siguiente material para el equipo con OT {self.equipment_data['numero_ot']} (PN/SN: {self.equipment_data['pn']} / {self.equipment_data['sn']}).

            Detalles de la Petición:
            -------------------------
            - Nombre de la Pieza: {material_data['nombre_pieza']}
            - PN de la Pieza: {material_data['pn_pieza'] or 'N/A'}
            - SN de la Pieza: {material_data['sn_pieza'] or 'N/A'}
            - Cantidad: {material_data['cantidad']}

            Un saludo.

            ---
            Este es un mensaje generado automáticamente por el Sistema de Control de Equipos.
        """)
        send_email_notification(subject, body)
        self.accept()


class ProductivityChartDialog(QDialog):
    """Diálogo para mostrar gráficos de productividad usando Matplotlib."""
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.setWindowTitle("Gráficos de Productividad")
        self.setMinimumSize(1000, 650)

        layout = QVBoxLayout(self)

        if not MATPLOTLIB_AVAILABLE:
            label = QLabel("Las librerías 'matplotlib' y 'pandas' son necesarias para los gráficos.\nInstálalas con: py -m pip install matplotlib pandas")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            return

        # Aplicar un estilo global a todos los gráficos para un look profesional
        plt.style.use('seaborn-v0_8-darkgrid')

        # --- Filtro de Fechas ---
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrar por fecha de cierre:"))
        filter_layout.addWidget(QLabel("Desde:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addYears(-1))
        filter_layout.addWidget(self.start_date_edit)
        
        filter_layout.addWidget(QLabel("Hasta:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        filter_layout.addWidget(self.end_date_edit)

        apply_filter_button = QPushButton("Aplicar Filtro")
        apply_filter_button.clicked.connect(self.refresh_charts)
        filter_layout.addWidget(apply_filter_button)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # --- Creación del sistema de pestañas ---
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Pestaña 1: Rendimiento del Taller (Gráfico de Barras) ---
        performance_tab = QWidget()
        performance_layout = QVBoxLayout(performance_tab)
        self.performance_figure = plt.figure()
        self.performance_canvas = FigureCanvas(self.performance_figure)
        performance_toolbar = NavigationToolbar(self.performance_canvas, self)
        performance_layout.addWidget(performance_toolbar)
        performance_layout.addWidget(self.performance_canvas)
        self.tabs.addTab(performance_tab, "Rendimiento del Taller")

        # --- Pestaña 2: Distribución de Resultados (Gráfico Circular) ---
        distribution_tab = QWidget()
        distribution_layout = QVBoxLayout(distribution_tab)
        self.distribution_figure = plt.figure()
        self.distribution_canvas = FigureCanvas(self.distribution_figure)
        distribution_toolbar = NavigationToolbar(self.distribution_canvas, self)
        distribution_layout.addWidget(distribution_toolbar)
        distribution_layout.addWidget(self.distribution_canvas)
        self.tabs.addTab(distribution_tab, "Distribución de Resultados")

        # --- Pestaña 3: Tiempo de Ciclo (Gráfico de Líneas) ---
        turnaround_tab = QWidget()
        turnaround_layout = QVBoxLayout(turnaround_tab)
        self.turnaround_figure = plt.figure()
        self.turnaround_canvas = FigureCanvas(self.turnaround_figure)
        turnaround_toolbar = NavigationToolbar(self.turnaround_canvas, self)
        turnaround_layout.addWidget(turnaround_toolbar)
        turnaround_layout.addWidget(self.turnaround_canvas)
        self.tabs.addTab(turnaround_tab, "Tiempo de Ciclo (Turnaround)")

        # --- Pestaña 4: Histograma de Complejidad ---
        complexity_tab = QWidget()
        complexity_layout = QVBoxLayout(complexity_tab)
        self.complexity_figure = plt.figure()
        self.complexity_canvas = FigureCanvas(self.complexity_figure)
        complexity_toolbar = NavigationToolbar(self.complexity_canvas, self)
        complexity_layout.addWidget(complexity_toolbar)
        complexity_layout.addWidget(self.complexity_canvas)
        self.tabs.addTab(complexity_tab, "Complejidad de Reparaciones")

        # Cargar los gráficos con los datos iniciales
        self.refresh_charts()

    def refresh_charts(self):
        """Recarga todos los gráficos basándose en el filtro de fecha."""
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd 00:00:00")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd 23:59:59")

        self.plot_workshop_performance(self.performance_figure, self.performance_canvas, start_date, end_date)
        self.plot_results_distribution(self.distribution_figure, self.distribution_canvas, start_date, end_date)
        self.plot_turnaround_time(self.turnaround_figure, self.turnaround_canvas, start_date, end_date)
        self.plot_repair_complexity(self.complexity_figure, self.complexity_canvas, start_date, end_date)

    def plot_workshop_performance(self, figure, canvas, start_date, end_date):
        """Consulta los datos y genera el gráfico de equipos cerrados por mes."""
        figure.clear() # Limpiar el gráfico anterior
        query = "SELECT fecha_cierre FROM equipos WHERE cerrado = 1 AND fecha_cierre BETWEEN ? AND ?"
        records = self.db.fetch_query(query, (start_date, end_date))
        
        if not records:
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "No hay datos de equipos cerrados para generar el gráfico.", 
                    ha='center', va='center', fontsize=12, wrap=True)
            ax.set_xticks([])
            ax.set_yticks([])
            canvas.draw()
            return

        # --- Procesamiento de Datos con Pandas ---
        df = pd.DataFrame(records, columns=['fecha_cierre'])
        df['fecha_cierre'] = pd.to_datetime(df['fecha_cierre'], format='%Y-%m-%d %H:%M')
        
        # Agrupar por mes y contar
        monthly_performance = df.groupby(df['fecha_cierre'].dt.to_period('M')).size()
        
        # Asegurarse de que el índice sea de tipo string para el gráfico
        monthly_performance.index = monthly_performance.index.strftime('%Y-%m')

        # --- Generación del Gráfico ---
        ax = figure.add_subplot(111) # Añadir subplot después de limpiar
        
        bars = ax.bar(monthly_performance.index, monthly_performance.values, color='#4C72B0', edgecolor='black', linewidth=0.8)
        
        # Añadir etiquetas y título
        ax.set_title(f'Rendimiento del Taller\n({start_date.split(" ")[0]} a {end_date.split(" ")[0]})', fontsize=16, fontweight='bold')
        ax.set_ylabel('Nº de Equipos Cerrados', fontsize=12)
        ax.set_xlabel('Mes', fontsize=12)
        
        # Añadir el valor exacto encima de cada barra
        for bar in bars:
            yval = bar.get_height()
            if yval > 0:
                ax.text(bar.get_x() + bar.get_width()/2.0, yval, int(yval), va='bottom', ha='center', fontsize=10)

        # Mejorar la visualización
        # ax.grid(axis='y', linestyle='--', alpha=0.7) # El estilo global ya añade una rejilla
        plt.xticks(rotation=45, ha="right") # Rotar etiquetas para mejor legibilidad
        figure.tight_layout() # Ajustar layout para que no se corten las etiquetas

        # Dibujar el gráfico en el canvas
        canvas.draw()

    def plot_results_distribution(self, figure, canvas, start_date, end_date):
        """Consulta los datos y genera un gráfico circular de la distribución de resultados."""
        figure.clear()
        query = "SELECT estado_salida FROM equipos WHERE cerrado = 1 AND estado_salida IS NOT NULL AND estado_salida != '' AND fecha_cierre BETWEEN ? AND ?"
        records = self.db.fetch_query(query, (start_date, end_date))

        if not records:
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "No hay datos de estado de salida para generar el gráfico.",
                    ha='center', va='center', fontsize=12, wrap=True)
            ax.set_xticks([])
            ax.set_yticks([])
            canvas.draw()
            return

        # --- Procesamiento de Datos con Pandas ---
        df = pd.DataFrame(records, columns=['estado_salida'])
        status_counts = df['estado_salida'].value_counts()

        # --- Generación del Gráfico Circular ---
        ax = figure.add_subplot(111)
        
        # Colores para el gráfico
        colors = plt.cm.Paired(range(len(status_counts)))

        # "Explotar" la porción más grande para destacarla
        explode = [0.1] + [0] * (len(status_counts) - 1)

        wedges, texts, autotexts = ax.pie(
            status_counts, 
            autopct='%1.1f%%',  # Formato de porcentaje
            startangle=90,
            colors=colors,
            pctdistance=0.85, # Distancia del texto de porcentaje desde el centro
            explode=explode,
            shadow=True
        )
        
        # Mejorar la legibilidad del texto de porcentaje
        plt.setp(autotexts, size=10, weight="bold", color="white")

        ax.set_title(f'Distribución de Resultados\n({start_date.split(" ")[0]} a {end_date.split(" ")[0]})', fontsize=16, fontweight='bold')
        ax.legend(wedges, status_counts.index, title="Estados", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
        ax.axis('equal')  # Asegura que el gráfico sea un círculo.
        
        figure.tight_layout()
        canvas.draw()

    def plot_turnaround_time(self, figure, canvas, start_date, end_date):
        """Consulta datos y genera un gráfico de líneas del tiempo de ciclo promedio."""
        figure.clear()
        query = "SELECT fecha_entrada, fecha_cierre FROM equipos WHERE cerrado = 1 AND fecha_entrada IS NOT NULL AND fecha_cierre BETWEEN ? AND ?"
        records = self.db.fetch_query(query, (start_date, end_date))

        if not records:
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "No hay suficientes datos para calcular el tiempo de ciclo.",
                    ha='center', va='center', fontsize=12, wrap=True)
            ax.set_xticks([])
            ax.set_yticks([])
            canvas.draw()
            return

        # --- Procesamiento de Datos con Pandas ---
        df = pd.DataFrame(records, columns=['fecha_entrada', 'fecha_cierre'])
        df['fecha_entrada'] = pd.to_datetime(df['fecha_entrada'])
        df['fecha_cierre'] = pd.to_datetime(df['fecha_cierre'])
        
        # Calcular la duración en días
        df['turnaround_days'] = (df['fecha_cierre'] - df['fecha_entrada']).dt.days
        
        # Agrupar por mes de cierre y calcular el promedio
        avg_turnaround = df.groupby(df['fecha_cierre'].dt.to_period('M'))['turnaround_days'].mean()
        avg_turnaround.index = avg_turnaround.index.strftime('%Y-%m')

        # --- Generación del Gráfico de Líneas ---
        ax = figure.add_subplot(111)
        
        ax.plot(avg_turnaround.index, avg_turnaround.values, marker='o', linestyle='--', color='#1f77b4', label='Tiempo Promedio')
        
        # Añadir etiquetas y título
        ax.set_title(f'Tiempo Promedio de Ciclo (Turnaround Time)\n({start_date.split(" ")[0]} a {end_date.split(" ")[0]})', fontsize=16, fontweight='bold')
        ax.set_ylabel('Días Promedio', fontsize=12)
        ax.set_xlabel('Mes de Cierre', fontsize=12)
        
        # Mejorar la visualización
        ax.legend()
        plt.xticks(rotation=45, ha="right")
        figure.tight_layout()

        canvas.draw()
    
    def plot_repair_complexity(self, figure, canvas, start_date, end_date):
        """Consulta datos y genera un histograma de las horas de trabajo."""
        figure.clear()
        query = "SELECT horas_trabajo FROM equipos WHERE cerrado = 1 AND horas_trabajo IS NOT NULL AND horas_trabajo > 0 AND fecha_cierre BETWEEN ? AND ?"
        records = self.db.fetch_query(query, (start_date, end_date))

        if not records:
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "No hay datos de horas de trabajo para generar el histograma.",
                    ha='center', va='center', fontsize=12, wrap=True)
            ax.set_xticks([])
            ax.set_yticks([])
            canvas.draw()
            return

        # --- Procesamiento de Datos ---
        # Extraemos solo los valores de horas de la lista de tuplas
        hours_data = [record['horas_trabajo'] for record in records]

        # --- Generación del Histograma ---
        ax = figure.add_subplot(111)
        
        # Definir los 'bins' o rangos para el histograma
        bins = [0, 10, 20, 50, 100, 200, max(500, max(hours_data) if hours_data else 500)]
        
        ax.hist(hours_data, bins=bins, color='#ff7f0e', edgecolor='black')
        
        # Añadir etiquetas y título
        ax.set_title(f'Histograma de Complejidad de Reparaciones\n({start_date.split(" ")[0]} a {end_date.split(" ")[0]})', fontsize=16, fontweight='bold')
        ax.set_ylabel('Nº de Equipos', fontsize=12)
        ax.set_xlabel('Horas de Trabajo', fontsize=12)
        
        # Mejorar la visualización
        # ax.grid(axis='y', linestyle='--', alpha=0.7) # El estilo global ya añade una rejilla
        figure.tight_layout()

        canvas.draw()