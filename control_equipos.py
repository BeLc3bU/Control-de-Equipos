# control_equipos.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import shutil
from datetime import datetime
import subprocess
import sys

# --- CONFIGURACIÓN INICIAL ---
DB_NAME = "control_equipos.db"
DOCS_BASE_DIR = "docs"

class Database:
    """Clase para gestionar la conexión y operaciones con la base de datos SQLite."""
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establece la conexión con la base de datos."""
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def disconnect(self):
        """Cierra la conexión con la base de datos."""
        if self.conn:
            self.conn.close()

    def execute_query(self, query, params=()):
        """Ejecuta una consulta (INSERT, UPDATE, DELETE)."""
        try:
            self.connect()
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error en la base de datos: {e}")
            return None
        finally:
            self.disconnect()

    def fetch_query(self, query, params=()):
        """Ejecuta una consulta de selección (SELECT)."""
        try:
            self.connect()
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error en la base de datos: {e}")
            return []
        finally:
            self.disconnect()

    def setup(self):
        """Crea la tabla 'equipos' si no existe."""
        query = """
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pn TEXT NOT NULL,
            sn TEXT NOT NULL UNIQUE,
            estado_entrada TEXT,
            observaciones_entrada TEXT,
            documento_entrada TEXT,
            fecha_entrada TEXT,
            estado_salida TEXT,
            observaciones_salida TEXT,
            documento_salida TEXT,
            fecha_salida TEXT
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

def copy_document(source_path, pn, sn, doc_type):
    """Copia un documento a la carpeta organizada."""
    if not source_path:
        return ""
    
    filename = os.path.basename(source_path)
    target_dir = os.path.join(DOCS_BASE_DIR, f"{pn}_{sn}", doc_type)
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
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
        elif sys.platform == "darwin": # macOS
            subprocess.Popen(["open", path])
        else: # linux
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("Error al abrir", f"No se pudo abrir el archivo: {e}")

