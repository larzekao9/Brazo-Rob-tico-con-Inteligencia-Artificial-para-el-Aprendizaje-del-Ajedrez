# /api-endpoint

Genera un endpoint REST completo con DRF para la plataforma de Gestión de Siniestros.

## Uso
```
/api-endpoint <modelo> <accion>
```
Ejemplos:
- `/api-endpoint Expediente list`
- `/api-endpoint Expediente create`
- `/api-endpoint FraudAnalysis retrieve`

## Qué genera

### 1. Serializer (`serializers.py`)
- Fields explícitos (no `fields = '__all__'`)
- Validaciones en `validate_<field>` para reglas de negocio
- Serializer de lectura y escritura separados si la complejidad lo justifica

### 2. ViewSet o APIView (`views.py`)
- Permiso de autenticación + permiso de rol
- Filtrado obligatorio por tenant del usuario autenticado
- Paginación con `PageNumberPagination`
- Documentación drf-spectacular con `@extend_schema`

### 3. URL (`urls.py`)
- Ruta registrada en el router del módulo

### 4. Tests (`tests/test_api.py`)
- Test de acceso autorizado (rol correcto)
- Test de acceso denegado (rol incorrecto)
- Test del happy path de la acción
- Test de validación fallida

## Instrucciones
1. Lee el modelo existente antes de generar el serializer.
2. Asegúrate de que el queryset filtre por `request.user.tenant`.
3. Registra la acción en el audit log si modifica datos.
4. Usa el agente `backend-django` para la implementación.
