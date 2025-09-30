# control_equipos.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import shutil
from datetime import datetime
import subprocess
import sys
import json
import smtplib
from email.message import EmailMessage

# --- CONFIGURACIÓN INICIAL ---
DB_NAME = "control_equipos.db"
DOCS_BASE_DIR = "docs"

# --- CONFIGURACIÓN SMTP (MODIFICAR CON TUS DATOS) ---
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "user@example.com"
SMTP_PASSWORD = "your_password"
EMAIL_RECIPIENT = "recipient@example.com"


class Database:
    """Clase para gestionar la conexión y operaciones con la base de datos SQLite."""
    def __init__(self, db_name):
        self.db_name = db_name

    def _get_connection(self):
        """Retorna una conexión a la base de datos."""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
        return conn

    def execute_query(self, query, params=()):
        """Ejecuta una consulta (INSERT, UPDATE, DELETE)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error en la base de datos: {e}")
            messagebox.showerror("Error de Base de Datos", f"No se pudo ejecutar la operación.\n\nError: {e}")
            return None

    def fetch_query(self, query, params=(), one=False):
        """Ejecuta una consulta de selección (SELECT)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                if one:
                    return cursor.fetchone()
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error en la base de datos: {e}")
            return None if one else []

    def setup(self):
        """Crea la tabla 'equipos' si no existe con la nueva estructura."""
        query = """
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_equipo TEXT,
            pn TEXT NOT NULL,
            sn TEXT NOT NULL UNIQUE,
            estado_entrada TEXT,
            numero_ot TEXT,
            defect_report TEXT,
            obs_entrada TEXT,
            fecha_entrada TEXT,
            doc_entrada TEXT,
            fotos TEXT,
            estado_salida TEXT,
            obs_salida TEXT,
            cerrado INTEGER DEFAULT 0,
            fecha_cierre TEXT,
            contenedor INTEGER,
            destino TEXT,
            horas_trabajo REAL,
            obs_cierre TEXT,
            certificado_cat TEXT,
            defect_report_final TEXT,
            fecha_salida TEXT,
            inventario INTEGER DEFAULT 1
        );
        """
        self.execute_query(query)

# --- LÓGICA DE LA APLICACIÓN ---
db = Database(DB_NAME)

def setup_environment():
    """Crea la base de datos y el directorio de documentos si no existen."""
    db.setup()
    if not os.path.exists(DOCS_BASE_DIR):
        os.makedirs(DOCS_BASE_DIR)

def copy_document(source_path, pn, sn, doc_type_folder):
    """Copia un documento a la carpeta organizada (entrada, trabajo, cierre)."""
    if not source_path:
        return ""
    
    filename = os.path.basename(source_path)
    target_dir = os.path.join(DOCS_BASE_DIR, f"{pn}_{sn}", doc_type_folder)
    
    os.makedirs(target_dir, exist_ok=True)
        
    target_path = os.path.join(target_dir, filename)
    shutil.copy(source_path, target_path)
    return target_path

def open_file(path):
    """Abre un archivo con el programa predeterminado del sistema."""
    if not path or not os.path.exists(path):
        messagebox.showwarning("Archivo no encontrado", "El documento no existe o la ruta es incorrecta.")
        return
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("Error al abrir", f"No se pudo abrir el archivo: {e}")

def send_email_notification(subject, body):
    """Envía una notificación por correo electrónico usando SMTP."""
    if SMTP_SERVER == "smtp.example.com":
        messagebox.showwarning("Configuración Requerida", "La función de correo no está configurada.\nEdita las constantes SMTP en el script.")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL_RECIPIENT

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        messagebox.showinfo("Correo Enviado", "La notificación de cierre ha sido enviada correctamente.")
    except Exception as e:
        messagebox.showerror("Error de Correo", f"No se pudo enviar el correo.\n\nError: {e}")


