"""
Funciones utilitarias para los agentes
"""

def safe_stringify(obj):
    """Convierte cualquier objeto a string de manera segura, manejando objetos personalizados."""
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, (int, float, bool)):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: safe_stringify(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_stringify(v) for v in obj]
    elif obj is None:
        return ""
    else:
        return str(obj)
