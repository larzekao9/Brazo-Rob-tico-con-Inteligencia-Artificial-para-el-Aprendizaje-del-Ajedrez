# /new-module

Crea el scaffold completo de un nuevo módulo Django para la plataforma de Gestión de Siniestros.

## Uso
```
/new-module <nombre-del-modulo>
```

## Qué genera
Dado el nombre del módulo (ej. `polizas`), crea la estructura estándar del proyecto:

```
apps/<nombre>/
├── __init__.py
├── admin.py          ← registro en Django admin
├── apps.py           ← AppConfig con label
├── models.py         ← modelos con UUID pk, timestamps y soft delete
├── serializers.py    ← serializers DRF con validaciones
├── views.py          ← ViewSets con permisos de rol
├── urls.py           ← router con el ViewSet registrado
├── permissions.py    ← clases de permiso por rol (Admin/Supervisor/Analista)
├── tasks.py          ← tareas Celery si el módulo las necesita
├── signals.py        ← señales post_save para audit log y Elasticsearch
└── tests/
    ├── __init__.py
    ├── factories.py  ← factory_boy factories
    ├── test_models.py
    └── test_api.py   ← tests de endpoints con pytest-django
```

## Instrucciones
1. Pregunta al usuario qué entidades (modelos) tiene el módulo y sus campos principales.
2. Genera cada archivo siguiendo las convenciones del proyecto (UUID pk, multi-tenant, audit log).
3. Registra la app en `INSTALLED_APPS` y agrega las URLs al `urls.py` principal.
4. Usa el agente `backend-django` para la implementación.
