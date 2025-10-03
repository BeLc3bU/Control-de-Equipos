# ui_utils.py

def show_error(title, message):
    """Muestra un mensaje de error. Intenta usar PyQt, si no, Tkinter."""
    try:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, title, message)
    except ImportError:
        from tkinter import messagebox
        messagebox.showerror(title, message)

def show_warning(title, message):
    """Muestra un mensaje de advertencia."""
    try:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(None, title, message)
    except ImportError:
        from tkinter import messagebox
        messagebox.showwarning(title, message)

def show_info(title, message):
    """Muestra un mensaje de información."""
    try:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(None, title, message)
    except ImportError:
        from tkinter import messagebox
        messagebox.showinfo(title, message)