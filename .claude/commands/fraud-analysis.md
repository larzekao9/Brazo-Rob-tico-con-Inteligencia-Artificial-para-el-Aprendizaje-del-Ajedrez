# /fraud-analysis

Genera o modifica código del módulo de análisis de fraude con IA.

## Uso
```
/fraud-analysis <componente>
```
Componentes disponibles:
- `pipeline` — pipeline completo de análisis de un expediente
- `score` — modelo XGBoost de scoring de fraude
- `explain` — explicabilidad SHAP del score
- `inconsistency` — detección de inconsistencias con LangChain
- `duplicates` — detección de siniestros duplicados con Pinecone
- `celery-task` — tarea Celery que orquesta el pipeline
- `api` — endpoint para consultar resultados del análisis

## Qué genera / modifica

### `pipeline`
Tarea Celery `analyze_expediente` que ejecuta todos los pasos en secuencia y guarda el resultado en `FraudAnalysis`.

### `score`
Función `compute_fraud_score(expediente)` que extrae features y corre el modelo XGBoost. Incluye feature engineering desde el expediente.

### `explain`
Función `explain_score(model, features)` que genera valores SHAP y los serializa como lista de `{feature, value, impact}`.

### `inconsistency`
Cadena LangChain que compara la declaración del asegurado con los datos de la póliza y las evidencias, y retorna inconsistencias detectadas.

### `duplicates`
Función que genera el embedding del expediente, lo consulta en Pinecone (namespace del tenant) y retorna siniestros similares con score de similitud.

### `celery-task`
Tarea con `bind=True`, reintentos con backoff exponencial y guardado de resultado parcial si algún paso falla.

### `api`
Endpoint `GET /api/expedientes/{id}/fraud-analysis/` que retorna el último análisis disponible.

## Instrucciones
1. El análisis IA es solo para planes Professional y Enterprise — valida el plan del tenant.
2. Usa el agente `ai-fraud` para la implementación.
3. Todos los prompts de LangChain se guardan en BD para auditoría.
