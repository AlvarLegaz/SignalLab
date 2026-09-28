# gui_utils.py
import sys
import os


def resource_path(relative_path):
    """
    Devuelve la ruta correcta tanto en modo .py como en .exe (PyInstaller)
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        # La carpeta de este fichero, no la carpeta desde la que se lanza el
        # programa: así 'python ruta/a/main.py' funciona desde cualquier sitio.
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)
