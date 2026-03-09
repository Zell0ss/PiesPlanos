# Diseño: Sistema Híbrido de Objetos (inspirado en Zork)

**Fecha:** 2026-03-09
**Estado:** Aprobado — listo para implementación
**Scope:** Rediseño limpio del modelo de objetos (Opción B)

---

## Motivación

El modelo actual de PiesPlanos tiene deuda técnica acumulada:
- Puertas duplicadas como objetos separados en cada habitación
- `Exit` sin condicionales ni nombres naturales — solo `{destination, item}`
- `Item` sin sistema de flags — solo `fixed: bool`
- Sin contenedores reales — las propiedades de contenido son texto descriptivo
- `Location` es un contenedor pasivo sin lifecycle hooks
- `base_description: StopAsyncIteration` (bug de tipo en Location)

El estudio de Zork I revela soluciones elegantes y probadas para todos estos problemas. Este diseño las adopta y adapta al género detective noir, evitando sobreingeniería.

---

## Principios de diseño

1. **Todo es un GameObject** — jerarquía unificada, comportamiento consistente
2. **Datos en YAML, lógica en Python** — separación clara de responsabilidades
3. **Flags como set[Enum]** — legible y extensible, sin bitmasks
4. **Navegación por intención** — nombres naturales, brújula como alias opcional
5. **Visibilidad por ámbito** — globals universales y local-globals por habitación
6. **El engine no cambia** — el pipeline Interpret→Resolve→Route→Execute se mantiene

---

## Jerarquía de clases

```
GameObject (base)
├── Item(GameObject)
├── Door(GameObject)
├── Location(GameObject)
└── NPC(GameObject)

Player  ← sin cambios estructurales
Investigation  ← sin cambios estructurales
```

### GameObject — clase base

```python
@dataclass
class GameObject:
    id: str
    name: str
    base_description: str
    synonyms: list[str] = field(default_factory=list)
    flags: set[GameFlag] = field(default_factory=set)
    children: list[str] = field(default_factory=list)  # IDs de hijos
    parent_id: str | None = None

    def has_flag(self, flag: GameFlag) -> bool:
        return flag in self.flags

    def add_flag(self, flag: GameFlag):
        self.flags.add(flag)

    def remove_flag(self, flag: GameFlag):
        self.flags.discard(flag)
```

**Nota sobre children:** Se almacenan como IDs (strings) para facilitar serialización YAML/SQLite. El engine resuelve IDs a objetos en memoria.

---

### GameFlag — enum de flags

```python
from enum import Enum, auto

class GameFlag(Enum):
    # Interacción básica
    TAKEABLE = auto()      # se puede coger
    FIXED = auto()         # no se puede mover
    OPENABLE = auto()      # se puede abrir/cerrar
    LOCKABLE = auto()      # tiene mecanismo de bloqueo

    # Estructura
    CONTAINER = auto()     # puede contener otros objetos
    SURFACE = auto()       # se puede poner cosas encima
    DOOR = auto()          # es una puerta/pasaje

    # Visibilidad
    INVISIBLE = auto()     # existe pero no aparece en descripciones
    SCENERY = auto()       # visible pero interacción limitada

    # Investigación
    CLUE_SOURCE = auto()   # puede revelar pistas
    EXAMINED = auto()      # ya fue examinado por el jugador
    EVIDENCE = auto()      # es evidencia física del caso

    # Estado dinámico
    OPEN = auto()          # está abierto en este momento
    LOCKED = auto()        # está bloqueado en este momento
    LIT = auto()           # emite luz (para mecánica de oscuridad futura)
```

---

### Item(GameObject)

```python
@dataclass
class Item(GameObject):
    clues: list[ClueData] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
```

`fixed: bool` y `reason_fixed` se eliminan — reemplazados por `GameFlag.FIXED`.
`examined: bool` se elimina — reemplazado por `GameFlag.EXAMINED`.

**YAML ejemplo:**
```yaml
- id: office_safe
  name: caja fuerte
  synonyms: [caja, safe, fuerte, caja fuerte]
  base_description: Una caja fuerte pequeña pero sólida en la esquina de la oficina...
  flags: [FIXED, OPENABLE, LOCKABLE, CONTAINER]
  children: []
  properties:
    color: verde oscuro
    lock_type: combinación
```

---

### Door(GameObject)

Objeto único que existe entre dos habitaciones. Eliminan la duplicación actual.

```python
@dataclass
class Door(GameObject):
    connects: tuple[str, str]         # (location_id_a, location_id_b)
    key_id: str | None = None         # ID del ítem llave, None si es puzzle
    unlock_condition: str | None = None  # ID de condición en el engine
```

