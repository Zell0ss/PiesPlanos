# [Proyecto] - Briefing para Claude

> **Propósito**: Transferir conocimiento entre Claude Code y Claude Web, y servir como resumen ejecutivo.
>
> **Audiencia**: Claude AI (ambas instancias) y desarrollador

---

## Qué es este proyecto

[2-3 líneas: qué hace, para qué sirve, caso de uso principal]

---

## Cómo funciona (flujo de datos)

\```
1. INGESTION: [Fuente] → [Formato crudo]
2. PROCESSING: [Proceso principal] → [Transformación]
3. STORAGE: [Dónde se guarda]
4. OUTPUT: [Resultado final]
\```

Descripción textual del flujo:
[2-3 párrafos explicando el flujo end-to-end]

---

## Stack técnico

- **Lenguaje**: Python 3.X
- **Frameworks/Libs principales**: 
  - [Lib 1]: [Para qué]
  - [Lib 2]: [Para qué]
- **Base de datos**: [Tipo] - [Por qué esta elección]
- **APIs externas**: 
  - [API 1]: [Para qué]
  - [API 2]: [Para qué]
- **Infraestructura**: [Local/Cloud, servicios necesarios]

---

## Comandos CLI principales

| Comando | Qué hace | Ejemplo de uso |
|---------|----------|----------------|
| `comando1 <args>` | [Descripción clara] | `comando1 --flag valor` |
| `comando2` | [Descripción clara] | `comando2` |
| `comando3 [opts]` | [Descripción clara] | `comando3 --output file.txt` |

---

## Estructura del proyecto

\```
proyecto/
├── src/
│   ├── modulo1/       # [Responsabilidad principal]
│   ├── modulo2/       # [Responsabilidad principal]
│   └── main.py        # Entry point CLI
├── tests/             # Tests con pytest
├── data/              # [Qué tipo de datos, propósito]
└── outputs/           # [Qué se genera aquí]
\```

**Módulos clave**:
- **modulo1**: [Responsabilidad, qué componentes incluye]
- **modulo2**: [Responsabilidad, qué componentes incluye]

---

## Decisiones de diseño críticas

### [Nombre decisión 1]

**Por qué**: [Razón principal en 1-2 líneas]

**Alternativas descartadas**: [Opciones que NO se eligieron y por qué]

**Trade-off aceptado**: [Qué se sacrificó con esta decisión]

---

### [Nombre decisión 2]

**Por qué**: [Razón principal]

**Alternativas descartadas**: [Opciones descartadas]

**Trade-off aceptado**: [Qué se sacrificó]

---

[Incluir 2-4 decisiones más importantes]

---

## Datos y modelos

### Modelo de datos principal

**Entidad principal**: [NombreEntidad]

Campos clave:
- `campo1`: [Tipo] - [Propósito, validaciones]
- `campo2`: [Tipo] - [Propósito, validaciones]
- `campo3`: [Tipo] - [Propósito, validaciones]

**Relaciones**: [Si hay relaciones entre entidades, describirlas]

---

### Flujo de transformación de datos

\```
[Input Format] 
  → [Proceso 1: validación/limpieza] 
  → [Formato Intermedio] 
  → [Proceso 2: transformación] 
  → [Output Format]
\```

**Formatos**:
- Input: [Descripción del formato de entrada]
- Output: [Descripción del formato de salida]

---

## Configuración

### Variables de entorno críticas

**Requeridas**:
- `VAR_REQUERIDA_1`: [Dónde obtener, formato esperado]
- `VAR_REQUERIDA_2`: [Dónde obtener, para qué se usa]

**Opcionales**:
- `VAR_OPCIONAL_1`: [Default: X, cuándo cambiar]
- `VAR_OPCIONAL_2`: [Default: Y, propósito]

### Archivos de configuración

[Si aplica: ubicación, formato (YAML/JSON/INI), qué configuran]

---

## Estado actual

**Versión**: [X.Y.Z]

**Última actualización**: [Fecha - Mes YYYY]

### Funcionalidades

✅ **Implementadas**:
- [Feature 1]
- [Feature 2]
- [Feature 3]

🚧 **En desarrollo**:
- [Feature en progreso, si aplica]

📋 **TODOs conocidos**:
- [Mejora pendiente 1]
- [Mejora pendiente 2]

---

## Casos de uso típicos

### Caso 1: [Nombre descriptivo]

**Objetivo**: [Qué quiere lograr el usuario]

**Flujo**:
1. [Paso 1 con comando]
2. [Paso 2 con comando]
3. [Resultado esperado]

**Ejemplo**:
\```bash
comando ejemplo arg1 arg2
\```

---

### Caso 2: [Nombre descriptivo]

**Objetivo**: [Qué quiere lograr]

**Flujo**:
1. [Paso]
2. [Paso]
3. [Resultado]

---

[Incluir 2-3 casos de uso más comunes]

---

## Limitaciones y caveats

### Limitaciones conocidas

- **Limitación 1**: [Qué no puede hacer y por qué]
- **Limitación 2**: [Restricción técnica o de diseño]

### Comportamientos no intuitivos

- **Caveat 1**: [Comportamiento que podría sorprender]
- **Caveat 2**: [Edge case a tener en cuenta]

---

## Contexto de desarrollo

**Motivación original**: [Por qué se creó este proyecto]

**Evolución**: [Si ha cambiado desde la idea inicial]

**Uso actual**: 
- Frecuencia: [Diario/Semanal/Mensual/Ad-hoc]
- Contexto: [Cuándo y cómo se usa]

---

## Patrones de código clave

### Patrón de uso más común

\```python
# [Explicación: cuándo usar este patrón]
# Ejemplo concreto del uso típico
código_ejemplo()
\```

---

### Patrón de extensión

\```python
# Cómo añadir [feature común, ej: nueva fuente de datos]
# Template que se sigue en el proyecto

class NuevaFeature(BaseClass):
    def metodo_requerido(self):
        # Implementación
        pass
\```

---

## Notas para Claude Web

**Contexto para discusiones de arquitectura**:
- [Información útil para entender decisiones]
- [Restricciones o requirements del proyecto]

**Decisiones pendientes**:
- [Decisión arquitectónica que requiere input]

**Áreas de mejora**:
- [Dónde el proyecto podría optimizarse]

---

## Notas para Claude Code

**Convenciones del proyecto**:
- [Estilo de código específico]
- [Patrones que se siguen consistentemente]

**Áreas que requieren atención**:
- [Módulos con deuda técnica]
- [Código que necesita refactoring]

**Al contribuir**:
- [Patrón a seguir para nuevas features]
- [Tests requeridos antes de merge]

---

*Última actualización: [Fecha]*  
*Generado desde: [commit/branch/fecha de código]*
\```

**Instrucciones específicas para generar BRIEFING**:

1. **Longitud objetivo**: 2-3 páginas (no más)
2. **Tono**: Técnico pero directo, optimizado para lectura rápida
3. **Priorizar**: Decisiones sobre implementación, "por qué" sobre "cómo"
4. **Incluir**: Solo lo necesario para que otro Claude entienda el proyecto sin ver código

**Casos de uso del BRIEFING**:
- Claude Web lee esto antes de discutir arquitectura
- Claude Code lee esto para entender contexto antes de contribuir
- Desarrollador lee esto como resumen ejecutivo al volver al proyecto
- Onboarding rápido (5-10 minutos de lectura)

---

## Checklist de Generación

Antes de entregar, verifica:

### README.md
- [ ] Descripción de 1 línea clara
- [ ] Quick Start funciona (probado mentalmente)
- [ ] Features en bullets
- [ ] Links a otras docs

### ARCHITECTURE.md
- [ ] Diagrama Mermaid presente y útil
- [ ] Al menos 2 "Decisiones Clave" documentadas
- [ ] Flujo de datos paso a paso
- [ ] Responde "¿por qué esto así?"

### QUICKSTART.md
- [ ] Máximo 5 pasos
- [ ] Output esperado en cada paso
- [ ] Tiempo estimado incluido
- [ ] Links a siguientes pasos

### BRIEFING.md
- [ ] Stack técnico completo
- [ ] Decisiones críticas documentadas (2-4)
- [ ] Casos de uso típicos (2-3)
- [ ] Comandos CLI principales listados
- [ ] Notas específicas para Claude Web y Claude Code
- [ ] Longitud: 2-3 páginas máximo

### General
- [ ] Nombres de archivos en MAYÚSCULAS
- [ ] Código en bloques markdown con sintaxis
- [ ] Sin TODOs o placeholders
- [ ] Consistencia de terminología

---

## Instrucciones de Ejecución

1. **Analiza el proyecto**:
   - Lee README actual (si existe)
   - Identifica tecnologías principales
   - Identifica flujo de datos principal
   - Detecta decisiones arquitectónicas no obvias

2. **Genera documentos en orden**:
   1. README.md
   2. BRIEFING.md (nuevo - crítico para intercambio Claude ↔ Claude)
   3. ARCHITECTURE.md (el más detallado)
   4. QUICKSTART.md
   5. docs/HOW-TO-*.md (según casos de uso detectados)
   6. .env.example
   7. CHANGELOG.md (solo si no existe)

3. **Prioriza**:
   - **Obligatorios**: README + BRIEFING + ARCHITECTURE + QUICKSTART
   - **Opcionales según complejidad**: HOW-TOs, REFERENCE
   - **Solo si no existe**: CHANGELOG

4. **Estilo**:
   - Tono: Directo, telegráfico
   - Público: "Yo del futuro" (humano) y Claude (AI)
   - Asumir: Conocimiento de Python y desarrollo
   - NO asumir: Recordar detalles del proyecto

---

## Ejemplos de Buenas Decisiones Documentadas

### ✅ Ejemplo bueno
```markdown
### ¿Por qué MariaDB en lugar de SQLite?

**Contexto**: Necesito cachear posts de múltiples fuentes sin re-procesar

**Opciones consideradas**:
1. SQLite - Simple, zero config
2. MariaDB - Mejor concurrencia
3. Redis - Cache rápido

**Decisión**: MariaDB

**Razones**:
- Plan futuro: dashboard web necesitará lecturas concurrentes
- Redis no persiste datos tras reinicio
- Ya uso MariaDB en otros proyectos → zero setup mental

**Trade-off**: Requiere servidor corriendo (vs SQLite file-based)
```

### ❌ Ejemplo malo
```markdown
### Base de datos

Uso MariaDB porque es mejor.
```

---

## Notas Finales

- **Minimalismo**: Solo documenta lo necesario
- **Claridad**: Preferir claridad sobre brevedad extrema
- **Mantenibilidad**: Docs fáciles de actualizar
- **Utilidad**: Cada doc debe responder preguntas específicas

Si tienes dudas sobre si documentar algo: **Documenta las decisiones, no la implementación.**