"""Contenido curado a mano sobre reglas de ajedrez, sin LLM de por medio.

Esto es lo único que el tutor "Turing" (`servicio_tutor.py`) puede citar cuando
le preguntan cómo se mueve una pieza o una regla general del juego — el LLM
nunca inventa este contenido, solo lo lee vía las tools `regla_pieza` y
`regla_general_ajedrez` (ver `PLAN_IMPLEMENTACION_COMPLETO.md` y el plan del
tutor: "el LLM nunca decide una regla de ajedrez por su cuenta").

`nombre`, `apodo` y `regla_especial` de cada pieza están copiados tal cual del
array `PIEZAS` en `frontend/src/paginas/PanelAprendizaje/PanelAprendizaje.jsx`
— ese es el contenido educativo ya revisado que usa el Panel de Aprendizaje.
`como_se_mueve` es contenido nuevo (no existía en ningún lado: ni el frontend
web ni la app Flutter tienen prosa de "cómo se mueve cada pieza", solo el
apodo y una regla especial), redactado en el mismo registro pedagógico.
"""
from __future__ import annotations

REGLAS_PIEZAS: dict[str, dict[str, str]] = {
    "rey": {
        "nombre": "Rey",
        "apodo": "El Monarca",
        "regla_especial": (
            "Se enroca una vez por partida: se pone a resguardo y de paso activa una torre."
        ),
        "como_se_mueve": (
            "Se mueve una sola casilla por turno, en cualquier dirección (horizontal, vertical "
            "o diagonal). Es la pieza más importante del tablero: si queda en jaque sin ninguna "
            "forma de escapar, la partida termina."
        ),
    },
    "dama": {
        "nombre": "Dama",
        "apodo": "La Soberana",
        "regla_especial": (
            "Es la pieza de mayor valor del tablero: se mueve como la torre y el alfil combinados."
        ),
        "como_se_mueve": (
            "Se desplaza cualquier cantidad de casillas libres, en línea recta o en diagonal, en "
            "cualquier dirección. Es la pieza con más movilidad de todo el tablero."
        ),
    },
    "torre": {
        "nombre": "Torre",
        "apodo": "El Bastión",
        "regla_especial": "Es la pieza que participa junto al rey en el enroque.",
        "como_se_mueve": (
            "Se mueve cualquier cantidad de casillas libres, en línea recta, de forma horizontal "
            "o vertical."
        ),
    },
    "alfil": {
        "nombre": "Alfil",
        "apodo": "El Francotirador",
        "regla_especial": (
            "Se queda toda la partida en casillas de un mismo color — nunca cambia de color de casilla."
        ),
        "como_se_mueve": "Se desplaza cualquier cantidad de casillas libres, siempre en diagonal.",
    },
    "caballo": {
        "nombre": "Caballo",
        "apodo": "El Infiltrador",
        "regla_especial": "Es la única pieza que puede saltar por encima de otras piezas.",
        "como_se_mueve": (
            "Se mueve en forma de \"L\": dos casillas en línea recta y luego una casilla más "
            "hacia un costado, perpendicular a la dirección anterior."
        ),
    },
    "peon": {
        "nombre": "Peón",
        "apodo": "La Vanguardia",
        "regla_especial": (
            'Puede capturar "al paso" y se convierte en otra pieza (corona) al llegar a la última fila.'
        ),
        "como_se_mueve": (
            "Avanza una casilla hacia adelante (dos si es su primer movimiento desde esa casilla) "
            "y solo captura en diagonal, una casilla hacia adelante."
        ),
    },
}

