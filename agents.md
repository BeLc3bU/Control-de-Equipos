# Agent Context: Control de Equipos (PyQt Version)

This document provides a detailed context for AI agents to understand the structure, purpose, and key components of the "Control de Equipos" application.

## 1. Project Overview

The project is a desktop application built with Python and PyQt6. Its primary function is to manage the workflow of avionic equipment in a testing workshop. It tracks equipment from entry, through testing and repair, to final dispatch. The application uses a SQLite database for data persistence and provides features like data entry, management, filtering, reporting (Excel/PDF), email notifications, and **productivity analysis through dynamic charts**.

This version is a migration from an older Tkinter-based GUI to a more modern PyQt6 interface, with significant improvements in performance, usability, and features.

## 2. Key Technologies

- **GUI:** PyQt6
- **Database:** SQLite3
- **Data Analysis & Charting:** Pandas, Matplotlib
- **Data Export:** Openpyxl
- **PDF Generation:** ReportLab
- **Core Language:** Python 3

## 3. File and Directory Structure

This section details the role of each significant file and directory in the project.

### `/` (Root Directory)

- **`main_pyqt.py`**: **(Primary Entry Point)** This is the main script to run the application. It initializes the application, sets up the main window (`MainWindow`), connects signals/slots, and handles high-level application logic like data refreshing and report generation.
- **`pyqt_windows.py`**: **(UI Components)** Contains the definitions for all secondary windows and dialogs. This includes `EntryDialog` for new equipment, `ProductivityChartDialog` for displaying graphs, and the refactored `ManageEquipmentDialog`, which now acts as an orchestrator for its tab widgets (`InfoTab`, `WorkTab`, `CloseTab`, `ExitTab`).

- **`database_improved.py`**: **(Data Layer)** Defines the `Database` class, which abstracts all interactions with the SQLite database. It handles connections, executing queries (SELECT, INSERT, UPDATE), and error handling.

- **`file_utils.py`**: **(File System Logic)** Contains helper functions for file operations, such as `copy_document` (which handles creating versioned folders) and `open_file` (for opening documents with the default system application).

- **`email_utils.py`**: **(Communication Logic)** Provides the `send_email_notification` function. It's designed to open the user's default web browser (specifically Gmail) with a pre-filled draft, avoiding the need for SMTP credential management.

- **`validators.py`**: **(Business Logic)** A crucial module containing the `Validator` class. It centralizes all data validation rules (e.g., for Part Numbers, Serial Numbers, work hours) to ensure data integrity before it reaches the database.

- **`config.py`**: **(Configuration)** Centralizes application settings, such as the database name, log file name, and base directory for documents.

- **`logger.py`**: **(Logging)** Sets up the application-wide logger. It configures logging to a file (`app.log` or `control_equipos.log`) and the console, which is essential for debugging.

- **`ui_utils.py`**: **(UI Helpers)** Provides simple, reusable functions (`show_error`, `show_warning`, `show_info`) to display message boxes to the user. This abstracts the GUI toolkit's specific implementation.

- **`README.md`**: The main documentation file for human developers, explaining what the project is, its features, and how to run it.

- **`agents.md`**: **(This File)** Context for AI assistants to understand the project structure and purpose.

### `/icons`

This directory stores all the `.png` icon files used in the PyQt6 user interface (e.g., for toolbar buttons).

### `/docs`

This is a **dynamically generated directory**. The application creates it on first run if it doesn't exist. It serves as the root folder for all user-uploaded documents. The `file_utils.py` module manages a structured hierarchy within it: `docs/EquipoNombre/SN/ArisingXX/document.pdf`.

### Legacy and Test Files

- **`control_equipos.py`**: **(Legacy)** This is the old main script for the **Tkinter version** of the application. It is no longer the entry point but is kept for reference.

- **`test_tkinter.py`**: A simple script to verify that the Tkinter library is correctly installed and operational on the system. It is not part of the main application's test suite.

## 4. Execution Flow

1.  The user runs `py main_pyqt.py`.
2.  `setup_environment()` is called, which initializes the `Database` object and creates the database schema if it doesn't exist.
3.  An instance of `QApplication` is created.
4.  An instance of `MainWindow` is created. Its `__init__` method builds the main UI, populates the main table by calling `refresh_table()`, and then loads user settings (window size, column widths) by calling `load_settings()`.
5.  The application enters the Qt event loop (`app.exec()`).
6.  User interactions trigger methods in `MainWindow`.

### Dialog Interaction Flow (e.g., `ManageEquipmentDialog`)

1.  User double-clicks a row in `MainWindow`.
2.  `on_double_click` creates an instance of `ManageEquipmentDialog`.
3.  `ManageEquipmentDialog` creates instances of its child tab widgets (`InfoTab`, `WorkTab`, etc.), passing them the database session and equipment data.
4.  The user interacts with a tab (e.g., adds a log entry in `WorkTab`).
5.  `WorkTab` validates the data, updates the database, and emits a `data_saved` signal.
6.  `ManageEquipmentDialog` catches this signal in its `on_child_data_changed` slot.
7.  `on_child_data_changed` reloads the data from the database, passes the updated data to all child tabs so they refresh their UIs, and emits its own `data_changed` signal.
8.  `MainWindow` catches this final signal and calls `refresh_table()` to update the main view.

## 5. Generated Files at Runtime

- **`control_equipos.db`**: The SQLite database file. Created on the first run.
- **`docs/`**: The directory for user-uploaded documents. Created on the first run.
- **`control_equipos.log`**: The log file where all application events and errors are recorded.