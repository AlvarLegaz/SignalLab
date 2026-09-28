# gui_utils.py
import sys
import os
import tkinter as tk


def resource_path(relative_path):
    """
    Devuelve la ruta correcta tanto en modo .py como en .exe (PyInstaller)
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
