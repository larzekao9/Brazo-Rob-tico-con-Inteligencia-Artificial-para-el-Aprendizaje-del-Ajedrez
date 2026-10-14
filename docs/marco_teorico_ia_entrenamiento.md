# Marco Teórico y Metodológico: Modelo de Inteligencia Artificial para la Toma de Decisiones en Ajedrez

**Proyecto de Grado:** Sistema Tutor Inteligente de Ajedrez (con brazo robótico como recurso de práctica y motivación)  
**Autores:** Suárez Burgos Hebert · Arze Kao Luis Ángel  
**Carrera:** Ingeniería Informática  
**Institución:** Universidad Autónoma Gabriel René Moreno (UAGRM) — Facultad de Ciencias de la Computación y Telecomunicaciones  
**Fecha:** Octubre de 2026 (actualizado el 2026-10-13)

> **Nota de actualización (2026-10-13).** Este documento se revisó contra las mediciones reales del repositorio. Cambios:
> (1) se agregó la versión **v6**, con validación por partida entera (§5.2, §7.3); (2) se midió la **fuerza de juego en
> partidas completas** y se estimó su Elo (§7.4, §13); (3) se agregó la **búsqueda de variantes** de Turing (§12);
> (4) se **corrigieron afirmaciones que las mediciones no respaldan**: la prevención de fuga de información de la v5 (§5.2),
> la tasa de errores graves en juego real (§7.2 y Fase 5), el número de parámetros y las analogías de "edad cognitiva" y
> "maestría FIDE" de la §8, que no equivalen a fuerza de juego. Todos los números de tablas provienen de ejecuciones
> reproducibles (`training/evaluar_modelo.py`, `training/enfrentar_modelos.py`, `training/medir_elo.py`).

---

## 1. Introducción y Justificación Teórica

El diseño de un sistema automatizado para el aprendizaje y juego del ajedrez tradicionalmente se ha fundamentado en motores de búsqueda heurística sobre árboles de juego, tales como Minimax con poda Alfa-Beta y tablas de transposición (Russell & Norvig, 2020). Sistemas consagrados en la industria como _Stockfish_ operan mediante la evaluación exhaustiva de decenas de millones de posiciones por segundo combinadas con funciones de evaluación estática altamente optimizadas (Romstad et al., 2024).

Sin embargo, el objetivo pedagógico y diferencial de esta investigación no radica en la replicación de una búsqueda por fuerza bruta, sino en la **construcción de un agente autónomo basado en aprendizaje profundo (Deep Learning)** capaz de emular el razonamiento intuitivo humano. Tal como demostraron Silver et al. (2017) con _AlphaZero_ y McIlroy-Young et al. (2020) con _Maia Chess_, una red neuronal convolucional puede aprender a priorizar jugadas prometedoras directamente a partir de la configuración espacial de las piezas, prescindiendo de árboles de búsqueda profundos durante la inferencia inmediata.

En este marco, el sistema implementa una **Red de Política (Policy Network)** entrenada mediante clonación de comportamiento (Behavioral Cloning) sobre partidas de ajedrez federado y competitivo. De acuerdo con las directrices metodológicas del proyecto, **el modelo decide sus propias jugadas de manera 100% independiente sin consultar a Stockfish en el flujo de inferencia**, utilizando a este último exclusivamente como un **oráculo de evaluación comparativa** para la retroalimentación al jugador y la auditoría de calidad de las versiones del modelo (HU4/HU6).

Este trabajo mide además hasta dónde llega esa intuición por sí sola (la red de política sin cálculo juega al nivel de un aficionado, §7.4) y cuánto aporta agregarle un cálculo propio de pocas jugadas (§12), sin recurrir a motores externos para decidir.

---

## 2. Modelado Matemático del Espacio de Estados y Acciones

El juego de ajedrez se modela formalmente como un Proceso de Decisión de Markov (MDP) de información perfecta, determinado por la tupla $(\mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R})$, donde $\mathcal{S}$ representa el conjunto de estados válidos del tablero y $\mathcal{A}$ el espacio discreto de acciones legales (Sutton & Barto, 2018).

```mermaid
flowchart LR
    A["Tablero FEN / chess.Board"] --> B["Transformación Tensorial (8x8x12)"]
    B --> C["Red Neuronal (ResNet / CNN)"]
    C --> D["Vector de Logits (4096 clases)"]
    D --> E["Máscara de Jugadas Legales"]
    E --> F["Softmax & Selección de Jugada (SAN)"]
```

### 2.1 Representación Tensorial de Entrada ($\mathcal{X}$)

Para que una red neuronal convolucional procese una posición de ajedrez preservando las relaciones topológicas bidimensionales de la cuadrícula, el estado del tablero se codifica como un tensor tridimensional binario de dimensiones:

$$\mathbf{X} \in \{0, 1\}^{8 \times 8 \times 12}$$

Donde:

- Las dimensiones $8 \times 8$ corresponden a las 64 casillas del escaque (filas de 1 a 8, columnas de 'a' a 'h').
- La profundidad de 12 canales representa de forma One-Hot la presencia de cada tipo de pieza:
  - Canales $0$ a $5$: Piezas del **jugador en turno** en orden canónico: Peón ($P$), Caballo ($N$), Alfil ($B$), Torre ($R$), Dama ($Q$), Rey ($K$).
  - Canales $6$ a $11$: Piezas del **adversario** en el mismo orden: Peón ($p$), Caballo ($n$), Alfil ($b$), Torre ($r$), Dama ($q$), Rey ($k$).

#### Invariancia de Perspectiva (Rotación Canónica)

Para maximizar la eficiencia en el aprendizaje de parámetros y evitar que la red deba aprender dos veces los mismos principios tácticos (una para blancas y otra para negras), se aplica una función de transformación canónica $\rho(s, c)$ sobre el índice de casilla $s \in [0, 63]$ dependiente del color activo $c$:

$$\rho(s, c) = \begin{cases} s, & \text{si } c = \text{Blanco} \\ 63 - s, & \text{si } c = \text{Negro} \end{cases}$$

De este modo, la red siempre analiza la posición bajo la perspectiva de: _"mis piezas avanzan desde las filas inferiores hacia las superiores"_, duplicando efectivamente la densidad de entrenamiento sin aumentar el tamaño del dataset.

### 2.2 Espacio de Acciones y Codificación de Salida ($\mathcal{Y}$)

El espacio de acciones discretas en ajedrez convencional comprende cualquier movimiento originado en una casilla $s_{origen}$ con destino en $s_{destino}$. Prescindiendo temporalmente de la subpromoción múltiple (asumiendo promoción estándar a dama), el número total de transiciones posibles entre casillas se define como:

$$|\mathcal{Y}| = 64 \times 64 = 4096 \text{ clases}$$

La etiqueta de entrenamiento $y \in \{0, 1, \dots, 4095\}$ para un movimiento ejecutado se calcula mediante:

$$y = \rho(s_{origen}, c) \times 64 + \rho(s_{destino}, c)$$

#### Máscara de Legalidad (Legal Move Masking)

A diferencia de un clasificador estándar de imágenes donde cualquier clase es teóricamente admisible, en ajedrez la inmensa mayoría de las 4,096 clases son físicamente ilegales en una posición dada. Para garantizar el cumplimiento estricto de las reglas FIDE sin forzar a la red a converger a probabilidad cero en millones de variantes imposibles, se aplica una **máscara booleana de legalidad** $\mathcal{M}(s) \subseteq \mathcal{A}$ generada por el motor de reglas (`python-chess`):

$$\hat{y} = \arg\max_{a \in \mathcal{M}(s)} \mathbf{z}_a$$

donde $\mathbf{z} \in \mathbb{R}^{4096}$ es el vector de salida sin normalizar (logits) producido por la red.

---

## 3. Arquitecturas Neuronales Desarrolladas

En el marco del proyecto se diseñaron dos generaciones de arquitecturas, documentadas en `backend/servicios/aprendizaje/modelo_jugadas.py`:

### 3.1 Arquitectura Convolucional Clásica (Versión v1 / v2)

Diseñada inicialmente para validar la viabilidad del pipeline de datos de punta a punta. Se compone de tres capas convolucionales planas seguidas de normalización por lotes (Batch Normalization) y una cabeza completamente conectada:

$$\mathbf{h}_1 = \text{ReLU}(\text{BN}(\text{Conv2D}_{3 \times 3}(12 \to 64, \text{pad}=1)))$$
$$\mathbf{h}_2 = \text{ReLU}(\text{BN}(\text{Conv2D}_{3 \times 3}(64 \to 128, \text{pad}=1)))$$
$$\mathbf{h}_3 = \text{ReLU}(\text{BN}(\text{Conv2D}_{3 \times 3}(128 \to 128, \text{pad}=1)))$$
$$\mathbf{z} = \mathbf{W}_2 \cdot \text{Dropout}_{0.3}(\text{ReLU}(\mathbf{W}_1 \cdot \text{vec}(\mathbf{h}_3) + \mathbf{b}_1)) + \mathbf{b}_2$$

_Limitación identificada:_ Al carecer de conexiones residuales, redes planas con más de 3 o 4 capas sufren degradación del gradiente, limitando su capacidad para modelar conceptos posicionales profundos como clavadas o ataques descubiertos.

### 3.2 Arquitectura ResNet con Bloques Residuales (Versión v3 Avanzada)