REGLAS_GENERALES: dict[str, str] = {
    "objetivo_del_juego": (
        "El objetivo del ajedrez es dar jaque mate al rey rival: dejarlo en jaque sin ninguna "
        "jugada legal que lo saque de esa amenaza. En cuanto eso pasa, la partida termina y gana "
        "quien dio el jaque mate, sin importar cuántas piezas le queden a cada lado."
    ),
    "turnos": (
        "Blancas y negras mueven por turnos, una jugada a la vez, y las blancas siempre empiezan "
        "la partida. No se puede pasar el turno: si te toca mover, tenés que mover alguna pieza "
        "aunque ninguna jugada te convenza."
    ),
    "jaque": (
        "Un jaque es cuando el rey está siendo atacado directamente por una pieza rival. Si tu "
        "rey está en jaque, tu única jugada legal válida es sacarlo de esa amenaza: moverlo a una "
        "casilla segura, bloquear el ataque con otra pieza, o capturar a la pieza que amenaza."
    ),
    "jaque_mate": (
        "El jaque mate pasa cuando el rey está en jaque y no existe ninguna jugada legal para "
        "escapar de esa amenaza — ni moverlo, ni bloquear, ni capturar al atacante. Ahí termina "
        "la partida: gana quien dio el jaque mate."
    ),
    "ahogado_tablas": (
        "El ahogado es una de las formas de tablas (empate): pasa cuando al jugador que le toca "
        "mover no tiene ningún jaque encima, pero tampoco le queda ninguna jugada legal disponible. "
        "En ese caso la partida termina en empate, no en derrota, aunque uno de los dos tenga mucha "
        "ventaja de material."
    ),
    "enroque": (
        "El enroque es la única jugada donde se mueven dos piezas propias a la vez: el rey se "
        "mueve dos casillas hacia una torre, y esa torre salta al otro lado del rey. Sirve para "
        "poner al rey a resguardo y, de paso, activar una torre. Solo se puede hacer si ni el rey "
        "ni esa torre se movieron antes en la partida, si no hay piezas entre ellos, y si el rey "
        "no está en jaque ni pasa por una casilla atacada."
    ),
    "captura_al_paso": (
        'La captura "al paso" es una regla especial de los peones: si un peón rival avanza dos '
        "casillas desde su posición inicial y queda al lado de uno de tus peones, tu peón lo puede "
        "capturar como si el rival solo hubiera avanzado una casilla — pero solo en la jugada "
        "inmediatamente siguiente; si no se usa en ese momento, se pierde esa oportunidad."
    ),
    "coronacion": (
        "La coronación pasa cuando un peón llega a la última fila del tablero (la fila 8 para "
        "blancas, la fila 1 para negras): ahí se convierte en la pieza que el jugador elija (dama, "
        "torre, alfil o caballo), casi siempre dama por ser la más fuerte. Es lo que le da al peón, "
        "la pieza de menor valor, la posibilidad de volverse decisivo al final de la partida."
    ),
    "valor_de_las_piezas": (
        "Cada pieza tiene un valor relativo en puntos, que sirve para comparar quién tiene más "
        "material en el tablero (no es una regla oficial del juego, es una guía práctica): peón = "
        "1 punto, caballo = 3 puntos, alfil = 3 puntos, torre = 5 puntos, dama = 9 puntos. El rey "
        "no tiene un valor en puntos, porque perderlo (jaque mate) termina la partida directamente, "
        "no es algo que se pueda \"cambiar\" por otras piezas. Estos valores son aproximados: en la "
        "práctica, la posición de cada pieza en el tablero también importa, no solo su tipo."
    ),
    "centipawns": (
        "Un centipawn es la unidad que usan los motores de ajedrez (como Stockfish, el que analiza "
        "las partidas en esta plataforma) para medir qué tan favorable es una posición: 100 "
        "centipawns equivalen a la ventaja de tener un peón de más. Por ejemplo, una evaluación de "
        "+150 centipawns para blancas significa una ventaja parecida a un peón y medio extra. Los "
        "números positivos favorecen a blancas y los negativos a negras. Es la misma unidad que "
        "aparece en el repaso de tus partidas y en el panel de Razonamiento Neuronal."
    ),
    "tablero_y_notacion": (
        "El tablero de ajedrez tiene 64 casillas, en una grilla de 8 columnas por 8 filas, con "
        "casillas claras y oscuras alternadas. Para nombrar cada casilla se usa la notación "
        "algebraica: las columnas se llaman de la \"a\" a la \"h\" (de izquierda a derecha desde el "
        "lado de las blancas) y las filas del 1 al 8 (de abajo hacia arriba desde el lado de las "
        "blancas) — por ejemplo, \"e4\" es la columna e, fila 4. Cada jugador empieza con 16 "
        "piezas: 8 peones, 2 torres, 2 caballos, 2 alfiles, 1 dama y 1 rey."
    ),
}
