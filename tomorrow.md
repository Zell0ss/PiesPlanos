# Tomorrow — Session Handoff

**Fecha:** 2026-03-18
**Rama:** main
**Commit:** 3bb75a7

---

## Qué se hizo esta sesión

### Fixes del test battery (bateria_tests.md)
- **Exits serialización**: el AI veía IDs internos (`backstage_corridor`). Ahora recibe `{to: "Corredor del backstage", commands: ["backstage", "norte", ...]}`.
- **NPC "None" al final**: `must_include=None` se inyectaba literalmente en el prompt. Ahora solo se incluye cuando tiene valor.
- **NPC idioma + puntuación**: prompt reescrito — responde en español castellano, usa guión largo (—) para diálogo, tono noir años 30.
- **"mirar a Eddie" → excepción**: el resolver encontraba a Crazy Eddie (nombre completo del AI) y luego llamaba `npc.examine()` que no existía. Añadido `examine()` a `NPC` y a `GameObject` base.
- **Inventario en inglés**: `_handle_inventory` traducido al español.
- **"coger la pistola" no entendido**: añadidos `_handle_take` y `_handle_drop` funcionales (respetan flag TAKEABLE/FIXED), y "take"/"drop" al router y al AI context.

### Convenciones IF implementadas
- **Footer de habitación determinista** (nunca AI-enhanced): `Puedes ver: ...`, `X está aquí.`, `Salidas: destino [comando] · ...`
- **`_room_footer()`** reutilizado en `_handle_look` y `_handle_move`.
- **Partial name match**: "jack" encuentra "Jack Napier" por primera palabra.

### game_context.py
- `items` ahora es lista de nombres (no dict de IDs).
- `people` añadido (lista de nombres de NPCs en la sala).
- Exits serializados como dicts legibles.

---

## Estado actual del juego (jugable)

| Comando | Estado |
|---------|--------|
| mirar / look | ✅ |
| examinar X / ver X / mira el X | ✅ |
| ir a X / entrar / norte / n | ✅ |
| salidas | ✅ (footer) |
| hablar con X / hablar con el barman | ✅ Jack responde en español con — |
| preguntar a X "cosa" | ✅ |
| inventario | ✅ |
| coger X | ✅ |
| dejar X | ✅ |
| mirar a NPC (examinar NPC) | ✅ |

---

## Próximas tareas (por orden de impacto)

1. **Segunda ronda del test battery** — el usuario va a probar de nuevo con los fixes actuales y reportar los resultados en `bateria_tests.md`. Habrá nuevos bugs menores.

2. **`_handle_talk` — Jack Napier con pistas reales** — el handler ya funciona y el prompt de Jack está completo, pero las pistas (`jenny_body_located`, `jenny_identity`, `jenny_boutique_location`) no se conectan aún al sistema de clues. Hablar con Jack debería revelar pistas condicionalmente.

3. **Hora como objeto global** — el usuario sugirió que la hora (el reloj del bar) sea un objeto global para que no sea inventada cada vez. Añadir a `globals.yaml` como `local_global` del `jazz_club` con descripción fija (`visible_in: [jazz_club]`).

4. **Crazy Eddie jugable** — Eddie está en `jazz_street` y sus pistas requieren `jenny_body_located`. Probar flujo completo desde la calle.

---

## Backlog (no urgente)

### Resolver — superficies y transparencia
El resolver actual busca en 6 pasos (inventario → habitación → NPCs → globals → puertas → contenedores abiertos). Le falta:
- **SURFACE**: objetos encima de superficies (e.g., libro sobre escritorio) — el flag existe pero el Step 6 solo mira CONTAINER+OPEN, no SURFACE.
- **TRANSPARENT**: contenedor cerrado pero visible (examinar sí, coger no).
- **Contenedores anidados**: solo 1 nivel de profundidad.
Afecta al `office_desk` del despacho cuando ese área sea jugable.

### NPC — clue discovery system
Conectar `clues_required` del YAML con la lógica del engine. Actualmente Jack y Eddie tienen pistas definidas pero no se revelan condicionalmente.

### Descripción de objetos — `enhance_examine` vs `enhance_description`
`Item.examine()` llama a `enhance_description` (genérico). Existe `enhance_examine` (específico para ítems) que da mejores descripciones. Considerar usar `enhance_examine` para ítems y `enhance_description` solo para habitaciones/NPCs.

### Save/load completo
`extract_delta` / `apply_delta` implementados pero el load desde Telegram no está conectado. Guardar funciona; cargar una partida anterior no.

### Inventario visible en room footer
Cuando el jugador lleva algo en el inventario, ¿debería aparecer en la descripción de sala? IF clásica no lo hace (el inventario es tuyo, no de la sala). Decisión pendiente.

### `pending_attempts` DB column
Existe la columna pero el contador en-memoria (`_pending` dict) es el que controla el soft-limit. Si se quiere persistir el contador entre reinicios del bot, habría que sincronizarlo con la DB.