El estado abierto/cerrado/bloqueado se gestiona con flags:
- `GameFlag.OPEN` — está abierta ahora
- `GameFlag.LOCKED` — está bloqueada ahora

**YAML ejemplo:**
```yaml
# doors.yaml  ← nuevo archivo
- id: main_door
  name: puerta principal del Azul
  synonyms: [puerta, entrada, salida, puerta principal]
  base_description: Una puerta de madera pesada con herrajes de latón...
  flags: [DOOR, OPENABLE, OPEN]
  connects: [jazz_street, jazz_club]
  key_id: null
  unlock_condition: null

- id: trap_door
  name: trampilla del sótano
  synonyms: [trampilla, trapa, sótano]
  base_description: Una trampilla de madera en el suelo...
  flags: [DOOR, OPENABLE, LOCKABLE, LOCKED]
  connects: [living_room, cellar]
  key_id: null
  unlock_condition: found_secret_lever
```

---

### Exit

```python
@dataclass
class Exit:
    destination: str           # location_id
    name: str                  # "puerta trasera", "escaleras al sótano"
    aliases: list[str] = field(default_factory=list)  # ["sur", "s", "abajo"]
    door_id: str | None = None
    condition: str | None = None  # condición sin puerta asociada
```

**YAML ejemplo:**
```yaml
# dentro de locations.yaml
exits:
  - destination: jazz_street
    name: puerta de entrada
    aliases: [salida, calle, sur, s]
    door_id: main_door

  - destination: backstage_corridor
    name: puerta del backstage
    aliases: [backstage, detrás, fondo]
    door_id: backstage_door
```

**Resolución de movimiento:**
Cuando el jugador dice "ve a la calle" o "sal" o "sur", el engine busca en los exits de la ubicación actual por match en `name`, `aliases`, o nombre/alias del `destination`. El AI interpreta primero el lenguaje libre.

---

### Location(GameObject)

```python
@dataclass
class Location(GameObject):
    exits: list[Exit] = field(default_factory=list)
    local_globals: list[str] = field(default_factory=list)  # IDs visibles aquí
    npcs: list[str] = field(default_factory=list)           # IDs de NPCs presentes
    visited: bool = False
    illustration_path: str | None = None
    investigation_complete: bool = False

    # Hooks — None si la habitación no necesita lógica especial
    on_enter: Callable | None = None
    on_look: Callable | None = None
    on_before_command: Callable | None = None
    on_after_command: Callable | None = None
```

**Nota:** Los items de la habitación van en `children` (heredado de GameObject).
`npcs` se mantiene separado de `children` para facilitar la búsqueda de NPCs.

**YAML ejemplo:**
```yaml
- id: jazz_club
  name: Jazz Club Azul — interior
  synonyms: [club, azul, interior, bar]
  base_description: El interior del club está envuelto en penumbra...
  flags: [LIT]
  children:
    - old_decorative_piano
    - jenny_dead_body
    - dropped_gun
  npcs:
    - jack_napier_barman
  local_globals:
    - jazz_music
    - main_door
    - backstage_door
  exits:
    - destination: jazz_street
      name: puerta de entrada
      aliases: [salida, calle, exterior]
      door_id: main_door
    - destination: backstage_corridor
      name: puerta del backstage
      aliases: [backstage, fondo, detrás]
      door_id: backstage_door
  illustration_path: images/locations/jazz_club_interior.jpg
```

---

### Hooks de Location — sistema de handlers

Las habitaciones con lógica especial tienen un archivo Python en `game_data/handlers/`.
El engine registra los handlers al cargar el juego.

```
game_data/
├── files/
│   ├── locations.yaml
│   ├── items.yaml
│   ├── doors.yaml       ← nuevo
│   ├── globals.yaml     ← nuevo
│   ├── npcs.yaml
│   └── clues.yaml
└── handlers/
    ├── __init__.py
    ├── jazz_club.py     ← lógica del club
    ├── office.py        ← lógica del despacho
    └── street.py        ← lógica de la calle
```

**Ejemplo de handler:**
```python
# game_data/handlers/jazz_club.py

def on_enter(location, player, engine):
    """Al entrar al club por primera vez, activar rastro de sangre."""
    if not location.visited:
        engine.activate_local_global("blood_trail", ["jazz_club", "backstage_corridor"])

def on_before_command(location, player, action, engine):
    """Antes de cada comando en el club."""
    # Ejemplo: si el barman está presente y el jugador intenta irse
    if action.get("action") == "move" and engine.npc_present("jack_napier_barman"):
        # El barman podría intervenir
        pass
```

**Registro en el engine:**
```python
engine.register_handlers("jazz_club", jazz_club)
```

---

## Sistema de visibilidad

