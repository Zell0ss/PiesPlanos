# Tomorrow — Session Handoff

**Fecha:** 2026-04-01
**Rama:** main
**Commit:** 1b76daf

---

## Qué se hizo esta sesión

### Motor de interacciones (use X with Y)
- `Interaction` dataclass en `core_data.py` con `from_dict()` para manejar la keyword `with`
- Campo `interactions: list[Interaction]` en `Item`
- Carga YAML: `with` → `with_item` automáticamente
- `_find_interaction()` — búsqueda simétrica Option A (primero en obj_a, luego en obj_b)
- `_check_conditions()` — `has_item` / `has_clue` / `game_flag`; distingue fallo físico vs fallo de conocimiento
- `_apply_effects()` — `set_flag`, `reveal_clue`, `unlock_exit`, `message`
- `_handle_use()` — pipeline completo con hint GUMSHOE en fallo de conocimiento
- Router actualizado: `use` → `_handle_use`
- Prompt AI actualizado: `use` devuelve `target` + `recipient`
- 26 tests nuevos, 191 total

### Contenido YAML
- Item `balas_extra` (.38 Special, marca Peters) en `band_room`
- Clue `shooting_angle` en `clues.yaml`
- `dropped_gun.interactions`:
  - `use with jenny_dead_body` → revela `shooting_angle` (sin condiciones)
  - `use with balas_extra` → `set_flag: pistola_cargada` (requiere llevar la pistola)

### Fix producción
- Bot llevaba sin reiniciarse desde el 18 de marzo
- Comando: `sudo systemctl restart lovecraft`
- **Añadir al workflow**: siempre reiniciar tras desplegar código nuevo

---

## Comportamiento verificado en producción

- Balas en el suelo del camerino (sin cogerlas) + pistola en inventario → `usar balas con pistola` → funciona
- El resolver busca cada objeto independientemente: inventario → habitación → globals
- La condición `has_item: dropped_gun` fuerza que lleves la pistola encima (no vale que esté en el suelo)
- Orden simétrico verificado: `usar pistola con balas` = `usar balas con pistola`

---

## Próximas tareas (por orden de impacto)

1. **Segunda ronda del battery** — probar con el bot reiniciado. En especial:
   - `usar pistola con el cuerpo` → pista del ángulo del disparo
   - `usar balas con pistola` / `usar pistola con balas` → simetría
   - `coger balas` → inventario → `usar pistola con balas` → cargada
   - Hablar con Jack Napier (¿responde bien en español?)

2. **Clue discovery en conversaciones** — Jack tiene `clues_required` en el YAML pero `_handle_talk` no los evalúa. Conectar el sistema de pistas a las respuestas de NPCs.

3. **Save/load** — `extract_delta`/`apply_delta` implementados; falta que `_restore_or_create` cargue el delta al restaurar sesión (está casi hecho, solo falta conectar).

4. **Hora como objeto global** — el reloj del bar como `local_global` de `jazz_club` para que no invente la hora cada vez.

---

## Backlog

### Resolver — superficies y transparencia
- `SURFACE`: items encima de superficies (Step 6 solo mira CONTAINER+OPEN)
- `TRANSPARENT`: contenedor cerrado visible (examinar sí, coger no)
- Afecta al `office_desk` cuando el despacho sea jugable

### Clue discovery system completo
Conectar `clues_required` del YAML con la lógica del engine. Actualmente Jack y Eddie tienen pistas definidas pero no se revelan condicionalmente.

### Efectos futuros en interactions
- `transform_item`: cambiar descripción de un objeto por flag (p.ej. "pistola vacía" vs "pistola cargada")
- `enable_npc_clue`: desbloquear qué puede revelar un NPC
- `conditional_examine`: override de `examine` con condiciones

### Descripción dinámica según flags
Cuando `pistola_cargada` está activo, la descripción de la pistola debería cambiar. Actualmente `base_description` es estática.

### Save/load completo desde Telegram
`extract_delta`/`apply_delta` implementados. Cargar partida anterior al hacer `/start`.

### `pending_attempts` DB persistente
El contador en-memoria se resetea al reiniciar. Si se quiere persistir el soft-limit entre reinicios, sincronizar con la columna DB.
