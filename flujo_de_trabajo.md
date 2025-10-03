```mermaid
graph TD
    subgraph "Fase de Inicialización"
        A["1. Usuario ejecuta `py main_pyqt.py`"] --> B("2. Se llama a `setup_environment()` para inicializar la BD");
        B --> C["3. Se crea la instancia de `QApplication`"];
        C --> D["4. Se crea la `MainWindow` y se construye la UI"];
        D --> E("5. `MainWindow.refresh_table()` consulta la BD y puebla la tabla");
    end

    subgraph "Ciclo de Vida de la Aplicación"
        E --> F{"6. La aplicación entra en el bucle de eventos `app.exec()`"};
        F -- "Interacción del Usuario (ej: clic en botón)" --> G("7. Se dispara un método en `MainWindow`");
        F -- Cierre de la Ventana --> Z[Fin del Programa];
    end

    subgraph "Flujo de un Diálogo (Ej: Registrar Equipo)"
        G --> H["8. Se crea una instancia de un diálogo (ej: `EntryDialog`)"];
        H --> I["9. El diálogo gestiona su propia lógica (validación, archivos, etc.)"];
        I --> J{"10. El usuario guarda con éxito (`accept()`)"};
        J -- Sí --> K["El diálogo emite una señal (ej: `data_changed`)"];
        J -- No (Cancela) --> F;
    end

    subgraph "Actualización de la UI"
        K --> L("11. `MainWindow` recibe la señal");
        L --> E;
    end