### globals.yaml — nuevo archivo

```yaml
global_objects:
  - id: floor
    name: suelo
    synonyms: [suelo, suelo, tierra, piso]
    base_description: El suelo bajo tus pies.
    flags: [SCENERY, FIXED]

  - id: walls
    name: paredes
    synonyms: [pared, paredes, muro, muros]
    base_description: Las paredes que te rodean.
    flags: [SCENERY, FIXED]

local_globals:
  - id: jazz_music
    name: música de jazz
    synonyms: [música, jazz, melodía, sonido]
    base_description: Un saxofón melancólico llena el ambiente con notas azules...
    flags: [SCENERY, INVISIBLE]
    visible_in: [jazz_club, backstage_corridor, band_room]

  - id: street_rain
    name: lluvia
    synonyms: [lluvia, tormenta, agua, llovizna]
    base_description: Una lluvia fina y persistente moja el asfalto...
    flags: [SCENERY]
    visible_in: [jazz_street, back_alley]

  - id: blood_trail
    name: rastro de sangre
    synonyms: [sangre, rastro, manchas, gotas]
    base_description: Pequeñas manchas oscuras salpican el suelo, frescas todavía...
    flags: [SCENERY, CLUE_SOURCE, INVISIBLE]  # INVISIBLE hasta que se active
    visible_in: [jazz_club, backstage_corridor]
```

### Orden de búsqueda de objetos

Cuando el engine resuelve un nombre a un objeto:

1. **Inventario del jugador** — prioridad máxima
2. **Children de la habitación actual** — objetos presentes en la sala
3. **NPCs de la habitación actual**
4. **GLOBAL_OBJECTS** — visibles en todas partes
5. **LOCAL_GLOBALS** donde `current_location_id` esté en `visible_in`
6. **Contenedores abiertos** en la habitación (children de children con flag OPEN+CONTAINER)

---

## Archivos afectados

### Archivos a reescribir
| Archivo | Cambio |
|---------|--------|
| `src/models/models.py` | Reescribir con nueva jerarquía |
| `src/models/core_data.py` | Añadir `Exit` actualizado, `GameFlag` |
| `game_data/files/locations.yaml` | Migrar al nuevo formato |
| `game_data/files/items.yaml` | Añadir flags, synonyms, children |

### Archivos nuevos
| Archivo | Propósito |
|---------|-----------|
| `game_data/files/doors.yaml` | Puertas como objetos únicos |
| `game_data/files/globals.yaml` | Global objects y local-globals |
| `game_data/handlers/__init__.py` | Registro de handlers |
| `game_data/handlers/jazz_club.py` | Lógica del club |

### Archivos que NO cambian
| Archivo | Razón |
|---------|-------|
| `src/engine.py` | Pipeline se mantiene — ajustes mínimos de resolución |
| `src/models/ai_enhancer.py` | Sin cambios |
| `src/models/game_context.py` | Ajustes menores |
| `src/utils/utils.py` | Sin cambios estructurales |
| `src/chains/` | Sin cambios |

---

## Impacto en el engine

El engine necesita ajustes menores (no reescritura) en:

1. **`_resolve()`** — implementar el orden de búsqueda de 6 pasos
2. **`_load_locations()`** — cargar doors.yaml y globals.yaml además de locations.yaml
3. **`_handle_move()`** — resolver exits por nombre/alias en lugar de por dirección
4. **Registro de hooks** — cargar handlers de `game_data/handlers/` y asociar a locations
5. **`_handle_examine()`** — buscar en children de contenedores abiertos

---

## Decisiones de diseño — registro

| Decisión | Alternativa descartada | Razón |
|----------|----------------------|-------|
| Opción B (rediseño limpio) | C (rediseño completo con engine) | Scope manejable; salto a C más fácil desde B |
| `set[GameFlag]` | IntFlag bitmask | Legibilidad > micro-optimización de memoria |
| Hooks en Python | Declarativo en YAML | Lógica narrativa compleja no encaja en YAML |
| Exits con nombre natural + alias | Solo brújula | Inmersión noir; el AI ya interpreta lenguaje libre |
| Puertas como objetos únicos (Door) | Duplicar en cada habitación | Elegancia, consistencia de estado, menos bugs |
| children como list[str] (IDs) | list[GameObject] (referencias) | Serialización limpia en YAML y SQLite |

---

## Lo que queda fuera de scope

- Dispatch system de Zork (M-HANDLED, M-NOT-HANDLED chain) — el pipeline actual es suficiente
- Sistema de combate — no aplica al género
- Mecánica de oscuridad/luz — flag LIT preparada pero sin implementar
- Load game (reconstrucción desde JSON) — deuda técnica preexistente, se mantiene pendiente