Inspirada en la formulación de _Deep Residual Learning_ (He et al., 2016), la versión `v3` incorpora conexiones de salto (_skip connections_) que posibilitan un entrenamiento más profundo y estable.

```mermaid
graph TD
    In["Entrada x (Tensor 12x8x8)"] --> ConvIn["Conv2D 3x3 (12 -> 128) + BN + ReLU"]

    subgraph BloqueResidual ["Bloque Residual (x4 veces)"]
        RIn["Entrada de Bloque x"] --> C1["Conv2D 3x3 (128 -> 128) + BN + ReLU"]
        C1 --> C2["Conv2D 3x3 (128 -> 128) + BN"]
        RIn -.-> Sum["Suma Residual: F(x) + x"]
        C2 --> Sum
        Sum --> Act["ReLU"]
    end

    ConvIn --> BloqueResidual
    BloqueResidual --> PolHead["Cabeza de Política: Conv2D 1x1 (128 -> 32) + BN + ReLU"]
    PolHead --> Dense["Linear(2048 -> 512) + ReLU + Dropout(0.3)"]
    Dense --> Out["Linear(512 -> 4096) [Logits]"]
```

#### Formulación del Bloque Residual

Cada bloque residual implementa la función:

$$\mathbf{y}_l = \sigma\Big(\mathbf{x}_l + \mathcal{F}(\mathbf{x}_l, \mathcal{W}_l)\Big)$$

donde $\sigma(\cdot)$ representa la activación ReLU y $\mathcal{F}$ corresponde a:

$$\mathcal{F}(\mathbf{x}_l) = \text{BN}_2\Big(\mathbf{W}_{2,l} * \sigma\big(\text{BN}_1(\mathbf{W}_{1,l} * \mathbf{x}_l)\big)\Big)$$

La conexión de identidad directa $\mathbf{x}_l$ permite que el flujo de información durante la retropropagación viaje sin atenuación:

$$\frac{\partial \mathcal{E}}{\partial \mathbf{x}_l} = \frac{\partial \mathcal{E}}{\partial \mathbf{x}_L} \frac{\partial \mathbf{x}_L}{\partial \mathbf{x}_l} = \frac{\partial \mathcal{E}}{\partial \mathbf{x}_L} \left( \mathbf{I} + \frac{\partial}{\partial \mathbf{x}_l} \sum_{i=l}^{L-1} \mathcal{F}(\mathbf{x}_i, \mathcal{W}_i) \right)$$

Esto garantiza que el término $\mathbf{I}$ prevenga el desvanecimiento del gradiente independientemente de la profundidad de la torre residual (He et al., 2016).

### 3.3 Arquitectura Squeeze-and-Excitation ResNet (Versiones v4 y v5)

Para superar las limitaciones de las redes residuales convencionales y modelar la **atención selectiva visual** inherente a los ajedrecistas de alta competencia, las versiones `v4` y `v5` implementan la clase `RedSEResNetAjedrez` incorporando bloques _Squeeze-and-Excitation_ (SE) (Hu et al., 2018).

```mermaid
graph TD
    In["Entrada x (Tensor C x 8 x 8)"] --> C1["Conv2D 3x3 (C -> C) + BN + ReLU"]
    C1 --> C2["Conv2D 3x3 (C -> C) + BN"]

    subgraph BloqueSE ["Mecanismo Squeeze-and-Excitation (Recalibración Adaptativa)"]
        GAP["Squeeze: AdaptiveAvgPool2d(1) -> Vector z (C x 1 x 1)"]
        FC1["Excitation 1: Linear(C -> C // r) + ReLU"]
        FC2["Excitation 2: Linear(C // r -> C) + Sigmoid -> Vector de Pesos s"]
        Scale["Scale: Multiplicación Canal a Canal (s * U)"]
        GAP --> FC1 --> FC2 --> Scale
    end

    C2 --> GAP
    C2 --> Scale
    In -.-> Sum["Suma Residual: F_SE(x) + x"]
    Scale --> Sum
    Sum --> Act["ReLU"]
```

#### Formulación Matemática del Bloque SE

Sea $\mathbf{U} = [\mathbf{u}_1, \mathbf{u}_2, \dots, \mathbf{u}_C] \in \mathbb{R}^{C \times 8 \times 8}$ el tensor generado tras las convoluciones y normalizaciones del bloque residual. El operador SE realiza:

1. **Compresión (_Squeeze_):** Agrega la información espacial del tablero ($8 \times 8$) para cada canal en un descriptor estadístico escalar $z_c$:
   $$z_c = \mathbf{F}_{sq}(\mathbf{u}_c) = \frac{1}{64} \sum_{i=1}^{8} \sum_{j=1}^{8} u_c(i, j), \quad \forall c \in \{1, \dots, C\}$$

2. **Excitación no lineal (_Excitation_):** Captura las correlaciones y dependencias cruzadas entre piezas aliadas y rivales mediante un mecanismo bottleneck con reducción $r = 8$:
   $$\mathbf{s} = \mathbf{F}_{ex}(\mathbf{z}, \mathbf{W}) = \sigma\Big(\mathbf{W}_2 \cdot \text{ReLU}(\mathbf{W}_1 \cdot \mathbf{z})\Big)$$
   donde $\mathbf{W}_1 \in \mathbb{R}^{\frac{C}{r} \times C}$ contrae la dimensionalidad, $\mathbf{W}_2 \in \mathbb{R}^{C \times \frac{C}{r}}$ la restituye y $\sigma(v) = \frac{1}{1 + e^{-v}}$ acota las ponderaciones en $[0, 1]$.

3. **Recalibración de Características (_Scale_):** Re-pondera dinámicamente cada canal según su relevancia táctica en la posición actual (por ejemplo, amplificando canales asociados a columnas semiabiertas o casillas del enroque amenazado):
   $$\tilde{\mathbf{x}}_c = \mathbf{F}_{scale}(\mathbf{u}_c, s_c) = s_c \cdot \mathbf{u}_c$$

#### Escalado Estructural entre Versiones:

- **Modelo v4:** 6 bloques residuales SE con $C = 128$ canales (~1.8M de parámetros entrenables).
- **Modelo v5 (Consolidación):** 8 bloques residuales SE con $C = 192$ canales (8.565.952 parámetros), con mayor capacidad representacional para discernir patrones posicionales. La v6 conserva esta misma arquitectura.

---

## 4. Función de Pérdida, Optimización y Regularización

### 4.1 Entropía Cruzada Categórica (Cross-Entropy Loss) y Label Smoothing

El aprendizaje por imitación se formula como la minimización de la divergencia entre la distribución de probabilidad predicha por la red $\hat{\mathbf{p}}$ y la distribución empírica de la jugada del experto $\mathbf{y} \in \{0, 1\}^K$:

$$\mathcal{L}_{CE}(\mathbf{y}, \hat{\mathbf{p}}) = - \sum_{k=1}^{K} y_k \log(\hat{p}_k) = - \log(\hat{p}_{a^*})$$

donde $a^*$ representa la acción seleccionada por el jugador humano de referencia y $\hat{p}_k$ se calcula mediante la función Softmax:

$$\hat{p}_k = \frac{\exp(z_k)}{\sum_{j=1}^{K} \exp(z_j)}$$

#### Regularización por Suavizado de Etiquetas (Label Smoothing)

En el ajedrez magistral coexisten con frecuencia dos o tres jugadas de idéntica solidez teórica. Forzar a la red a predecir con probabilidad $1.0$ una única variante genera dogmatismo y penaliza indebidamente jugadas maestras alternativas válidas (Müller et al., 2019). Para mitigar este efecto, en las versiones avanzadas (`v4` y `v5`) se introduce _Label Smoothing_ con parámetro $\alpha = 0.05$:

$$y_k^{LS} = (1 - \alpha) y_k + \frac{\alpha}{K}$$

Esto previene la saturación de los logits y fomenta una política calibrada con mayor plasticidad táctica.

### 4.2 Optimizador AdamW (Decoupled Weight Decay)

Se emplea el algoritmo **AdamW** propuesto por Loshchilov y Hutter (2019), el cual desacopla el decaimiento de pesos ($L_2$ regularization) del cálculo de momentos adaptativos del gradiente, evitando la reducción desproporcionada de pesos en parámetros con gradientes dispersos:

$$\mathbf{m}_t = \beta_1 \mathbf{m}_{t-1} + (1 - \beta_1) \mathbf{g}_t$$
$$\mathbf{v}_t = \beta_2 \mathbf{v}_{t-1} + (1 - \beta_2) \mathbf{g}_t^2$$
$$\hat{\mathbf{m}}_t = \frac{\mathbf{m}_t}{1 - \beta_1^t}, \quad \hat{\mathbf{v}}_t = \frac{\mathbf{v}_t}{1 - \beta_2^t}$$
$$\boldsymbol{\theta}_t = \boldsymbol{\theta}_{t-1} - \eta_t \left( \frac{\hat{\mathbf{m}}_t}{\sqrt{\hat{\mathbf{v}}_t} + \epsilon} + \lambda \boldsymbol{\theta}_{t-1} \right)$$

Parámetros configurados:

- Tasa de aprendizaje base: $\eta_0 = 10^{-3}$
- Factor de decaimiento de pesos: $\lambda = 10^{-4}$
- Coeficientes de momento: $\beta_1 = 0.9, \beta_2 = 0.999, \epsilon = 10^{-8}$

