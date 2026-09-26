try:
    from .escena import (
        cargar_formas_visuales_piezas,
        cerrar_escena,
        crear_escena,
        resaltar_jugada,
        sincronizar_piezas,
    )
    __all__ = [
        "crear_escena",
        "resaltar_jugada",
        "sincronizar_piezas",
        "cargar_formas_visuales_piezas",
        "cerrar_escena",
    ]
except ImportError:
    __all__ = []
