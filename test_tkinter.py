# test_tkinter.py
import tkinter as tk

try:
    print("Intentando crear una ventana de prueba...")
    root = tk.Tk()
    root.title("Prueba de Tkinter")
    root.geometry("300x150")
    label = tk.Label(root, text="¡Si ves esta ventana, Tkinter funciona!", font=("Helvetica", 12))
    label.pack(pady=40)
    print("Ventana creada. Mostrando ahora...")
    root.mainloop()
    print("La ventana de prueba se cerró correctamente.")
except Exception as e:
    print(f"\n¡ERROR! Ocurrió un problema al iniciar Tkinter: {e}")
    input("Presiona Enter para salir.")