### 4.3 Planificador de Tasa de Aprendizaje: Cosine Annealing

Para garantizar una convergencia suave hacia mínimos locales de alta generalización sin oscilaciones abruptas en las etapas finales, se utiliza la política de recocido por coseno (Loshchilov & Hutter, 2017):

$$\eta_t = \eta_{min} + \frac{1}{2}(\eta_{max} - \eta_{min})\left(1 + \cos\left(\frac{t}{T_{max}}\pi\right)\right)$$

donde $T_{max}$ equivale al número total de épocas de entrenamiento ($T_{max} = 15$) y $\eta_{min} = 10^{-6}$.

---

## 5. Curaduría del Corpus y Mitigación de Sesgos

### 5.1 Filtrado de Calidad por ELO ($\ge 1900$)

En sistemas supervisados aplica el axioma fundamental: _Garbage In, Garbage Out_. Un modelo entrenado indiscriminadamente sobre partidas públicas aprende tanto las buenas jugadas como los errores graves (_blunders_) de jugadores aficionados.

En la versión `v3`, el cargador de streaming `training/data_pipeline.py` implementa un filtro de admisión basado en las cabeceras PGN:

$$\text{Filtro}(p) = \begin{cases} \text{Admitir}, & \text{si } \min(\text{WhiteElo}(p), \text{BlackElo}(p)) \ge 1900 \\ \text{Descartar}, & \text{en caso contrario} \end{cases}$$

Esto asegura que las posiciones de entrenamiento provengan de partidas donde ambos participantes poseen nivel de candidato a maestro o superior, modelando aperturas teóricas depuradas y planes tácticos sólidos.

Las versiones v4 y v5 usaron el umbral de 2000 y la **v6 el de 2200** (siempre sobre ambos jugadores). La elección se hizo con datos: contando las partidas del archivo de Lichess de febrero de 2017 (primeras 3.000.000 de partidas), las que cumplen el filtro en ambos jugadores son:

| ELO mínimo (ambos jugadores) | Partidas | % del total leído |
| :--- | ---: | ---: |
| 2000 | 197.432 | 6,58 % |
| 2200 | 38.277 | 1,28 % |
| 2300 | 14.500 | 0,48 % |
| 2400 | 5.093 | 0,17 % |
| 2500 | 1.527 | 0,05 % |

Un umbral de 2300 dejaba solo 14.500 partidas (apenas más que las 12.000 de la v5); el de 2200 permitió usar 35.000 partidas de jugadores fuertes.

### 5.2 Prevención de Fuga de Información (Data Leakage)

A diferencia de problemas de visión artificial estándar donde las imágenes son independientes e idénticamente distribuidas (i.i.d.), en ajedrez **posiciones consecutivas de una misma partida comparten un alto grado de correlación espacial**.

Si el split de entrenamiento y validación se realiza a nivel de posiciones individuales aleatorias, la red memoriza posiciones previas de la misma partida en el conjunto de entrenamiento y "adivina" el resultado en validación, reportando métricas falsamente infladas (Kaufman et al., 2012).

**Qué ocurrió en este proyecto (corrección del 2026-10-13).** En la v5 (y anteriores) la validación del entrenamiento se hizo mezclando posiciones sueltas en una proporción 90/10, de modo que posiciones de una misma partida quedaron a ambos lados del corte: la precisión de validación reportada para la v5 (42,1 %) es, por lo tanto, **optimista**. Además, la evaluación original (`saltar_partidas = 35000`) omitía partidas del archivo en bruto sin garantizar que quedaran fuera de la zona usada para entrenar (la v5 consumió las primeras 12.000 partidas que cumplían el filtro de ELO, que se extienden mucho más allá de la partida 35.000 del archivo), y evaluaba partidas de cualquier nivel.

**Corrección aplicada en la v6** (`training/data_pipeline.py::pgn_a_muestras_divididas`):

- La separación entrenamiento/validación se hace **por partida entera**: cada partida va completa a un lado (el 3 % de las partidas a validación, con semilla fija). Ninguna posición de una partida de validación aparece en entrenamiento.
- La extracción registra hasta qué partida del archivo llegó (`partidas_crudas_leidas`); la evaluación comparativa usa partidas **posteriores** a ese punto (con un margen de 1.000) y **solo de maestros** (`evaluar_modelo(..., elo_minimo=...)`), así ninguna versión comparada las vio.
- Las posiciones se guardan como `uint8` (768 bytes en lugar de 3.072), lo que permite entrenar con millones de posiciones en la memoria de Colab.

Por esta razón la precisión de validación de la v6 **no es comparable** con la reportada para la v5: la comparación válida entre versiones es la del §7.3, con las mismas partidas nuevas para ambas.

---

## 6. Marco de Evaluación Científica, Indicadores Pedagógicos y el Oráculo de Stockfish (HU4 / HU5 / HU6)

Evaluar un modelo de ajedrez exclusivamente por _Accuracy Top-1_ resulta insuficiente: en muchas posiciones existen dos o tres jugadas de idéntica calidad teórica. Si el gran maestro jugó $1.\,\text{c4}$ y el modelo predice $1.\,\text{Nf3}$, el Accuracy tradicional contabiliza un error (0%), a pesar de que ambas son jugadas maestras de primer nivel.

Por ello, el sistema implementa una infraestructura integral de evaluación de doble eje en `training/evaluar_modelo.py` y un motor de tutoría pedagógica y análisis en tiempo real en `backend/servicios/retroalimentacion/servicio_retroalimentacion.py`:

### 6.1 Métrica 1: Exactitud Top-1 Humano (Top-1 Accuracy)

Mide la fidelidad del modelo frente a la toma de decisiones humana experta en partidas federadas:

$$\text{Accuracy}_{Top-1} = \frac{\sum_{i=1}^{M} \mathbb{I}(\hat{y}_i = y_i^*)}{M} \times 100\%$$

### 6.2 Métrica 2: Pérdida en Centipawns (Centipawn Loss - CPL)

Para cada jugada donde el modelo discrepa del humano ($\hat{y} \ne y^*$), o para auditar las decisiones del usuario frente al oráculo, se invoca a Stockfish como **árbitro objetivo de fuerza** para medir el deterioro de la posición en centipawns ($1 \text{ peón} = 100 \text{ cp}$):