# --- INTERFAZ GRÁFICA (GUI) ---

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Control de Equipos - Banco de Pruebas de Aviónica")
        self.geometry("1200x700")

        # --- Layout Principal ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Panel de Botones ---
        button_panel = ttk.Frame(main_frame)
        button_panel.pack(fill=tk.X, pady=5)

        ttk.Button(button_panel, text="Registrar Entrada", command=self.open_entry_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_panel, text="Registrar Salida", command=self.open_exit_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_panel, text="Exportar a Excel", command=self.export_to_excel).pack(side=tk.LEFT, padx=5)

        # --- Panel de Búsqueda ---
        search_panel = ttk.Frame(main_frame)
        search_panel.pack(fill=tk.X, pady=5)
        ttk.Label(search_panel, text="Buscar por PN o SN:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_table())
        ttk.Entry(search_panel, textvariable=self.search_var, width=40).pack(side=tk.LEFT)

        # --- Tabla de Equipos (TreeView) ---
        self.tree = ttk.Treeview(main_frame, columns=("ID", "PN", "SN", "Estado Entrada", "Fecha Entrada", "Estado Salida", "Fecha Salida"), show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

        # Definir encabezados y anchos de columna
        columns = {"ID": 30, "PN": 150, "SN": 150, "Estado Entrada": 100, "Fecha Entrada": 120, "Estado Salida": 100, "Fecha Salida": 120}
        for col, width in columns.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=tk.CENTER)
        
        self.tree.bind("<Double-1>", self.on_double_click)

        # --- Panel de Estadísticas ---
        stats_frame = ttk.LabelFrame(main_frame, text="Estadísticas", padding="10")
        stats_frame.pack(fill=tk.X, pady=5)
        self.stats_label = ttk.Label(stats_frame, text="Cargando...")
        self.stats_label.pack(anchor=tk.W)

        self.refresh_table()

    def refresh_table(self):
        """Limpia y recarga la tabla con datos de la BD, aplicando el filtro de búsqueda."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        search_term = self.search_var.get().strip()
        if search_term:
            query = "SELECT id, pn, sn, estado_entrada, fecha_entrada, estado_salida, fecha_salida FROM equipos WHERE pn LIKE ? OR sn LIKE ?"
            params = (f"%{search_term}%", f"%{search_term}%")
        else:
            query = "SELECT id, pn, sn, estado_entrada, fecha_entrada, estado_salida, fecha_salida FROM equipos ORDER BY fecha_entrada DESC"
            params = ()

        records = db.fetch_query(query, params)
        for row in records:
            self.tree.insert("", tk.END, values=row)
        
        self.update_stats()

    def update_stats(self):
        """Calcula y muestra estadísticas básicas."""
        records = db.fetch_query("SELECT estado_entrada, COUNT(*) FROM equipos GROUP BY estado_entrada")
        stats_text = "Equipos por estado de entrada: "
        if not records:
            stats_text += "Sin datos."
        else:
            stats_text += " | ".join([f"{estado or 'N/A'}: {count}" for estado, count in records])
        self.stats_label.config(text=stats_text)

    def on_double_click(self, event):
        """Maneja el doble clic en una fila para abrir documentos."""
        item_id = self.tree.focus()
        if not item_id:
            return
        
        item_values = self.tree.item(item_id, "values")
        record_id = item_values[0]
        
        record = db.fetch_query("SELECT documento_entrada, documento_salida FROM equipos WHERE id = ?", (record_id,))
        if not record:
            return
        
        doc_entrada, doc_salida = record[0]
        
        if not doc_entrada and not doc_salida:
            messagebox.showinfo("Sin Documentos", "Este registro no tiene documentos adjuntos.")
            return

        # Crear una ventana para elegir qué documento abrir
        choice_win = tk.Toplevel(self)
        choice_win.title("Abrir Documento")
        choice_win.geometry("300x150")
        ttk.Label(choice_win, text="¿Qué documento desea abrir?").pack(pady=10)
        
        if doc_entrada:
            ttk.Button(choice_win, text=f"Entrada: {os.path.basename(doc_entrada)}", command=lambda: open_file(doc_entrada)).pack(pady=5, fill=tk.X, padx=10)
        if doc_salida:
            ttk.Button(choice_win, text=f"Salida: {os.path.basename(doc_salida)}", command=lambda: open_file(doc_salida)).pack(pady=5, fill=tk.X, padx=10)

    def export_to_excel(self):
        """Exporta los datos de la tabla a un archivo Excel."""
        try:
            import pandas as pd
        except ImportError:
            messagebox.showerror(
                "Librería no encontrada",
                "La librería 'pandas' es necesaria para exportar a Excel.\n"
                "Por favor, instálala ejecutando en la terminal:\n"
                "py -m pip install pandas openpyxl"
            )
            return

        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Sin datos", "No hay datos para exportar.")
            return

        data = [self.tree.item(item)['values'] for item in items]
        columns = [self.tree.heading(col)['text'] for col in self.tree['columns']]
        df = pd.DataFrame(data, columns=columns)

        try:
            filepath = "reporte_equipos.xlsx"
            df.to_excel(filepath, index=False)
            messagebox.showinfo("Exportación Exitosa", f"Datos exportados a {filepath}")
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo guardar el archivo Excel: {e}")

    def open_entry_window(self):
        EntryWindow(self)

    def open_exit_window(self):
        ExitWindow(self)

class EntryWindow(tk.Toplevel):
    """Ventana para el registro de entrada de un equipo."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Registrar Entrada de Equipo")
        self.geometry("450x350")
        self.transient(parent)
        self.grab_set()

        self.doc_path = tk.StringVar()
        
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="PN (Part Number):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.pn_entry = ttk.Entry(frame, width=40)
        self.pn_entry.grid(row=0, column=1, sticky=tk.EW)

        ttk.Label(frame, text="SN (Serial Number):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.sn_entry = ttk.Entry(frame, width=40)
        self.sn_entry.grid(row=1, column=1, sticky=tk.EW)

        ttk.Label(frame, text="Estado de Entrada:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.estado_entrada_combo = ttk.Combobox(frame, values=["Útil", "Reparable", "Litigio", "Baja"], state="readonly")
        self.estado_entrada_combo.grid(row=2, column=1, sticky=tk.EW)
        self.estado_entrada_combo.set("Útil")

        ttk.Label(frame, text="Observaciones:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.obs_entrada_text = tk.Text(frame, height=4, width=40)
        self.obs_entrada_text.grid(row=3, column=1, sticky=tk.EW)

        ttk.Label(frame, text="Documento:").grid(row=4, column=0, sticky=tk.W, pady=5)
        doc_frame = ttk.Frame(frame)
        doc_frame.grid(row=4, column=1, sticky=tk.EW)
        ttk.Entry(doc_frame, textvariable=self.doc_path, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(doc_frame, text="...", width=3, command=self.select_document).pack(side=tk.LEFT)

        ttk.Button(frame, text="Guardar Entrada", command=self.save_entry).grid(row=5, column=0, columnspan=2, pady=20)

    def select_document(self):
        path = filedialog.askopenfilename(title="Seleccionar documento")
        if path:
            self.doc_path.set(path)

    def save_entry(self):
        pn = self.pn_entry.get().strip()
        sn = self.sn_entry.get().strip()
        estado = self.estado_entrada_combo.get()
        obs = self.obs_entrada_text.get("1.0", tk.END).strip()
        doc_source = self.doc_path.get()

        if not pn or not sn:
            messagebox.showerror("Error de Validación", "PN y SN son campos obligatorios.")
            return

        # Validar si el SN ya existe
        if db.fetch_query("SELECT id FROM equipos WHERE sn = ?", (sn,)):
            messagebox.showerror("Error de Duplicado", f"El Serial Number '{sn}' ya existe en la base de datos.")
            return

        # Copiar documento
        doc_target_path = copy_document(doc_source, pn, sn, "entrada")

        # Guardar en BD
        query = """
        INSERT INTO equipos (pn, sn, estado_entrada, observaciones_entrada, documento_entrada, fecha_entrada)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (pn, sn, estado, obs, doc_target_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        if db.execute_query(query, params):
            messagebox.showinfo("Éxito", "Equipo registrado correctamente.")
            self.parent.refresh_table()
            self.destroy()
        else:
            messagebox.showerror("Error de Base de Datos", "No se pudo guardar el registro.")

class ExitWindow(tk.Toplevel):
    """Ventana para el registro de salida de un equipo."""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Registrar Salida de Equipo")
        self.geometry("450x400")
        self.transient(parent)
        self.grab_set()

        self.doc_path = tk.StringVar()
        self.record_id = None

        frame = ttk.Frame(self, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # --- Sección de Búsqueda ---
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text="Buscar por SN:").pack(side=tk.LEFT)
        self.sn_search_entry = ttk.Entry(search_frame, width=25)
        self.sn_search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Buscar", command=self.search_sn).pack(side=tk.LEFT)

        # --- Formulario de Salida (inicialmente deshabilitado) ---
        self.form_frame = ttk.LabelFrame(frame, text="Datos del Equipo", padding="10")
        self.form_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.form_frame, text="PN:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.pn_label = ttk.Label(self.form_frame, text="-")
        self.pn_label.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(self.form_frame, text="SN:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.sn_label = ttk.Label(self.form_frame, text="-")
        self.sn_label.grid(row=1, column=1, sticky=tk.W)

        ttk.Label(self.form_frame, text="Estado de Salida:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.estado_salida_combo = ttk.Combobox(self.form_frame, values=["Reparado", "Rechazado", "Baja"], state="disabled")
        self.estado_salida_combo.grid(row=2, column=1, sticky=tk.EW)

        ttk.Label(self.form_frame, text="Observaciones:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.obs_salida_text = tk.Text(self.form_frame, height=4, width=40, state="disabled")
        self.obs_salida_text.grid(row=3, column=1, sticky=tk.EW)

        ttk.Label(self.form_frame, text="Documento:").grid(row=4, column=0, sticky=tk.W, pady=5)
        doc_frame = ttk.Frame(self.form_frame)
        doc_frame.grid(row=4, column=1, sticky=tk.EW)
        self.doc_entry = ttk.Entry(doc_frame, textvariable=self.doc_path, state="disabled")
        self.doc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.doc_button = ttk.Button(doc_frame, text="...", width=3, command=self.select_document, state="disabled")
        self.doc_button.pack(side=tk.LEFT)

        self.save_button = ttk.Button(frame, text="Guardar Salida", command=self.save_exit, state="disabled")
        self.save_button.pack(pady=10)

    def search_sn(self):
        sn = self.sn_search_entry.get().strip()
        if not sn:
            return
        
        query = "SELECT id, pn, sn, fecha_salida FROM equipos WHERE sn = ?"
        result = db.fetch_query(query, (sn,))

        if not result:
            messagebox.showwarning("No Encontrado", f"No se encontró ningún equipo con el SN '{sn}'.")
            self.reset_form()
            return
        
        record = result[0]
        self.record_id, pn, sn_found, fecha_salida = record

        if fecha_salida:
            messagebox.showwarning("Ya Registrado", f"Este equipo ya tiene una fecha de salida registrada ({fecha_salida}).")
            self.reset_form()
            return

        self.pn_label.config(text=pn)
        self.sn_label.config(text=sn_found)
        self.enable_form()

    def enable_form(self):
        """Habilita los campos del formulario una vez que se encuentra un equipo."""
        self.estado_salida_combo.config(state="readonly")
        self.estado_salida_combo.set("Reparado")
        self.obs_salida_text.config(state="normal")
        self.doc_entry.config(state="readonly")
        self.doc_button.config(state="normal")
        self.save_button.config(state="normal")

    def reset_form(self):
        """Limpia y deshabilita el formulario."""
        self.record_id = None
        self.pn_label.config(text="-")
        self.sn_label.config(text="-")
        self.estado_salida_combo.set("")
        self.estado_salida_combo.config(state="disabled")
        self.obs_salida_text.delete("1.0", tk.END)
        self.obs_salida_text.config(state="disabled")
        self.doc_path.set("")
        self.doc_entry.config(state="disabled")
        self.doc_button.config(state="disabled")
        self.save_button.config(state="disabled")

    def select_document(self):
        path = filedialog.askopenfilename(title="Seleccionar documento de salida")
        if path:
            self.doc_path.set(path)

    def save_exit(self):
        if not self.record_id:
            return

        estado = self.estado_salida_combo.get()
        obs = self.obs_salida_text.get("1.0", tk.END).strip()
        doc_source = self.doc_path.get()
        pn = self.pn_label.cget("text")
        sn = self.sn_label.cget("text")

        # Copiar documento
        doc_target_path = copy_document(doc_source, pn, sn, "salida")

        # Actualizar BD
        query = """
        UPDATE equipos
        SET estado_salida = ?, observaciones_salida = ?, documento_salida = ?, fecha_salida = ?
        WHERE id = ?
        """
        params = (estado, obs, doc_target_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.record_id)
        
        if db.execute_query(query, params) is not None:
            messagebox.showinfo("Éxito", "Salida de equipo registrada correctamente.")
            self.parent.refresh_table()
            self.destroy()
        else:
            messagebox.showerror("Error de Base de Datos", "No se pudo actualizar el registro.")

# --- PUNTO DE ENTRADA PRINCIPAL ---
if __name__ == "__main__":
    setup_environment()
    app = App()
    app.mainloop()
