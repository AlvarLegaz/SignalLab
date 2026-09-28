# ==============================
# Utilidades - Funciones para valores seguros
# ==============================

def safe_get(var, default):
    try:
        v = var.get()
        if v == "" or v is None:
            return default
        return float(v)
    except Exception:
        return default
    
def safe_int(var, default):
    """
    Devuelve un entero seguro desde una variable Tk.
    """
    try:
        v = var.get()
        if v == "" or v is None:
            return default
        return int(float(v))
    except Exception:
        return default

def safe_float(var, default):
    """
    Devuelve un float seguro desde una variable Tk.
    """
    try:
        v = var.get()
        if v == "" or v is None:
            return default
        return float(v)
    except Exception:
        return default