$$\Delta_{cp}(s, a) = \max\Big(0, \; \mathcal{E}_{motor}(s) - \big(-\mathcal{E}_{motor}(s')\big)\Big)$$

donde $\mathcal{E}_{motor}(s)$ representa la evaluación de la mejor jugada según Stockfish en la posición previa, y $-\mathcal{E}_{motor}(s')$ es la evaluación del motor en la posición resultante tras ejecutar la jugada $a$ (invirtiendo el signo para preservar la perspectiva del jugador evaluado).

### 6.3 Taxonomía Exhaustiva de Indicadores de Calidad de Jugada (Lichess & FIDE Digital)

En correspondencia con los estándares modernos de las plataformas internacionales de ajedrez (Lichess y Chess.com) y para cumplir con los requerimientos pedagógicos del proyecto (**RF18** y **RF20**), las decisiones se clasifican formalmente en siete niveles jerárquicos:

| Indicador                | Etiqueta en Sistema | Criterio Matemático y Táctico                                                                                            | Significado Pedagógico                                                                       |
| :----------------------- | :------------------ | :----------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------- |
| 💎 **Brillante**         | `brillante`         | Sacrificio de material ventajoso ($Val(P_{sac}) > 0$) o jugada táctica única de alta profundidad con $P_{win} \ge 60\%$. | Decisión táctica magistral que supera la visión convencional y desarticula la defensa rival. |
| ⭐ **Mejor Jugada**      | `mejor`             | $\hat{a} = a_{oraculo}^*$ o pérdida mínima imperceptible $\Delta_{cp} \le 10 \text{ cp}$.                                | La jugada óptima teórica según el oráculo de cálculo profundo.                               |
| ✨ **Excelente**         | `excelente`         | $10 < \Delta_{cp} \le 30 \text{ cp}$.                                                                                    | Movimiento casi perfecto que conserva la totalidad de la ventaja estratégica.                |
| 👍 **Buena**             | `buena`             | $30 < \Delta_{cp} < 50 \text{ cp}$.                                                                                      | Movimiento sólido, aceptable y funcional que mantiene la estabilidad de la posición.         |
| ⚠️ **Imprecisión**       | `imprecision`       | $50 \le \Delta_{cp} < 100 \text{ cp}$ (pérdida entre medio y un peón).                                                   | Desviación posicional leve que cede parte de la iniciativa o disminuye el dinamismo.         |
| ❌ **Error**             | `error`             | $100 \le \Delta_{cp} < 300 \text{ cp}$ (pérdida de 1 a 3 peones).                                                        | Fallo táctico relevante que transfiere ventaja al contrincante.                              |
| 🛑 **Blunder (Colgada)** | `blunder`           | $\Delta_{cp} \ge 300 \text{ cp}$ o transición que permite jaque mate forzado ($mate\_en \le -1$).                        | Error grave catastrófico: pérdida neta de pieza o desprotección letal del rey.               |

### 6.4 Modelo Logístico de Probabilidad de Victoria (Curva Lichess Win%)

Presentar al estudiante principiante un valor numérico abstracto como `+2.45 cp` o `-1.12 cp` resulta pedagógicamente confuso e ineficaz para niños o aficionados. Para la barra de ventaja interactiva en tiempo real (**HU6**), el sistema traduce los centipawns a una escala probabilística continua $P_{win} \in [0.0\%, 100.0\%]$ mediante la **curva logística sigmoidea oficial de Lichess**:

$$P_{win}(cp) = 50 + 50 \times \left( \frac{2}{1 + \exp(-k \cdot cp)} - 1 \right)$$

donde $k = 0.00368208$ representa la constante empírica calibrada sobre cientos de millones de partidas maestras de torneos.

#### Propiedades Matemáticas y Puntos Notables:

1. **Punto Neutro (Equilibrio Inicial):** Para una posición teóricamente igualada ($cp = 0$):
   $$P_{win}(0) = 50 + 50 \times \left( \frac{2}{1 + 1} - 1 \right) = 50.0\%$$
2. **Monotonía y Simetría Perfecta:** $P_{win}(cp) = 100 - P_{win}(-cp)$, preservando neutralidad e invariancia entre ambos bandos.
3. **Comportamiento Asintótico:**
   $$\lim_{cp \to +\infty} P_{win}(cp) = 100.0\%, \quad \lim_{cp \to -\infty} P_{win}(cp) = 0.0\%$$
4. **Sensibilidad Práctica ante Desbalances Materiales Estándar:**
   - **Ventaja de 1 Peón ($cp = +100$):** $P_{win} \approx 59.1\%$ (ligera iniciativa ganadora).
   - **Ventaja de 1 Pieza Menor ($cp = +300$):** $P_{win} \approx 76.5\%$ (ventaja táctica decisiva).
   - **Ventaja de 1 Torre ($cp = +500$):** $P_{win} \approx 87.2\%$ (posición ganada casi incuestionable).
   - **Ventaja de 1 Dama ($cp = +900$):** $P_{win} \approx 96.6\%$ (victoria virtualmente asegurada).
5. **Tratamiento Formal de Redes de Jaque Mate Forzado:**
   $$P_{win}(\text{mate}) = \begin{cases} 100.0\%, & \text{si } mate > 0 \text{ (mate forzado a favor)} \\ 0.0\%, & \text{si } mate < 0 \text{ (mate forzado en contra)} \end{cases}$$

#### Justificación Pedagógica (HU6):

La reducción de la carga cognitiva es sustancial: un estudiante escolar no requiere saber qué es un "centipeón", sino que visualiza en la interfaz una barra dinámica que refleja qué jugador tiene el control del tablero, reforzando la relación causa-efecto de cada decisión inmediata.

### 6.5 Algoritmo de Detección de Principios Ajedrecísticos (Tutoría Pedagógica HU5 / HU6)

El módulo `backend/servicios/retroalimentacion/servicio_retroalimentacion.py::explicar_jugada` analiza la transición entre los estados del tablero antes y después de cada movimiento, transformando la evaluación matemática en retroalimentación formativa estructurada (**RF19**):

1. **Seguridad del Rey y Enroque (`seguridad_del_rey`):** Reconoce movimientos de enroque (`O-O` y `O-O-O`), destacando cómo la maniobra traslada al monarca a un flanco seguro y activa la torre hacia columnas abiertas.
2. **Detección de Piezas Indefensas y Colgadas (`pieza_indefensa`):** Computa el balance de atacantes y defensores en la casilla de destino:
   $$\mathcal{A}_{rival} = \text{Attackers}_{rival}(s_{dest}), \quad \mathcal{D}_{propio} = \text{Attackers}_{propio}(s_{dest})$$
   Si $\mathcal{A}_{rival} \ne \emptyset$ y $(\mathcal{D}_{propio} = \emptyset \lor \min_{a \in \mathcal{A}} Val(a) < Val(p))$, el algoritmo alerta que la pieza quedó desprotegida o bajo asedio de menor valor, instruyendo al usuario a retirarla o protegerla antes de ejecutar la jugada.
3. **Oportunidad Táctica Desaprovechada (`oportunidad_tactica`):** Si la jugada efectuada incurre en pérdida sustancial ($\Delta_{cp} \ge 50$) y la mejor jugada omitida $a_{oraculo}^*$ realizaba una captura material, se explicita qué pieza enemiga desprotegida se dejó escapar.
4. **Principios de Apertura (`control_del_centro`, `desarrollo_piezas`):** Durante los primeros 8 turnos de la partida:
   - Premia el avance de peones a las cuatro casillas centrales vitales $\{e4, d4, e5, d5\}$.
   - Recompensa el desarrollo activo y armónico de caballos y alfiles.
   - Señala como imprecisión mover peones laterales de flanco si aún no se han desarrollado las piezas menores.
5. **Iniciativa Táctica y Jaques (`iniciativa_tactica`):** Identifica jugadas de jaque que arrebatan los tiempos al oponente y fuerzan respuestas pasivas.

### 6.6 Métrica de Precisión Global Ponderada de la Partida

Para la vista resumen post-partida (**HU5**), el sistema consolida el rendimiento integral mediante una media ponderada en escala $0$ a $100$:

$$\text{Precisión Global} = \frac{1}{N} \sum_{i=1}^{N} w(q_i)$$

con los siguientes coeficientes empíricos según la calidad de cada jugada $q_i$:

- $w(\text{brillante}) = 100.0$
- $w(\text{mejor}) = 100.0$
- $w(\text{excelente}) = 95.0$
- $w(\text{buena}) = 80.0$
- $w(\text{imprecisión}) = 50.0$
- $w(\text{error}) = 20.0$
- $w(\text{blunder}) = 0.0$

A partir de esta distribución, el tutor genera un diagnóstico pedagógico formativo automatizado: orientando hacia la visión táctica preventiva si existen $\ge 2$ blunders, aconsejando mejorar la coordinación de piezas menores si predominan imprecisiones, o elogiando la solidez de Gran Maestro si la precisión supera el $80\%$.

---

## 7. Resultados Experimentales y Comparativa Empírica (v2 a v6)

La evaluación científica se ejecutó sobre partidas de prueba no vistas durante las fases de entrenamiento (`saltar_partidas = 6000` en v3, `15000` en v4 y `35000` en v5), contrastando cada predicción de las distintas redes neuronales contra la evaluación objetiva del oráculo Stockfish.

### 7.1 Tabla Comparativa del Desarrollo Cognitivo Cuadrupartito

| Métrica de Desempeño                          | Modelo v2 (CNN base) | Modelo v3 (ResNet 4B) | Modelo v4 (SE-ResNet 6B) | Modelo v5 (SE-ResNet 8B) |     Salto Total (v2 $\to$ v5)      |
| :-------------------------------------------- | :-----------------------------: | :------------------------------: | :----------------------------------: | :---------------------------------------: | :--------------------------------: |
| **Total Jugadas Evaluadas**                   |              1,426              |              1,204               |                1,231                 |                 **1,421**                 |                 -                  |
| **Aciertos Exactos (Top-1)**                  |          26.58% (379)           |           37.54% (452)           |             37.86% (466)             |             **41.87% (595)**              |    **+15.29% (+57.5% rel.)** 🚀    |
| **Alternativas Aceptables (< 50 cp)**         |          27.42% (391)           |           27.16% (327)           |             32.49% (400)             |             **32.86% (467)**              |       **+5.44% de solidez**        |
| **Total Jugadas Sólidas/Viables**             |          54.00% (770)           |           64.70% (779)           |             70.35% (866)             |            **74.74% (1,062)**             |  **+20.74% (Casi 75% sólido)** 🏆  |
| **Imprecisiones (50–99 cp)**                  |          11.57% (165)           |           10.96% (132)           |             9.02% (111)              |              **7.88% (112)**              |           **-3.69%** 📉            |
| **Errores Posicionales (100–299 cp)**         |          15.08% (215)           |           12.29% (148)           |              8.04% (99)              |              **8.80% (125)**              |             **-6.28%**             |
| **Blunders / Cuelgues Graves ($\ge 300$ cp)** |          19.35% (276)           |           12.04% (145)           |             12.59% (155)             |              **8.59% (122)**              | **-10.76% (Menos de la mitad)** 🛡️ |

> **Nota metodológica (2026-10-13).** Las cifras de esta tabla corresponden a la evaluación original de cada versión. Para la v5 esa evaluación no garantizaba que las partidas estuvieran fuera de la zona de entrenamiento ni se restringía a maestros (§5.2). Se conservan por trazabilidad histórica; la comparación v5 contra v6 con partidas realmente no vistas es la de §7.3.

### 7.2 Discusión Científica y Análisis de Ablación

1. **Ruptura de la Barrera del 40% en Accuracy Top-1 y 75% en Solidez:**  
   El modelo `v5` alcanza un hito fundamental para la tesis: un **41.87% de coincidencia exacta** con Grandes Maestros humanos y un **74.74% de jugadas sólidas** (Top-1 + Aceptables con pérdida $< 50$ cp), con inferencia en CPU en menos de $15$ ms por jugada. La fuerza de juego en partidas completas se midió aparte y es la de un aficionado (§7.4).
2. **Desplome Histórico de los Blunders (Por Debajo del 9%):**  
   Los errores catastróficos o cuelgues tácticos graves cayeron al **8.59%** (en comparación con el $19.35\%$ del modelo inicial). La poda táctica local `predecir_jugada_maestra()` (< 3 ms) descarta las jugadas que entregan una pieza mayor o permiten un mate en 1, pero **no se midió una tasa de errores graves en partidas reales**; las partidas completas muestran que el modelo sigue cometiendo errores tácticos frente a rivales que calculan (§7.4).
3. **Efecto de la Escala Curricular y Atención por Canales:**  
   El entrenamiento con 12,000 partidas de maestros (ELO $\ge$ 2000, ~850,000 posiciones en train) junto con la torre residual SE de 8 bloques y 192 canales dotó al agente de una comprensión posicional profunda, evidenciada por la baja tasa de imprecisiones ($7.88\%$).

### 7.3 Modelo v6: más partidas, jugadores más fuertes y validación por partida

**Configuración.** Red `RedSEResNetAjedrez` idéntica a la v5 (8 bloques residuales SE, 192 canales, 8.565.952 parámetros) para que la diferencia se deba a los datos y a la forma de validar. Corpus: **35.000 partidas** con ambos jugadores de ELO $\ge 2200$ (33.970 de entrenamiento y 1.030 de validación; 2.794.656 y 84.715 posiciones respectivamente, 2.879.371 en total, unas tres veces las de la v5). Optimización: AdamW ($\text{lr}_{max}=10^{-3}$, decaimiento de pesos $10^{-4}$), una época de calentamiento lineal y descenso coseno hasta $10^{-5}$, lote de 256, *label smoothing* $0{,}05$ y precisión mixta (FP16) sobre una GPU Tesla T4; unos 9,4 minutos por época.

**Curva de validación (por partida).**

| Época | Pérdida de entrenamiento | Val. top-1 | Val. top-3 |
| ---: | ---: | ---: | ---: |
| 1 | 3,3657 | 38,68 % | 65,04 % |
| 3 | 2,3994 | 45,70 % | 73,66 % |
| 6 | 2,0990 | 47,62 % | 75,77 % |
| **9** | **1,8910** | **47,64 %** | 75,58 % |
| 12 | 1,6978 | 47,02 % | 74,74 % |
| 16 | 1,4506 | 46,09 % | 73,60 % |

A partir de la época 9 la pérdida de entrenamiento sigue descendiendo mientras la precisión de validación **decrece**: **sobreajuste** (la red memoriza partidas de entrenamiento). Se conservó el punto de mayor precisión de validación (época 9) y el cuaderno de entrenamiento incorporó una **parada temprana** (`PACIENCIA = 4` épocas sin mejora).

**Comparación v5 contra v6 con partidas nuevas.** Treinta partidas de maestros (ELO $\ge 2200$) posteriores a la zona de entrenamiento, 2.619 jugadas, las mismas para ambas versiones (`training/evaluar_modelo.py`); cada desacierto se clasifica por la pérdida que le causa según Stockfish (oráculo de medición, no de decisión). Los porcentajes son sobre el total de jugadas:

| Indicador | v5 | v6 |
| :--- | ---: | ---: |
| Coincide con la jugada del maestro (top-1) | 43,15 % | **48,99 %** |
| Desacierto aceptable (< 50 cp) | 33,4 % | 32,4 % |
| Imprecisión (50–99 cp) | 8,9 % | 8,2 % |
| Error (100–299 cp) | 8,5 % | 7,1 % |
| Blunder ($\ge 300$ cp) | 6,0 % | **3,3 %** |

La v6 acierta casi seis puntos más y comete casi la mitad de errores graves. Es una evaluación orientativa (30 partidas, y las jugadas de una misma partida no son independientes).

### 7.4 Fuerza de juego en partidas completas

La exactitud al predecir la jugada de un maestro no mide si el modelo **juega bien**. Para medirlo se jugaron partidas completas (`training/enfrentar_modelos.py`) con la misma lógica de decisión que usa la aplicación (red + poda táctica, sin consultar a Stockfish), en 20 aperturas distintas jugadas con los dos colores, para que ningún lado tenga ventaja. Las partidas que llegan a 240 medias jugadas se declaran tablas.

**Modelo contra modelo.** La v6 contra la v5, 40 partidas: **+23 =15 −2** (puntaje 76,2 %, equivalente a unos $+200$ puntos de Elo; intervalo de confianza aproximado del 95 %: de $+124$ a $+307$).

**Contra Stockfish con el nivel de habilidad (`Skill Level`) limitado**, 0,05 s por jugada (victorias / tablas / derrotas del modelo):

| Rival | v5 | v6 |
| :--- | :---: | :---: |
| Skill 0 (12 partidas) | 1 / 3 / 8 | **5 / 2 / 5** |
| Skill 3 (12 partidas) | 1 / 2 / 9 | 0 / 5 / 7 |
| Skill 5 (12 partidas) | 0 / 0 / 12 | 0 / 1 / 11 |
| Skill 8, 12, 16 y 20 (20 partidas c/u) | casi todo derrotas | 0 / 0 / 20 en los cuatro niveles |

**Conclusión.** La red de política sola juega aproximadamente al nivel de Stockfish con la habilidad mínima: **imita jugadas de maestros, pero no juega como un maestro**. Es esperable, porque la red no explora variantes y Stockfish sí. En consecuencia, el nivel "18 / Maestro" de la escala del sistema se deriva del ELO de los datos de entrenamiento y **no es una fuerza de juego medida**; el tope de nivel del modelo no se modificó.

### 7.5 Búsqueda de variantes sobre la red

Los resultados de agregar cálculo a la red (§12) se reportan en §12.4.

---

## 8. Fases Evolutivas del Entrenamiento (Metáfora Antropomórfica del Aprendizaje)

Para la sustentación académica y defensa de grado, el proceso de entrenamiento del agente inteligente se estructura bajo la **Metáfora del Desarrollo Cognitivo Antropomórfico**, fundamentada rigurosamente en la _Teoría del Aprendizaje por Currículo_ (_Curriculum Learning_, Bengio et al., 2009) y la _Teoría de Plantillas y Bloques Perceptuales en Ajedrez_ (_Template Theory_, Chase & Simon, 1973; Gobet & Simon, 1996).

> **Aclaración (2026-10-13).** Las "edades cognitivas" y los títulos de esta sección son una **analogía pedagógica** para explicar la progresión de las versiones; **no indican fuerza de juego**. La fuerza medida se reporta en §7.4 y §13: la red sola de la v6 juega al nivel de un aficionado (Elo estimado de unos 1.355 contra Stockfish con ELO calibrado, en las condiciones descritas en §13).

El sistema no nació siendo un Gran Maestro; su red neuronal fue "educada" de manera análoga a las etapas de maduración de un ajedrecista humano a lo largo de su vida:

```mermaid
timeline
    title Evolución de las Versiones del Agente Neuronal (v1 a v6)
    Fase 1 (Prototipo) : Prototipo v1 : 200 partidas sin filtrar : Reglas elementales y visión miope : Comprobación de tubería de datos
    Fase 2 (Corpus ampliado) : Modelo v2 : 2,000 partidas Lichess : Comprensión de patrones comunes : Auditoría con Oráculo Stockfish (26.5% Top-1, 19.3% Blunders)
    Fase 3 (Red residual) : Modelo v3 : 3,000 partidas (ELO >= 1900) : ResNet profunda con Skip Connections : Gran reducción de colgadas (37.5% Top-1, 12.0% Blunders)
    Fase 4 (Atención selectiva) : Modelo v4 : 8,000 partidas (ELO >= 2000) : SE-ResNet 6 Bloques con Atención Selectiva : Label Smoothing y Refinamiento Posicional
    Fase 5 (Consolidación) : Modelo v5 : 12,000 partidas magistrales (ELO >= 2000) : SE-ResNet 8 Bloques (192 Canales) : 41.87% Top-1, 74.74% Sólido, Poda Táctica Local (< 3 ms)
    Fase 6 (Validación honesta) : Modelo v6 : 35,000 partidas (ELO >= 2200) : Validación por partida entera : 48.99% Top-1 en partidas nuevas, gana 23-2 a la v5
```

---

### Fase 1: El Prototipo (Versión v1)

- **Analogía pedagógica (no indica fuerza de juego):** ~10 años (Principiante que recién asimila las reglas de movimiento).
- **Parámetros Técnicos:** 200 partidas tomadas al azar, 10 épocas, optimizador Adam convencional, CNN básica de 3 capas.
- **Comportamiento Lúdico:** Juega por imitación inmediata de jugadas observadas. No evalúa consecuencias a medio plazo; mueve piezas atacadas sin coordinar planes defensivos.
- **Aporte Académico:** Demostró la viabilidad técnica del flujo completo (lectura de PGN streaming $\to$ codificación tensorial $8 \times 8 \times 12 \to$ inferencia en tiempo real).

### Fase 2: Corpus Ampliado (Versión v2)

- **Analogía pedagógica (no indica fuerza de juego):** ~15 años (Jugador de club escolar que asiste a torneos locales).
- **Parámetros Técnicos:** 2,000 partidas de Lichess sin filtro ELO (~140,000 posiciones), 10 épocas, split limpio por partida completa.
- **Comportamiento Lúdico:** Conoce tácticas estándar (jaques directos, capturas obvias, desarrollo de piezas menores), pero sufre de distracciones tácticas frecuentes cuando el rival elabora clavadas o amenazas a distancia.
- **Resultados Empíricos:** Coincidencia Top-1 del $26.58\%$ y $54.00\%$ de jugadas sólidas, pero con un $19.35\%$ de errores catastróficos (_blunders_ $\ge 300$ cp) debido al ruido de partidas de aficionados.

### Fase 3: Red Residual (Versión v3)

- **Analogía pedagógica (no indica fuerza de juego):** ~20 años (Aspirante a Maestro FIDE / Candidato a Maestro).
- **Parámetros Técnicos:** 3,000 partidas rigurosamente filtradas ($\text{ELO} \ge 1900$), 4 bloques residuales (`RedResNetAjedrez`), optimizador AdamW con _Cosine Annealing_.
- **Comportamiento Lúdico:** Estudia exclusivamente las obras de maestros. Las conexiones residuales (_skip connections_) actúan como la memoria de trabajo humana, permitiendo seguir la trayectoria de diagonales y columnas abiertas sin degradación.
- **Resultados Empíricos:** Salto extraordinario a **$37.54\%$ en precisión Top-1 (+41.2% relativo)**, **$64.70\%$ de decisiones competitivas** y caída drástica de errores graves al **$12.04\%$ (-37.8% de blunders)**.

### Fase 4: Atención Selectiva (Versión v4)

- **Analogía pedagógica (no indica fuerza de juego):** 25+ años (Gran Maestro Internacional con alta capacidad de cálculo y atención focalizada).
- **Fundamento Teórico:** Incorpora la **Teoría de la Atención Selectiva** mediante bloques _Squeeze-and-Excitation_ (Hu et al., 2018). Un Gran Maestro no calcula mecánicamente cada casilla; focaliza su atención cognitiva en las piezas desprotegidas y las rupturas críticas del centro.
- **Parámetros Técnicos:**
  1. **Datos de Élite:** 8,000 partidas con $\min(\text{WhiteElo}, \text{BlackElo}) \ge 2000$ (~600,000 a 700,000 posiciones magistrales).
  2. **Arquitectura:** `RedSEResNetAjedrez` con 6 bloques residuales y recalibración adaptativa de canales.
  3. **Regularización Cognitiva:** Pérdida de entropía cruzada con _Label Smoothing_ ($\alpha = 0.05$), que impide la sobreconfianza dogmática y reconoce que en posiciones ricas pueden coexistir múltiples planes correctos.
  4. **Optimización:** 20 épocas con decaimiento de peso y programación coseno de la tasa de aprendizaje.

### Fase 5: Consolidación (Versión v5)

- **Analogía pedagógica (no indica fuerza de juego):** ~30 años (Gran Maestro FIDE internacional en el cénit de su madurez competitiva, intuición estratégica y solidez técnica).
- **Fundamento Teórico:** Escalado curricular a gran escala y blindaje contra el error catastrófico mediante **doble filtro cognitivo**: Percepción Neuronal Profunda SE-ResNet-8 complementada con **Poda Táctica Heurística Local** (`predecir_jugada_maestra`).
- **Parámetros Técnicos:**
  1. **Dataset de Maestros a Gran Escala:** 12,000 partidas completas con $\min(\text{WhiteElo}, \text{BlackElo}) \ge 2000$ (944.534 posiciones en total; la separación 90/10 se hizo por posición suelta, ver §5.2).
  2. **Arquitectura Robusta:** `RedSEResNetAjedrez` con 8 bloques residuales SE y 192 canales (8.565.952 parámetros entrenables).
  3. **Poda Táctica Heurística en Inferencia:** Para garantizar movimientos 100% seguros y evitar cualquier anomalía en el brazo físico provocada por el residual de $8.59\%$ de colgadas del clasificador base, la función `predecir_jugada_maestra()` extrae las $K=5$ mejores alternativas por política de Softmax y ejecuta un filtrado táctico instantáneo en CPU (< 3 ms) sin consultar motores externos. Este filtro descarta en tiempo $\mathcal{O}(1)$ cualquier jugada que entregue una pieza mayor indefensa sin contrapartida o permita jaque mate forzado en 1 ply, que descarta las jugadas que entregan una pieza mayor o permiten un mate en 1. Su efecto sobre la tasa de errores en partidas completas no se midió por separado (ver §7.4).
- **Resultados Empíricos:**
  - Hito histórico de **41.87% de coincidencia exacta humana Top-1** (595 aciertos sobre 1,421 jugadas de la evaluación original; ver la nota metodológica de §7).
  - Tasa de jugadas viables y sólidas del **74.74%** (1,062 de 1,421).
  - Desplome de blunders al **8.59%** en el modelo neuronal base (reducción de más del 55% frente al modelo v2).
  - Inferencia ultra-rápida de **10 a 15 ms en CPU** estándar, óptima para el control en tiempo real del brazo robótico sin latencia perceptible.

### Fase 6: Más Datos y Validación Honesta (Versión v6)

- **Analogía pedagógica (no indica fuerza de juego):** repaso del mismo programa de estudio con más material y un examen sin repetición de preguntas.
- **Parámetros técnicos:** misma arquitectura que la v5; 35.000 partidas con ELO $\ge 2200$ en ambos jugadores; validación por partida entera; precisión mixta; parada temprana.
- **Resultados empíricos:** 47,64 % de top-1 en validación por partida (época 9); 48,99 % de top-1 en 2.619 jugadas de maestros no vistas (la v5: 43,15 %); errores graves del 3,3 % (la v5: 6,0 %); gana 23, empata 15 y pierde 2 contra la v5 en partidas completas (§7.3–§7.4).
- **Limitación observada:** sobreajuste desde la época 9; el siguiente avance requiere más partidas distintas, más regularización o cálculo adicional (§12).

---

## 9. Interpretabilidad y Explicabilidad del Modelo (XAI)

Uno de los principales desafíos en la adopción de redes neuronales en entornos educativos es el problema de la "caja negra" (Adadi & Berrada, 2018). Para brindar valor formativo al estudiante y transparencia técnica en la defensa de grado, el sistema integra un módulo de **Explicabilidad mediante Mapas de Saliencia (Saliency Maps)** en `backend/servicios/aprendizaje/inferencia.py::calcular_saliencia`.

```mermaid
flowchart LR
    A["Posición FEN"] --> B["Forward Pass (Red Neuronal)"]
    B --> C["Identificación de Jugada Ganadora a*"]
    C --> D["Backward Pass: Gradiente d(Score) / d(Entrada)"]
    D --> E["Suma Absoluta sobre Canales (8x8)"]
    E --> F["Normalización Min-Max [0, 1]"]
    F --> G["Visualización Mapa de Calor (Frontend)"]
```

### 9.1 Formulación Matemática del Mapa de Saliencia por Gradiente

Dado el tensor de entrada $\mathbf{X} \in \mathbb{R}^{8 \times 8 \times 12}$ y el puntaje logit sin normalizar $z_{a^*}$ correspondiente a la jugada seleccionada $a^*$, la importancia o saliencia de cada casilla $(i, j)$ se define como la magnitud del gradiente de la predicción con respecto a los canales de dicha casilla:

$$S_{i, j} = \sum_{c=1}^{12} \left| \frac{\partial z_{a^*}}{\partial \mathbf{X}_{i, j, c}} \right|, \quad \forall i, j \in \{0, \dots, 7\}$$

Para su renderizado en la interfaz de usuario (_Razonamiento Neuronal_ en React y Flutter), la matriz de saliencia $\mathbf{S} \in \mathbb{R}^{8 \times 8}$ se aplana a un vector de 64 elementos y se normaliza en el rango unitario $[0, 1]$:

$$\tilde{S}_k = \frac{S_k - \min(\mathbf{S})}{\max(\mathbf{S}) - \min(\mathbf{S}) + \epsilon}$$

### 9.2 Utilidad Pedagógica

El mapa de calor resultante ilumina las casillas críticas del tablero que motivaron la decisión de la red:

- Piezas amenazadas o clavadas.
- Puntos de ruptura en cadenas de peones.
- Casillas de escape del rey rival.
  Esto permite al estudiante comprender **por qué** la inteligencia artificial consideró prioritario cierto sector del tablero antes de ejecutar el movimiento.

### 9.3 Explicabilidad Contrastiva: Candidatas de Turing

El mapa de saliencia (Sección 9.1) explica *dónde* mira la red para una única jugada ya decidida, pero no responde una pregunta pedagógicamente igual de relevante: *¿qué otras alternativas consideró la red y por qué las descartó?* Para cubrir ese vacío, el sistema incorpora un segundo mecanismo de explicabilidad, complementario y no sustitutivo del anterior, implementado en `backend/servicios/aprendizaje/inferencia.py::explicar_top_candidatas` y expuesto en el panel "Candidatas de Turing" de la interfaz de _Razonamiento Neuronal_.

A diferencia del mapa de saliencia (que opera sobre gradientes de una sola jugada), esta técnica es **contrastiva por diseño**: toma las $N=3$ jugadas legales con mayor puntaje bruto de la red $z_{a}$, calcula su probabilidad relativa mediante _softmax_ restringido al conjunto de jugadas legales $\mathcal{L}(s)$ de la posición $s$,

$$P(a \mid s) = \frac{e^{z_a}}{\sum_{a' \in \mathcal{L}(s)} e^{z_{a'}}}, \quad \forall a \in \text{top-3}(\mathcal{L}(s))$$

y expone las tres en paralelo junto con la marca de cuál de ellas es la que efectivamente jugaría el modelo (`elegida=True`).

**Consistencia decisión-explicación.** Un riesgo conocido de los módulos de explicabilidad post-hoc es que la explicación mostrada al usuario diverja de la lógica que realmente ejecuta el sistema en producción (Rudin, 2019). Para evitarlo, `explicar_top_candidatas` no reimplementa la regla de decisión: llama a la misma función auxiliar `_evaluar_candidata_tactica` que usa `predecir_jugada_maestra` para la partida real, garantizando que la jugada marcada como `elegida` en el panel sea, por construcción, idéntica a la que el modelo ejecutaría si estuviera jugando esa posición.

**Chequeos tácticos autónomos por candidata.** Sobre cada una de las tres candidatas se aplican, en memoria y sin invocar a Stockfish (en cumplimiento de la Regla 1 de independencia del modelo — ver §1 de las reglas técnicas del proyecto), tres verificaciones deterministas basadas en las reglas de `python-chess`:

1. **`da_jaque_mate`**: la candidata termina la partida de inmediato.
2. **`rival_tiene_mate_en_1`**: tras jugarla, el rival dispone de al menos una respuesta que da mate en su siguiente turno — una candidata con esta bandera en `True` es descartada por la regla de decisión salvo que las tres candidatas la compartan.
3. **`pieza_colgada`**: la pieza recién movida queda en una casilla atacada sin defensa propia o por una pieza rival de menor valor material; en ese caso se resta una penalidad $\text{pen} = (\text{monto}_{cp} / 100) \times 2.0$ al score de red antes de comparar candidatas, donde $\text{monto}_{cp}$ es la diferencia de valor entre la pieza perdida y la capturada (0 si no hay captura).

**Comparación con el oráculo Stockfish, candidata por candidata.** Para cada una de las tres jugadas se calcula además `evaluacion_stockfish_cp` (evaluación de Stockfish tras jugarla, en centipawns desde la perspectiva de quien mueve) y `diferencia_cp` (contra la evaluación de la posición antes de mover, con signo invertido para expresarla siempre desde la perspectiva del jugador). Es importante remarcar que, igual que en la Sección 1 de las reglas del proyecto, esta comparación es puramente informativa: Stockfish nunca participa en el cálculo de `elegida`, solo se ejecuta *después* de que la red ya decidió, como una segunda opinión que el estudiante puede usar para calibrar cuánto confiar en la sugerencia de la red en esa posición concreta.

En conjunto, el panel responde tres preguntas pedagógicas que el mapa de saliencia por sí solo no cubre: *(a)* ¿qué tan segura estaba la red de su elección frente a las alternativas cercanas (probabilidades relativas)?, *(b)* ¿descartó la red alguna jugada por una razón táctica concreta y verificable?, y *(c)* ¿qué tan de acuerdo está un motor de fuerza bruta con cada una de las alternativas que la red consideró viables?

---

## 10. Protocolo de Promoción de Checkpoints y Control de Calidad (RF15 / RF16)

Para garantizar la estabilidad del software y evitar regresiones cualitativas, el sistema implementa un criterio formal de aceptación antes de sustituir un checkpoint en producción:

$$
\text{Aprobación}(v_{nueva}) = \begin{cases}
\text{Promover}, & \text{si } \text{Legalidad}(v_{nueva}) = 100\% \\
                 & \land \; \text{TasaBlunders}(v_{nueva}) \le \text{TasaBlunders}(v_{actual}) \\
                 & \land \; \text{Accuracy}_{Top-1}(v_{nueva}) \ge \text{Accuracy}_{Top-1}(v_{actual}) - \delta \\
\text{Rechazar / Rollback}, & \text{en caso contrario}
\end{cases}
$$

Donde:

- **Legalidad Estricta:** Ninguna predicción puede violar las reglas de movimiento bajo ninguna circunstancia.
- **Tolerancia de Margen ($\delta = 1.0\%$):** Permite fluctuaciones menores en coincidencias humanas directas siempre que la tasa de colgadas graves (_blunders_) disminuya significativamente.
- **Mecanismo de Desacople:** Al mantener desacoplada la interfaz `cargar_modelo()` mediante el patrón Factory y detección dinámica de arquitectura, si una versión falla en validación, el sistema realiza un _rollback_ inmediato a la versión previa estable simplemente modificando la variable `RUTA_CHECKPOINT_POR_DEFECTO`, sin necesidad de recompilar ni desplegar código nuevo.

---

## 11. Eficiencia Computacional y Factibilidad de Despliegue

Una decisión arquitectónica deliberada del proyecto fue priorizar la eficiencia de inferencia en hardware accesible:

| Parámetro                |       Modelo Neuronal Propio (v5 SE-ResNet-8)       |                 Motor Stockfish 16                  |
| ------------------------ | :-------------------------------------------------: | :-------------------------------------------------: |
| **Paradigma**            |     Reconocimiento de Patrones (Intuición pura)     |      Búsqueda Minimax Alfa-Beta (Fuerza bruta)      |
| **Tiempo de Inferencia** |              **10 – 15 ms por jugada**              |    500 – 2,000 ms por jugada (según profundidad)    |
| **Consumo de Memoria**   |             ~34.3 MB (pesos del modelo)             | Variable (16 MB – 2 GB según Hash de transposición) |
| **Requerimiento de GPU** | **Solo en Entrenamiento** (Inferencia corre en CPU) |       No aplicable (Corre en CPU multi-hilo)        |
| **Dependencia Externa**  |       Totalmente autónomo (In-Memory PyTorch)       |       Requiere binario nativo compilado en SO       |

Esta latencia ultra baja (< 20 ms) resulta determinante para la fase de integración con el brazo robótico (HU9, Sprint 3): el sistema de control en tiempo real no sufre bloqueos esperando que un motor calcule durante segundos, facilitando una sincronización fluida entre la captura visual de la cámara, la decisión de la IA y el envío de comandos cinemáticos al microcontrolador ESP32.

---

## 12. Búsqueda de Variantes sobre la Red de Política (Turing con Cálculo)

### 12.1 Motivación

Los resultados de §7.4 muestran que una red de política sin cálculo comete errores tácticos que cualquier motor de búsqueda evita: no "ve" que una jugada pierde una pieza dos jugadas más tarde. Siguiendo la tradición de los programas de ajedrez desde Shannon (1950), se combina la **intuición** de la red (qué jugadas merecen atención) con **cálculo** explícito de variantes (qué ocurre si se juegan), de forma análoga a cómo AlphaGo y AlphaZero combinan una red de política con búsqueda (Silver et al., 2016; 2017). A diferencia de esos sistemas, aquí la evaluación de las posiciones hojas es una función propia, simple y determinista, y **en ningún momento se consulta a Stockfish** (Regla 1 del proyecto).

### 12.2 Diseño (`backend/servicios/aprendizaje/busqueda_turing.py`)

1. **Probabilidades de la red.** Una sola pasada de la red da, por *softmax* restringido a las jugadas legales, la probabilidad $P(a \mid s)$ de cada jugada.
2. **Candidatas.** Las 12 jugadas más probables y, hasta 6 más, capturas y jaques que la red hubiera subestimado.
3. **Búsqueda.** *Negamax* con poda alfa-beta (Knuth & Moore, 1975), ordenamiento de jugadas por captura (mayor víctima, menor atacante) y promoción, **búsqueda de quietud** (se siguen las capturas hasta que la posición se calma, hasta 8 niveles, para no evaluar en medio de un intercambio) y **profundización iterativa** con límite de tiempo: si el tiempo se agota a mitad de un nivel se usa el resultado del nivel anterior.
4. **Evaluación estática.** Material (peón 100, caballo 320, alfil 330, torre 500, dama 900 centipeones) más una tabla de posición por tipo de pieza; el rey usa una tabla de final cuando ningún bando conserva más de 2.600 centipeones de material sin contar peones. Se trata la repetición, el material insuficiente y la regla de los 50 movimientos como tablas.
5. **Combinación con la red.** El puntaje final de cada candidata $a$ es

$$S(a) = C(a) + w \cdot \ln P(a \mid s)$$

donde $C(a)$ es el puntaje del cálculo (centipeones, desde la óptica de quien mueve) y $w$ (`peso_red`) regula cuánto manda la red: con $w = 0$ decide solo el cálculo; con $w$ alto la red decide salvo que el cálculo encuentre una ventaja mayor. Se elige la jugada de mayor $S(a)$; los mates encontrados cortan la profundización.

**Costo.** En Python, con `python-chess`, el buscador procesa unos 17.000 a 20.000 nodos por segundo; una profundidad de 2 a 3 medias jugadas por posición cuesta entre décimas de segundo y un segundo. El procedimiento es determinista y no aprende en vivo (Regla 2).

### 12.3 Verificación

Quince pruebas unitarias (`test_busqueda_turing.py`) comprueban, entre otras cosas: que se encuentre un mate en 1 y el mate del pasillo, que se capture una dama colgada, que **no se regale la dama aunque la red la prefiera**, que con $w = 0$ mande solo el cálculo, que se devuelva siempre una jugada legal, que la posición recibida no se modifique y que una búsqueda con tiempo casi nulo igualmente responda.

### 12.4 Resultados

Se enfrenta la red **más** búsqueda contra la **misma red sola** (checkpoint v6), 20 aperturas con los dos colores (40 partidas), máximo 1 s por jugada de búsqueda. Resultados desde el punto de vista de la red con búsqueda:

| Profundidad | Peso de la red $w$ | Victorias / tablas / derrotas | Puntaje | Diferencia de Elo (IC 95 %) |
| :---: | :---: | :---: | ---: | :--- |
| 2 | 40 | 29 / 11 / 0 | 86,2 % | $+319$ ($+234$ a $+454$) |
| 3 | 20 | 29 / 9 / 2 | 83,8 % | $+285$ ($+191$ a $+437$) |
| 3 | 40 | **34 / 6 / 0** | **92,5 %** | $+436$ ($+330$ a $+679$) |
| 3 | 100 | 24 / 15 / 1 | 78,8 % | $+228$ ($+150$ a $+333$) |

La mejor configuración medida es la de **profundidad 3 con $w = 40$**: no perdió ninguna de las 40 partidas contra la red sola. Con $w$ más bajo (20) el cálculo manda demasiado y su evaluación simple (material y posición) comete errores que la red evitaba; con $w$ más alto (100) la red manda tanto que el cálculo casi no corrige nada (más tablas). El valor intermedio rinde mejor, lo que respalda combinar ambas fuentes en lugar de usar una sola. Estos intervalos son de 40 partidas y las configuraciones se ajustaron sobre las mismas 20 aperturas, de modo que la diferencia exacta de Elo debe tomarse como orden de magnitud; el Elo absoluto con búsqueda frente a Stockfish aún no se ha medido.

---

## 13. Medición de la Fuerza de Juego (Elo) y Protocolo UCI

### 13.1 Modelo de Elo

El sistema de calificación Elo (Elo, 1978) estima la probabilidad esperada de que un jugador $A$ de calificación $R_A$ obtenga un punto (victoria = 1, tablas = 0,5) frente a $B$ de calificación $R_B$:

$$E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}}$$

Dados los resultados de $A$ contra rivales de calificación conocida $R_i$ (con $n_i$ partidas y puntaje medio $s_i$), se estima $R_A$ como el valor que iguala el puntaje esperado al obtenido, es decir, la solución de $\sum_i n_i\,(s_i - E_i(R_A)) = 0$ (estimación de máxima verosimilitud logística, `training/enfrentar_modelos.py::estimar_elo`, resuelta por bisección). El intervalo de confianza del 95 % se aproxima con la información de Fisher, $\operatorname{Var}(\hat R_A) \approx \left[ k^2 \sum_i n_i E_i (1 - E_i) \right]^{-1}$ con $k = \ln 10 / 400$; es aproximado y se achata con pocas partidas.

### 13.2 Rivales calibrados

Se usa como rival Stockfish con fuerza limitada (`UCI_LimitStrength` y `UCI_Elo`, rango de 1320 a 3190). **Limitación:** esa calibración corresponde a controles de tiempo largos; con $0{,}2$ s por jugada no es exacta, por lo que el Elo estimado es **relativo a ese rival y a ese tiempo** y sirve sobre todo para comparar versiones del modelo entre sí, no como calificación oficial.

### 13.3 Resultado para la v6 (red sola)

Cuarenta partidas contra cada rival (20 aperturas, dos colores), 0,2 s por jugada del rival:

| Rival (Stockfish con ELO calibrado) | Victorias / tablas / derrotas | Puntaje |
| :--- | :---: | ---: |
| 1320 | 16 / 9 / 15 | 51,2 % |
| 1500 | 7 / 10 / 23 | 30,0 % |
| 1700 | 2 / 9 / 29 | 16,2 % |

**Elo estimado de la v6 (red sola): $\approx 1355$ (intervalo del 95 %: de 1284 a 1427; 120 partidas).** Es el valor de referencia contra el cual se mide cada mejora posterior (la búsqueda de §12 y las versiones siguientes), aceptando un cambio únicamente si el puntaje mejora de forma clara.

### 13.4 Interfaz UCI

Turing se expone como motor del **protocolo UCI** (*Universal Chess Interface*; Meyer-Kahlen, 2000), el estándar con el que los programas de ajedrez se comunican con sus motores (`training/turing_uci.py`). Soporta `uci`, `isready`, `setoption` (opciones `Checkpoint` y `Nivel`), `ucinewgame`, `position`, `go` y `quit`. Con ello Turing puede conectarse a cualquier programa que acepte motores UCI, igual que Stockfish, y medirse con herramientas estándar. La interfaz se verificó con pruebas unitarias del protocolo y con una prueba de punta a punta en la que un proceso real de Turing juega contra la biblioteca `python-chess` con la red cargada.

---

## 14. Referencias Bibliográficas (Normas APA 7ma Edición)

- Adadi, A., & Berrada, M. (2018). Peeking inside the black-box: A review of Explainable Artificial Intelligence (XAI). _IEEE Access_, 6, 52138-52160. https://doi.org/10.1109/ACCESS.2018.2870052
- Bengio, Y., Louradour, J., Collobert, R., & Weston, J. (2009). Curriculum learning. En _Proceedings of the 26th annual international conference on machine learning (ICML)_ (pp. 41-48). https://doi.org/10.1145/1553374.1553380
- Chase, W. G., & Simon, H. A. (1973). Perception in chess. _Cognitive Psychology_, 4(1), 55-81. https://doi.org/10.1016/0010-0285(73)90004-2
- Elo, A. E. (1978). _The rating of chessplayers, past and present_. Arco Publishing.
- FIDE. (2022). _FIDE Laws of Chess_. International Chess Federation. https://www.fide.com/fide/handbook
- Fiekas, N. (2024). _python-chess: A chess library for Python_. https://python-chess.readthedocs.io/
- Gobet, F., & Simon, H. A. (1996). Templates in chess memory: A mechanism for recalling several boards. _Cognitive Psychology_, 31(1), 1-40. https://doi.org/10.1006/cogp.1996.0011
- He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition. En _Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)_ (pp. 770-778). https://doi.org/10.1109/CVPR.2016.90
- Hu, J., Shen, L., & Sun, G. (2018). Squeeze-and-excitation networks. En _Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)_ (pp. 7132-7141). https://doi.org/10.1109/CVPR.2018.00745
- Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data mining: Formulation, detection, and avoidance. _ACM Transactions on Knowledge Discovery from Data (TKDD)_, 6(4), 1-21. https://doi.org/10.1145/2382577.2382579
- Knuth, D. E., & Moore, R. W. (1975). An analysis of alpha-beta pruning. _Artificial Intelligence_, 6(4), 293-326. https://doi.org/10.1016/0004-3702(75)90019-3
- Lichess. (s. f.). _Lichess open database_ [Conjunto de datos, licencia CC0]. https://database.lichess.org/
- Loshchilov, I., & Hutter, F. (2017). SGDR: Stochastic gradient descent with warm restarts. En _International Conference on Learning Representations (ICLR)_.
- Loshchilov, I., & Hutter, F. (2019). Decoupled weight decay regularization. En _International Conference on Learning Representations (ICLR)_. https://openreview.net/forum?id=Bkg6RiCqY7
- McIlroy-Young, R., Sen, S., Kleinberg, J., & Anderson, A. (2020). Aligning superhuman AI with human behavior: Chess as a model system. En _Proceedings of the 26th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining_ (pp. 1677-1687). https://doi.org/10.1145/3394486.3403219
- Meyer-Kahlen, S. (2000). _UCI - Universal Chess Interface_. Shredder Chess. https://www.shredderchess.com/chess-features/uci-universal-chess-interface.html
- Müller, R., Kornblith, S., & Hinton, G. E. (2019). When does label smoothing help? En _Advances in Neural Information Processing Systems (NeurIPS)_, 32.
- Romstad, T., Costalba, M., Kiiski, J., & Linscott, G. (2024). _Stockfish: A strong open-source chess engine_. https://stockfishchess.org/
- Rudin, C. (2019). Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead. _Nature Machine Intelligence_, 1(5), 206-215. https://doi.org/10.1038/s42256-019-0048-x
- Russell, S., & Norvig, P. (2020). _Artificial Intelligence: A Modern Approach_ (4ta ed.). Pearson.
- Shannon, C. E. (1950). Programming a computer for playing chess. _Philosophical Magazine_, 41(314), 256-275.
- Silver, D., Huang, A., Maddison, C. J., Guez, A., Sifre, L., van den Driessche, G., Schrittwieser, J., Antonoglou, I., Panneershelvam, V., Lanctot, M., Dieleman, S., Grewe, D., Nham, J., Kalchbrenner, N., Sutskever, I., Lillicrap, T., Leach, M., Kavukcuoglu, K., Graepel, T., & Hassabis, D. (2016). Mastering the game of Go with deep neural networks and tree search. _Nature_, 529(7587), 484-489. https://doi.org/10.1038/nature16961
- Silver, D., Hubert, T., Schrittwieser, J., Antonoglou, I., Lai, M., Guez, A., Lanctot, M., Sifre, L., Dhar, S., Lillicrap, T., Graepel, T., & Hassabis, D. (2017). Mastering chess and shogi by self-play with a general reinforcement learning algorithm. _arXiv preprint arXiv:1712.01815_. https://doi.org/10.48550/arXiv.1712.01815
- Sutton, R. S., & Barto, A. G. (2018). _Reinforcement Learning: An Introduction_ (2da ed.). MIT Press.
