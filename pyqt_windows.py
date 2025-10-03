# pyqt_windows.py
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QComboBox, QTextEdit, QPushButton, QLabel,
    QFileDialog, QMessageBox, QTabWidget, QWidget, QListWidget,
    QTableView, QAbstractItemView, QHeaderView, QCheckBox
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal

# --- IMPORTACIONES DE TU LÓGICA EXISTENTE ---
from config import Config
from logger import logger
from validators import Validator
from file_utils import copy_document, open_file
from email_utils import send_email_notification


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
        fields = {
            "Nombre Equipo:": "nombre_equipo",
            "PN (Part Number):": "pn",
            "SN (Serial Number):": "sn",
            "Nº OT (Orden Técnica):": "numero_ot",
            "Nº DR (Defect Report):": "defect_report"
        }
        for label_text, key in fields.items():
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
        cancel_button.clicked.connect(self.reject) # Cierra el diálogo sin hacer nada
        save_button = QPushButton("Guardar Entrada")
        save_button.setDefault(True)
        save_button.clicked.connect(self.save_entry)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)

        main_layout.addLayout(button_layout)

        # QoL: Poner el foco en el primer campo
        self.entries["nombre_equipo"].setFocus()

    def select_document(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar documento SL2000")
        if path:
            self.doc_path_label.setText(path)

    def save_entry(self):
        data = {key: entry.text().strip() for key, entry in self.entries.items()}

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


class ManageEquipmentDialog(QDialog):
    """Ventana para gestionar todos los aspectos de un equipo existente."""
    data_changed = pyqtSignal()

    def __init__(self, db_session, record_id, parent=None):
        super().__init__(parent)
        self.db = db_session
        self.record_id = record_id
        
        self._is_dirty = False # Flag para rastrear cambios no guardados
        self.setMinimumSize(900, 700)
        self.setModal(True)

        self.load_data()

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.create_tabs()

    def closeEvent(self, event):
        """Se activa al intentar cerrar la ventana."""
        if self._is_dirty:
            reply = QMessageBox.question(
                self, "Cambios no guardados",
                "Tienes cambios sin guardar. ¿Estás seguro de que quieres cerrar y descartarlos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        event.accept()

    def load_data(self):
        self.data = self.db.fetch_query("SELECT * FROM equipos WHERE id = ?", (self.record_id,), one=True)
        if not self.data:
            QMessageBox.critical(self, "Error", "No se pudo cargar el equipo.")
            # Cierra el diálogo si no hay datos
            self.reject()
            return
        self.setWindowTitle(f"Gestionar Equipo - SN: {self.data['sn']} (OT: {self.data['numero_ot']})")

    def create_tabs(self):
        # Tab 1: Información General
        info_tab = QWidget()
        self.populate_info_tab(info_tab)
        self.tabs.addTab(info_tab, 'Información General')

        # Tab 2: Trabajo y Fotos
        work_tab = QWidget()
        self.populate_work_tab(work_tab)
        self.tabs.addTab(work_tab, 'Trabajo')

        # Tab 3: Cierre y Documentación Final
        close_tab = QWidget()
        self.populate_close_tab(close_tab)
        self.tabs.addTab(close_tab, 'Cierre y Documentación')

        # Tab 4: Salida de Inventario
        exit_tab = QWidget()
        self.populate_exit_tab(exit_tab)
        self.tabs.addTab(exit_tab, 'Salida de Inventario')

    def populate_info_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # --- Datos de Entrada ---
        form_layout = QFormLayout()
        fields = [
            ("ID:", self.data['id']), ("Nombre:", self.data['nombre_equipo']),
            ("PN / SN:", f"{self.data['pn']} / {self.data['sn']}"),
            ("Estado Entrada:", self.data['estado_entrada']), ("Fecha Entrada:", self.data['fecha_entrada']),
            ("Nº OT / Nº DR:", f"{self.data['numero_ot']} / {self.data['defect_report'] or 'N/A'}")
        ]
        for label, value in fields:
            form_layout.addRow(QLabel(label), QLabel(str(value)))
        
        obs_entrada = QTextEdit(self.data['obs_entrada'] or "")
        obs_entrada.setReadOnly(True)
        form_layout.addRow("Obs. Entrada:", obs_entrada)
        
        layout.addLayout(form_layout)

        # --- Documentos Adjuntos ---
        layout.addWidget(QLabel("Documentos Adjuntos (doble clic para abrir):"))
        self.docs_list = QListWidget()
        self.docs_list.doubleClicked.connect(self.open_selected_document)
        layout.addWidget(self.docs_list)
        
        self.refresh_docs_list()

    def refresh_docs_list(self):
        self.docs_list.clear()
        all_docs = []
        if self.data['doc_entrada']: all_docs.append(self.data['doc_entrada'])
        all_docs.extend(json.loads(self.data['fotos'] or '[]'))
        if self.data['certificado_cat']: all_docs.append(self.data['certificado_cat'])
        if self.data['defect_report_final']: all_docs.append(self.data['defect_report_final'])

        for doc_path in all_docs:
            self.docs_list.addItem(doc_path)

    def open_selected_document(self):
        selected_item = self.docs_list.currentItem()
        if selected_item:
            open_file(selected_item.text())

    def populate_work_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # --- Actualizar Estado y Observaciones ---
        work_form_layout = QFormLayout()
        self.estado_salida_combo = QComboBox()
        self.estado_salida_combo.addItems(["", "Útil", "Reparable", "Stamby", "Falto de material", "Baja", "Incompleto"])
        self.estado_salida_combo.setCurrentText(self.data['estado_salida'] or "")
        self.estado_salida_combo.currentTextChanged.connect(self.mark_as_dirty)
        work_form_layout.addRow("Estado de Salida:", self.estado_salida_combo)

        self.obs_salida_text = QTextEdit(self.data['obs_salida'] or "")
        self.obs_salida_text.textChanged.connect(self.mark_as_dirty)
        work_form_layout.addRow("Observaciones de Salida:", self.obs_salida_text)
        
        save_work_button = QPushButton("Guardar Cambios de Trabajo")
        save_work_button.clicked.connect(self.save_work_changes)
        work_form_layout.addRow(save_work_button)
        layout.addLayout(work_form_layout)

        # --- Historial de Intervenciones ---
        layout.addWidget(QLabel("Historial de Intervenciones:"))
        self.log_model = QStandardItemModel()
        self.log_view = QTableView()
        self.log_view.setModel(self.log_model)
        self.log_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.log_view.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.log_view)
        self.refresh_log_table()

        log_entry_layout = QHBoxLayout()
        self.new_log_entry = QTextEdit()
        self.new_log_entry.setPlaceholderText("Escribe una nueva intervención aquí...")
        self.new_log_entry.setFixedHeight(60)
        add_log_button = QPushButton("Añadir al Historial")
        add_log_button.clicked.connect(self.save_log_entry)
        log_entry_layout.addWidget(self.new_log_entry)
        log_entry_layout.addWidget(add_log_button)
        layout.addLayout(log_entry_layout)

        # --- Añadir Archivos y Materiales ---
        bottom_layout = QHBoxLayout()        
        
        # Frame para añadir archivos
        file_frame = QWidget()
        file_frame_layout = QGridLayout(file_frame)
        file_frame_layout.setContentsMargins(0,0,0,0)
        
        btn_docs = QPushButton("Subir documentos escaneados")
        btn_docs.clicked.connect(lambda: self.add_files("Seleccionar documentos escaneados"))
        file_frame_layout.addWidget(btn_docs, 0, 0)

        btn_fotos = QPushButton("Añadir Fotos")
        btn_fotos.clicked.connect(lambda: self.add_files("Seleccionar Fotos", [("Archivos de Imagen", "*.jpg *.jpeg *.png *.gif")]))
        file_frame_layout.addWidget(btn_fotos, 0, 1)

        material_button = QPushButton("Solicitar Material")
        material_button.clicked.connect(self.open_material_request)
        
        bottom_layout.addWidget(file_frame)
        bottom_layout.addWidget(material_button)
        layout.addLayout(bottom_layout)

    def add_files(self, title, filetypes=None):
        """Añade archivos genéricos a la lista de 'fotos' del equipo."""
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
        self._is_dirty = False # Marcar como limpio después de guardar

    def save_log_entry(self):
        new_entry = self.new_log_entry.toPlainText().strip()
        if not new_entry: return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            current_log_list = json.loads(self.data['log_trabajo']) if self.data['log_trabajo'] else []
        except (json.JSONDecodeError, TypeError):
            current_log_list = [{"timestamp": "Fecha Antigua", "entry": self.data['log_trabajo'] or ""}]

        current_log_list.insert(0, {"timestamp": timestamp, "entry": new_entry})
        updated_log_json = json.dumps(current_log_list, indent=2)

        self.update_field_in_db('log_trabajo', updated_log_json, refresh_log=True)

    def open_material_request(self):
        dialog = MaterialRequestDialog(self.data, self)
        dialog.exec()

    def populate_close_tab(self, tab):
        layout = QVBoxLayout(tab)
        is_closed = bool(self.data['cerrado'])

        form_layout = QFormLayout()
        self.close_entries = {}
        fields = {"Destino:": "destino", "Horas de Trabajo:": "horas_trabajo"}
        for label, key in fields.items():
            entry = QLineEdit(str(self.data[key] or ""))
            entry.setDisabled(is_closed)
            entry.textChanged.connect(self.mark_as_dirty)
            self.close_entries[key] = entry
            form_layout.addRow(label, entry)

        self.contenedor_check = QCheckBox("Sí")
        self.contenedor_check.setChecked(bool(self.data['contenedor']))
        self.contenedor_check.setDisabled(is_closed)
        self.contenedor_check.stateChanged.connect(self.mark_as_dirty)
        form_layout.addRow("Contenedor:", self.contenedor_check)

        self.obs_cierre_text = QTextEdit(self.data['obs_cierre'] or "")
        self.obs_cierre_text.setDisabled(is_closed)
        self.obs_cierre_text.textChanged.connect(self.mark_as_dirty)
        form_layout.addRow("Obs. Cierre:", self.obs_cierre_text)
        layout.addLayout(form_layout)

        if is_closed:
            layout.addWidget(QLabel(f"Equipo cerrado el: {self.data['fecha_cierre']}"))
        else:
            save_close_button = QPushButton("Guardar y Cerrar Equipo")
            save_close_button.clicked.connect(self.save_and_close)
            layout.addWidget(save_close_button)

        # Botón para enviar notificación por correo
        send_email_button = QPushButton("Enviar Notificación de Cierre por Correo")
        send_email_button.clicked.connect(self.send_close_email)
        layout.addWidget(send_email_button)

    def save_and_close(self):
        self.load_data() # Asegurarse de tener el último estado
        if not self.data['estado_salida']:
            QMessageBox.critical(self, "Validación Fallida", "Debe definir un 'Estado de Salida' en la pestaña 'Trabajo'.")
            return
        
        data_to_save = {key: entry.text().strip() for key, entry in self.close_entries.items()}
        
        is_valid_hours, hours_error = Validator.validate_hours(data_to_save['horas_trabajo'])
        if not is_valid_hours:
            QMessageBox.critical(self, "Validación Fallida", f"Horas de trabajo no válidas: {hours_error}")
            return

        params = {
            "destino": data_to_save['destino'],
            "horas_trabajo": float(data_to_save['horas_trabajo']) if data_to_save['horas_trabajo'] else None,
            "contenedor": 1 if self.contenedor_check.isChecked() else 0,
            "obs_cierre": self.obs_cierre_text.toPlainText().strip(),
            "cerrado": 1,
            "fecha_cierre": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "id": self.record_id
        }

        query = """UPDATE equipos SET 
                   destino = :destino, horas_trabajo = :horas_trabajo, contenedor = :contenedor, 
                   obs_cierre = :obs_cierre, cerrado = :cerrado, fecha_cierre = :fecha_cierre
                   WHERE id = :id"""

        if self.db.execute_query(query, params) is not None:
            QMessageBox.information(self, "Éxito", "Equipo cerrado correctamente.")
            reply = QMessageBox.question(self, "Enviar Notificación", "¿Desea enviar la notificación de cierre por correo ahora?")
            if reply == QMessageBox.StandardButton.Yes:
                self.send_close_email()
            self.data_changed.emit()
            self._is_dirty = False
            self.accept()

    def send_close_email(self):
        self.load_data()
        if not self.data['cerrado']:
            QMessageBox.warning(self, "Equipo no cerrado", "Debe guardar y cerrar el equipo antes de enviar la notificación.")
            return
        
        subject = f"Cierre de Equipo - OT {self.data['numero_ot']} - SN {self.data['sn']}"
        
        body_lines = [
            "Buenas,",
            "",
            "Se adjunta la información referente al cierre del siguiente equipo:",
            "",
            f"  - Orden Técnica: {self.data['numero_ot']}",
            f"  - Nombre del Equipo: {self.data['nombre_equipo']}",
            f"  - PN / SN: {self.data['pn']} / {self.data['sn']}",
            f"  - Horas de Trabajo: {self.data['horas_trabajo'] or 'N/A'}",
            f"  - Estado de Salida: {self.data['estado_salida']}",
            f"  - Observaciones Cierre: {self.data['obs_cierre'] or 'Ninguna'}"
        ]

        if self.data['estado_salida'] == 'Reparable':
            body_lines.append(f"  - Destino: {self.data['destino'] or 'No especificado'}")

        body_lines.extend([
            "",
            "Un saludo.",
            "",
            "---",
            "Este es un mensaje generado automáticamente por el Sistema de Control de Equipos."
        ])

        body = "\n".join(body_lines)
        send_email_notification(subject, body)

    def populate_exit_tab(self, tab):
        layout = QVBoxLayout(tab)
        if not self.data['inventario']:
            layout.addWidget(QLabel(f"Este equipo salió del inventario el {self.data['fecha_salida']}."))
        else:
            exit_button = QPushButton("Confirmar Salida de Inventario")
            exit_button.clicked.connect(self.mark_as_exited)
            layout.addWidget(exit_button)

    def mark_as_exited(self):
        self.load_data()
        estado = self.data['estado_salida']
        doc_cat = self.data['certificado_cat']
        doc_dr = self.data['defect_report_final']

        if estado == 'Útil' and not doc_cat:
            QMessageBox.critical(self, "Validación Fallida", "No se puede dar salida. Falta el Certificado CAT para este equipo 'Útil'.")
            return
        if estado == 'Reparable' and not doc_dr:
            QMessageBox.critical(self, "Validación Fallida", "No se puede dar salida. Falta el DR Final para este equipo 'Reparable'.")
            return
        if not estado:
            QMessageBox.critical(self, "Validación Fallida", "El equipo no tiene un 'Estado de Salida' definido.")
            return

        reply = QMessageBox.question(self, "Confirmar Salida", "¿Está seguro? Esta acción no se puede deshacer.")
        if reply == QMessageBox.StandardButton.Yes:
            query = "UPDATE equipos SET inventario = 0, fecha_salida = ? WHERE id = ?"
            params = (datetime.now().strftime("%Y-%m-%d %H:%M"), self.record_id)
            if self.db.execute_query(query, params) is not None:
                QMessageBox.information(self, "Éxito", "El equipo ha sido marcado como fuera de inventario.")
                self.data_changed.emit()
                self.accept()

    def update_field_in_db(self, field_name, value, refresh_log=False):
        """Función de ayuda para actualizar uno o más campos en la BD."""
        if isinstance(field_name, list): # Para múltiples campos
            set_clause = ", ".join([f"{name} = ?" for name in field_name])
            params = (*value, self.record_id)
        else: # Para un solo campo
            set_clause = f"{field_name} = ?"
            params = (value, self.record_id)

        query = f"UPDATE equipos SET {set_clause} WHERE id = ?"
        if self.db.execute_query(query, params) is not None:
            self.load_data()
            if refresh_log: self.refresh_log_table()
            self.refresh_docs_list()
            self.data_changed.emit()
            QMessageBox.information(self, "Éxito", "Los datos han sido actualizados.")

    def mark_as_dirty(self):
        """Marca la ventana como 'sucia' (con cambios no guardados)."""
        self._is_dirty = True


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
        send_button.clicked.connect(self.send_request)
        button_layout.addWidget(send_button)
        layout.addRow(button_layout)

    def send_request(self):
        material_data = {key: entry.text().strip() for key, entry in self.entries.items()}

        if not material_data["nombre_pieza"] or not material_data["cantidad"]:
            QMessageBox.critical(self, "Error de Validación", "Nombre de la pieza y Cantidad son obligatorios.")
            return

        subject = f"Solicitud de Material para OT {self.equipment_data['numero_ot']} (SN: {self.equipment_data['sn']})"
        body = f"""
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
        """
        send_email_notification(subject, body.strip())
        self.accept()