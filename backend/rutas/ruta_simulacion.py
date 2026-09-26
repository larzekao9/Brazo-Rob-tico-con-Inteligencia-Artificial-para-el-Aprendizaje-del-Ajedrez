"""Endpoint HTTP para abrir la ventana 3D en vivo (PyBullet) desde la Sala de Control.

Pensado para uso local de desarrollo/demo: ejecuta un proceso arbitrario en la
máquina donde corre este backend (ver `servicio_simulacion_3d.py`). No hace
falta hardening de inyección de comandos porque los argumentos van como lista
a `Popen`, no como string de shell.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.esquemas.simulacion_esquema import AbrirVentana3DRequest, AbrirVentana3DResponse
from backend.rutas.ruta_auth import get_current_user, security
from backend.servicios.partida.servicio_simulacion_3d import lanzar_ventana_3d

router = APIRouter(prefix="/simulacion", tags=["simulacion"])


@router.post("/abrir-ventana-3d", response_model=AbrirVentana3DResponse)
def abrir_ventana_3d(
    request: AbrirVentana3DRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _usuario_id: int = Depends(get_current_user),
) -> AbrirVentana3DResponse:
    """Lanza `ver_partida_en_vivo.py` como proceso aparte, con el token del usuario actual.

    Requiere `Authorization: Bearer <token>` (HU10) — ese mismo token crudo se
    le pasa al script lanzado, porque necesita autenticarse él mismo contra
    `GET /partida/{id}`. No espera a que el proceso termine: responde apenas
    lo lanza, la ventana queda corriendo aparte hasta que se cierre.
    """
    try:
        lanzar_ventana_3d(request.partida_id, credentials.credentials)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return AbrirVentana3DResponse(lanzado=True)