# --- INTERFAZ GRÁFICA (GUI) ---

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Control de Equipos - Banco de Pruebas de Aviónica")
        self.geometry("1400x750")

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Panel Superior (Botones y Filtros) ---
        top_panel = ttk.Frame(main_frame)
        top_panel.pack(fill=tk.X, pady=5)

        ttk.Button(top_panel, text="Registrar Nuevo Equipo", command=self.open_entry_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_panel, text="Refrescar Tabla", command=self.refresh_table).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_panel, text="Exportar a Excel", command=self.export_to_excel).pack(side=tk.LEFT, padx=5)
        
        # Filtros
        filter_frame = ttk.Frame(top_panel)
        filter_frame.pack(side=tk.RIGHT, padx=10)
        
        ttk.Label(filter_frame, text="Filtro Inventario:").pack(side=tk.LEFT, padx=(10, 2))
        self.inventory_filter = ttk.Combobox(filter_frame, values=["Todos", "En Inventario", "Fuera de Inventario"], state="readonly", width=15)
        self.inventory_filter.set("En Inventario")
        self.inventory_filter.pack(side=tk.LEFT)
        self.inventory_filter.bind("<<ComboboxSelected>>", self.refresh_table)

        ttk.Label(filter_frame, text="Buscar (PN/SN):").pack(side=tk.LEFT, padx=(10, 2))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_table())
        ttk.Entry(filter_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT)

        # --- Tabla de Equipos (TreeView) ---
        cols = ("ID", "Nombre", "PN", "SN", "Estado Entrada", "Fecha Entrada", "Estado Salida", "Cerrado", "Inventario")
        self.tree = ttk.Treeview(main_frame, columns=cols, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

        col_widths = {"ID": 40, "Nombre": 200, "PN": 150, "SN": 150, "Estado Entrada": 100, "Fecha Entrada": 120, "Estado Salida": 100, "Cerrado": 80, "Inventario": 80}
        for col in cols:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_column(_col, False))
            self.tree.column(col, width=col_widths.get(col, 100), anchor=tk.CENTER)
        
        self.tree.bind("<Double-1>", self.on_double_click)

        # --- Panel de Estadísticas ---
        stats_frame = ttk.LabelFrame(main_frame, text="Estadísticas Rápidas", padding="10")
        stats_frame.pack(fill=tk.X, pady=5)
        self.stats_label = ttk.Label(stats_frame, text="Cargando...")
        self.stats_label.pack(anchor=tk.W)

        self.refresh_table()

    def sort_column(self, col, reverse):
        """Ordena la tabla por la columna seleccionada."""
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def refresh_table(self, *args):
        """Limpia y recarga la tabla con datos de la BD, aplicando filtros."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        search_term = self.search_var.get().strip()
        inv_filter = self.inventory_filter.get()

        query = "SELECT id, nombre_equipo, pn, sn, estado_entrada, fecha_entrada, estado_salida, cerrado, inventario FROM equipos"
        conditions = []
        params = []

        if search_term:
            conditions.append("(pn LIKE ? OR sn LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        
        if inv_filter == "En Inventario":
            conditions.append("inventario = 1")
        elif inv_filter == "Fuera de Inventario":
            conditions.append("inventario = 0")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY fecha_entrada DESC"

        records = db.fetch_query(query, tuple(params))
        for row in records:
            values = (
                row['id'], row['nombre_equipo'], row['pn'], row['sn'],
                row['estado_entrada'], row['fecha_entrada'], row['estado_salida'],
                "Sí" if row['cerrado'] else "No",
                "Dentro" if row['inventario'] else "Fuera"
            )
            self.tree.insert("", tk.END, values=values)
        
        self.update_stats()

    def update_stats(self):
        """Calcula y muestra estadísticas básicas."""
        total_row = db.fetch_query("SELECT COUNT(*) FROM equipos", one=True)
        inventario_row = db.fetch_query("SELECT COUNT(*) FROM equipos WHERE inventario = 1", one=True)

        total = total_row[0] if total_row else 0
        en_inventario = inventario_row[0] if inventario_row else 0

        stats_text = f"Total Equipos: {total} | En Inventario: {en_inventario} | Fuera de Inventario: {total - en_inventario}"
        self.stats_label.config(text=stats_text)

    def on_double_click(self, event):
        """Abre la ventana de detalles/gestión para el equipo seleccionado."""
        item_id_str = self.tree.focus()
        if not item_id_str:
            return
        
        item_values = self.tree.item(item_id_str, "values")
        record_id = item_values[0]
        
        ManageEquipmentWindow(self, record_id)

    def export_to_excel(self):
        """Exporta los datos de la tabla a un archivo Excel."""
        try:
            import pandas as pd
        except ImportError:
            messagebox.showerror("Librería no encontrada", "Se necesita 'pandas' y 'openpyxl'.\nInstala con: py -m pip install pandas openpyxl")
            return

        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Sin datos", "No hay datos para exportar.")
            return

        data = [self.tree.item(item)['values'] for item in items]
        columns = [self.tree.heading(col)['text'] for col in self.tree['columns']]
        df = pd.DataFrame(data, columns=columns)
        
        try:
            filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")])
            if filepath:
                df.to_excel(filepath, index=False)
                messagebox.showinfo("Exportación Exitosa", f"Datos exportados a {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo guardar el archivo Excel: {e}")

    def open_entry_window(self):
        EntryWindow(self)

class EntryWindow(tk.Toplevel):
    """Ventana para el registro de entrada de un nuevo equipo."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Registrar Entrada de Equipo")
        self.geometry("500x450")
        self.transient(parent)
        self.grab_set()

        self.doc_path = tk.StringVar()
        
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        fields = {
            "Nombre Equipo:": "nombre_equipo", "PN (Part Number):": "pn", "SN (Serial Number):": "sn",
            "Nº OT (Orden Técnica):": "numero_ot", "Nº DR (Defect Report):": "defect_report"
        }
        self.entries = {}
        row_num = 0
        for label_text, key in fields.items():
            ttk.Label(frame, text=label_text).grid(row=row_num, column=0, sticky=tk.W, pady=2)
            entry = ttk.Entry(frame, width=40)
            entry.grid(row=row_num, column=1, sticky=tk.EW, pady=2)
            self.entries[key] = entry
            row_num += 1

        ttk.Label(frame, text="Estado de Entrada:").grid(row=row_num, column=0, sticky=tk.W, pady=2)
        self.estado_entrada_combo = ttk.Combobox(frame, values=["Útil", "Reparable", "Litigio", "Baja"], state="readonly")
        self.estado_entrada_combo.grid(row=row_num, column=1, sticky=tk.EW)
        self.estado_entrada_combo.set("Reparable")
        row_num += 1

        ttk.Label(frame, text="Observaciones Entrada:").grid(row=row_num, column=0, sticky=tk.NW, pady=5)
        self.obs_entrada_text = tk.Text(frame, height=4, width=40)
        self.obs_entrada_text.grid(row=row_num, column=1, sticky=tk.EW)
        row_num += 1

        ttk.Label(frame, text="Documento SL2000:").grid(row=row_num, column=0, sticky=tk.W, pady=5)
        doc_frame = ttk.Frame(frame)
        doc_frame.grid(row=row_num, column=1, sticky=tk.EW)
        ttk.Entry(doc_frame, textvariable=self.doc_path, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(doc_frame, text="...", width=3, command=self.select_document).pack(side=tk.LEFT)
        row_num += 1

        ttk.Button(frame, text="Guardar Entrada", command=self.save_entry).grid(row=row_num, column=0, columnspan=2, pady=20)

    def select_document(self):
        path = filedialog.askopenfilename(title="Seleccionar documento SL2000")
        if path:
            self.doc_path.set(path)

    def save_entry(self):
        data = {key: entry.get().strip() for key, entry in self.entries.items()}
        
        if not data["pn"] or not data["sn"]:
            messagebox.showerror("Error de Validación", "PN y SN son campos obligatorios.")
            return

        if db.fetch_query("SELECT id FROM equipos WHERE sn = ?", (data["sn"],), one=True):
            messagebox.showerror("Error de Duplicado", f"El Serial Number '{data['sn']}' ya existe.")
            return

        doc_target_path = copy_document(self.doc_path.get(), data["pn"], data["sn"], "entrada")

        query = """
        INSERT INTO equipos (nombre_equipo, pn, sn, numero_ot, defect_report, estado_entrada, obs_entrada, doc_entrada, fecha_entrada)
        VALUES (:nombre_equipo, :pn, :sn, :numero_ot, :defect_report, :estado_entrada, :obs_entrada, :doc_entrada, :fecha_entrada)
        """
        params = {
            **data,
            "estado_entrada": self.estado_entrada_combo.get(),
            "obs_entrada": self.obs_entrada_text.get("1.0", tk.END).strip(),
            "doc_entrada": doc_target_path,
            "fecha_entrada": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        if db.execute_query(query, params):
            messagebox.showinfo("Éxito", "Equipo registrado correctamente.")
            self.parent.refresh_table()
            self.destroy()

class ManageEquipmentWindow(tk.Toplevel):
    """Ventana para gestionar todos los aspectos de un equipo existente."""
    def __init__(self, parent, record_id):
        super().__init__(parent)
        self.parent = parent
        self.record_id = record_id
        
        self.title("Gestionar Equipo")
        self.geometry("900x700")
        self.transient(parent)
        self.grab_set()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        self.load_data()
        self.create_tabs()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.parent.refresh_table()
        self.destroy()

    def load_data(self):
        self.data = db.fetch_query("SELECT * FROM equipos WHERE id = ?", (self.record_id,), one=True)
        self.title(f"Gestionar Equipo - SN: {self.data['sn']}")

    def create_tabs(self):
        # Tab 1: Información General
        info_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(info_tab, text='Información General')
        self.populate_info_tab(info_tab)

        # Tab 2: Trabajo y Fotos
        work_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(work_tab, text='Trabajo / Fotos')
        self.populate_work_tab(work_tab)

        # Tab 3: Cierre y Documentación Final
        close_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(close_tab, text='Cierre y Documentación')
        self.populate_close_tab(close_tab)

        # Tab 4: Salida de Inventario
        exit_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(exit_tab, text='Salida de Inventario')
        self.populate_exit_tab(exit_tab)

    def populate_info_tab(self, tab):
        """Muestra la información de entrada y documentos."""
        frame = ttk.LabelFrame(tab, text="Datos de Entrada", padding="10")
        frame.pack(fill=tk.X)

        fields = [
            ("ID", self.data['id']), ("Nombre", self.data['nombre_equipo']),
            ("PN", self.data['pn']), ("SN", self.data['sn']),
            ("Estado Entrada", self.data['estado_entrada']), ("Fecha Entrada", self.data['fecha_entrada']),
            ("Nº OT", self.data['numero_ot']), ("Nº DR", self.data['defect_report'])
        ]
        for i, (label, value) in enumerate(fields):
            ttk.Label(frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(frame, text=value or "-", font=("", 10, "bold")).grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(frame, text="Obs. Entrada:").grid(row=len(fields), column=0, sticky=tk.NW, padx=5, pady=2)
        obs_text = tk.Text(frame, height=4, width=60)
        obs_text.insert("1.0", self.data['obs_entrada'] or "")
        obs_text.config(state="disabled")
        obs_text.grid(row=len(fields), column=1, sticky=tk.W, padx=5, pady=2)
        
        docs_frame = ttk.LabelFrame(tab, text="Documentos Adjuntos", padding="10")
        docs_frame.pack(fill=tk.X, pady=10)
        
        docs = {
            "Doc. Entrada (SL2000)": self.data['doc_entrada'],
            "Certificado (CAT)": self.data['certificado_cat'],
            "DR Final": self.data['defect_report_final']
        }
        for label, path in docs.items():
            if path:
                btn = ttk.Button(docs_frame, text=f"Abrir {label}", command=lambda p=path: open_file(p))
                btn.pack(anchor=tk.W, pady=2)
        
        ttk.Label(docs_frame, text="\nFotos de trabajo:").pack(anchor=tk.W, pady=(10,2))
        self.photo_listbox = tk.Listbox(docs_frame, height=5)
        self.photo_listbox.pack(fill=tk.X, expand=True)
        self.photo_listbox.bind("<Double-1>", lambda e: open_file(self.photo_listbox.get(self.photo_listbox.curselection())))
        self.refresh_photo_list()

    def populate_work_tab(self, tab):
        """Permite actualizar estado de salida, observaciones y añadir fotos."""
        frame = ttk.LabelFrame(tab, text="Actualizar Trabajo", padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Estado de Salida:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.estado_salida_combo = ttk.Combobox(frame, values=["", "Útil", "Reparable"], state="readonly")
        self.estado_salida_combo.set(self.data['estado_salida'] or "")
        self.estado_salida_combo.grid(row=0, column=1, sticky=tk.EW, pady=5)

        ttk.Label(frame, text="Observaciones de Salida:").grid(row=1, column=0, sticky=tk.NW, pady=5)
        self.obs_salida_text = tk.Text(frame, height=5)
        self.obs_salida_text.insert("1.0", self.data['obs_salida'] or "")
        self.obs_salida_text.grid(row=1, column=1, sticky=tk.EW, pady=5)

        ttk.Button(frame, text="Guardar Cambios de Trabajo", command=self.save_work_changes).grid(row=2, column=1, sticky=tk.E, pady=10)

        photo_frame = ttk.LabelFrame(tab, text="Añadir Fotos", padding="10")
        photo_frame.pack(fill=tk.X, pady=10)
        ttk.Button(photo_frame, text="Añadir Archivos de Foto...", command=self.add_photos).pack()

    def populate_close_tab(self, tab):
        """Formulario de cierre y subida de documentos finales."""
        is_closed = self.data['cerrado']
        
        form_frame = ttk.LabelFrame(tab, text="Formulario de Cierre", padding="10")
        form_frame.pack(fill=tk.X)
        
        self.close_entries = {}
        fields = {"Destino:": "destino", "Horas de Trabajo:": "horas_trabajo"}
        row = 0
        for label, key in fields.items():
            ttk.Label(form_frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
            entry = ttk.Entry(form_frame, width=40)
            entry.insert(0, self.data[key] or "")
            entry.config(state="disabled" if is_closed else "normal")
            entry.grid(row=row, column=1, sticky=tk.EW, pady=2)
            self.close_entries[key] = entry
            row += 1

        ttk.Label(form_frame, text="Contenedor:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.contenedor_var = tk.BooleanVar(value=bool(self.data['contenedor']))
        ttk.Checkbutton(form_frame, variable=self.contenedor_var, text="Sí", state="disabled" if is_closed else "normal").grid(row=row, column=1, sticky=tk.W)
        row += 1

        ttk.Label(form_frame, text="Obs. Cierre (montajes/desmontajes):").grid(row=row, column=0, sticky=tk.NW, pady=5)
        self.obs_cierre_text = tk.Text(form_frame, height=4)
        self.obs_cierre_text.insert("1.0", self.data['obs_cierre'] or "")
        self.obs_cierre_text.config(state="disabled" if is_closed else "normal")
        self.obs_cierre_text.grid(row=row, column=1, sticky=tk.EW, pady=5)
        row += 1

        if is_closed:
            ttk.Label(form_frame, text=f"Equipo cerrado el: {self.data['fecha_cierre']}", font=("", 10, "bold")).grid(row=row, column=0, columnspan=2, pady=10)
        else:
            ttk.Button(form_frame, text="Guardar y Cerrar Equipo", command=self.save_and_close).grid(row=row, column=1, sticky=tk.E, pady=10)
        
        ttk.Button(form_frame, text="Enviar Notificación de Cierre por Correo", command=self.send_close_email).grid(row=row, column=0, sticky=tk.W, pady=10)

        doc_frame = ttk.LabelFrame(tab, text="Documentación Final", padding="10")
        doc_frame.pack(fill=tk.X, pady=10)
        ttk.Button(doc_frame, text="Subir Certificado CAT (si es Útil)", command=lambda: self.upload_final_doc("cat")).pack(anchor=tk.W, pady=2)
        ttk.Button(doc_frame, text="Subir Defect Report Final (si es Reparable)", command=lambda: self.upload_final_doc("dr")).pack(anchor=tk.W, pady=2)

    def populate_exit_tab(self, tab):
        """Permite marcar el equipo como fuera de inventario."""
        frame = ttk.LabelFrame(tab, text="Salida de Inventario", padding="10")
        frame.pack(fill=tk.X)

        if not self.data['inventario']:
            ttk.Label(frame, text=f"Este equipo salió del inventario el {self.data['fecha_salida']}.", font=("", 10, "bold")).pack(pady=10)
        else:
            ttk.Label(frame, text="Marcar este equipo como 'Fuera de Inventario'.").pack(pady=5)
            ttk.Button(frame, text="Confirmar Salida de Inventario", command=self.mark_as_exited).pack(pady=10)

    def save_work_changes(self):
        estado_salida = self.estado_salida_combo.get()
        obs_salida = self.obs_salida_text.get("1.0", tk.END).strip()
        
        query = "UPDATE equipos SET estado_salida = ?, obs_salida = ? WHERE id = ?"
        if db.execute_query(query, (estado_salida, obs_salida, self.record_id)) is not None:
            messagebox.showinfo("Éxito", "Cambios de trabajo guardados.")
            self.load_data() # Recargar datos

    def add_photos(self):
        paths = filedialog.askopenfilenames(title="Seleccionar fotos", filetypes=[("Image Files", "*.jpg *.jpeg *.png *.gif")])
        if not paths:
            return
        
        current_photos = json.loads(self.data['fotos'] or '[]')
        
        for path in paths:
            new_path = copy_document(path, self.data['pn'], self.data['sn'], "trabajo")
            if new_path not in current_photos:
                current_photos.append(new_path)
        
        query = "UPDATE equipos SET fotos = ? WHERE id = ?"
        if db.execute_query(query, (json.dumps(current_photos), self.record_id)) is not None:
            messagebox.showinfo("Éxito", f"{len(paths)} foto(s) añadida(s).")
            self.load_data()
            self.refresh_photo_list()

    def refresh_photo_list(self):
        self.photo_listbox.delete(0, tk.END)
        photos = json.loads(self.data['fotos'] or '[]')
        for photo_path in photos:
            self.photo_listbox.insert(tk.END, photo_path)

    def save_and_close(self):
        self.load_data() # Asegurarse de tener el último estado
        if not self.data['estado_salida']:
            messagebox.showerror("Validación Fallida", "Debe definir un 'Estado de Salida' en la pestaña 'Trabajo / Fotos' antes de cerrar.")
            return

        data_to_save = {key: entry.get().strip() for key, entry in self.close_entries.items()}
        data_to_save['contenedor'] = self.contenedor_var.get()
        data_to_save['obs_cierre'] = self.obs_cierre_text.get("1.0", tk.END).strip()
        data_to_save['cerrado'] = 1
        data_to_save['fecha_cierre'] = datetime.now().strftime("%Y-%m-%d %H:%M")

        query = """UPDATE equipos SET 
                   destino = :destino, horas_trabajo = :horas_trabajo, contenedor = :contenedor, 
                   obs_cierre = :obs_cierre, cerrado = :cerrado, fecha_cierre = :fecha_cierre
                   WHERE id = :id"""
        params = {**data_to_save, "id": self.record_id}

        if db.execute_query(query, params) is not None:
            messagebox.showinfo("Éxito", "Equipo cerrado correctamente.")
            self.on_close()

    def send_close_email(self):
        self.load_data()
        if not self.data['cerrado']:
            messagebox.showwarning("Equipo no cerrado", "Debe guardar y cerrar el equipo antes de enviar la notificación.")
            return
        
        subject = f"Cierre de Equipo - OT {self.data['numero_ot']} - SN {self.data['sn']}"
        body = f"""
        Se ha cerrado el trabajo para el siguiente equipo:
        
        - Nombre: {self.data['nombre_equipo']}
        - PN/SN: {self.data['pn']} / {self.data['sn']}
        - Orden Técnica (OT): {self.data['numero_ot']}
        - Estado Final: {self.data['estado_salida']}
        - Horas de Trabajo: {self.data['horas_trabajo']}
        - Destino: {self.data['destino']}
        - Contenedor: {'Sí' if self.data['contenedor'] else 'No'}
        
        Observaciones de Cierre:
        {self.data['obs_cierre']}
        
        Fecha de Cierre: {self.data['fecha_cierre']}
        """
        send_email_notification(subject, body.strip())

    def upload_final_doc(self, doc_type):
        self.load_data()
        if not self.data['cerrado']:
            messagebox.showwarning("Equipo no cerrado", "Debe cerrar el equipo antes de subir la documentación final.")
            return
        
        estado_salida = self.data['estado_salida']
        if doc_type == 'cat' and estado_salida != 'Útil':
            messagebox.showerror("Validación Fallida", "Solo se puede subir un CAT para equipos con estado 'Útil'.")
            return
        if doc_type == 'dr' and estado_salida != 'Reparable':
            messagebox.showerror("Validación Fallida", "Solo se puede subir un DR Final para equipos con estado 'Reparable'.")
            return

        path = filedialog.askopenfilename(title=f"Seleccionar documento {'CAT' if doc_type == 'cat' else 'DR Final'}")
        if not path:
            return
        
        new_path = copy_document(path, self.data['pn'], self.data['sn'], "cierre")
        
        field_to_update = "certificado_cat" if doc_type == 'cat' else "defect_report_final"
        query = f"UPDATE equipos SET {field_to_update} = ? WHERE id = ?"
        
        if db.execute_query(query, (new_path, self.record_id)) is not None:
            messagebox.showinfo("Éxito", "Documento final subido correctamente.")
            self.load_data()

    def mark_as_exited(self):
        self.load_data()
        estado = self.data['estado_salida']
        doc_cat = self.data['certificado_cat']
        doc_dr = self.data['defect_report_final']

        if estado == 'Útil' and not doc_cat:
            messagebox.showerror("Validación Fallida", "No se puede dar salida. Falta el Certificado CAT para este equipo 'Útil'.")
            return
        if estado == 'Reparable' and not doc_dr:
            messagebox.showerror("Validación Fallida", "No se puede dar salida. Falta el DR Final para este equipo 'Reparable'.")
            return
        
        if messagebox.askyesno("Confirmar Salida", "¿Está seguro de que desea marcar este equipo como fuera de inventario? Esta acción no se puede deshacer."):
            query = "UPDATE equipos SET inventario = 0, fecha_salida = ? WHERE id = ?"
            params = (datetime.now().strftime("%Y-%m-%d %H:%M"), self.record_id)
            if db.execute_query(query, params) is not None:
                messagebox.showinfo("Éxito", "El equipo ha sido marcado como fuera de inventario.")
                self.on_close()

# --- PUNTO DE ENTRADA PRINCIPAL ---
if __name__ == "__main__":
    setup_environment()
    app = App()
    app.mainloop()
