# Requerimientos de glosa

> **Tipo:** Reference · **Fecha:** 2026-10-04 · **Estado:** borrador para revisar
>
> Lista extraída de las funciones públicas de LingQ (centro de ayuda, blog, foro, fichas de las tiendas y reseñas; ver [Fuentes](#fuentes)). Cada fila anota cómo se comporta LingQ, porque ese detalle es lo que no se puede reconstruir después sin volver a investigar. Las prioridades son una propuesta, no una decisión.

## Alcance

glosa replica el núcleo de LingQ: leer contenido propio, consultar palabras mientras se lee, llevar el estado de cada palabra y repasar lo guardado. Añade dos cosas que LingQ no tiene: detección automática de phrasal verbs y modelos de IA configurables.

**Fuera de alcance**

| Qué | Por qué |
|---|---|
| Cursos y biblioteca de contenido: cursos guiados, Mini Stories, guías de gramática, lecciones compartidas por otros usuarios, suscripción a cursos, tienda de lecciones | Decisión del 2026-10-04: glosa trabaja solo con contenido que el usuario importa |
| Tutores, intercambio de escritura, foro, desafíos, rankings | Propuesto: dependen de una comunidad y de un servicio central; glosa es personal y auto-hospedado |
| Monedas y avatar | Propuesto: gamificación cosmética, las reseñas la describen como secundaria |

> En LingQ un libro importado se guarda como un "curso" que agrupa lecciones. glosa necesita igual un contenedor **Libro → secciones**; eso es estructura de importación, no "la parte de cursos" descartada.

**Prioridades:** `P0` MVP (lo que el README ya promete) · `P1` siguiente · `P2` más adelante.

## 1. Lector

| ID | Requerimiento | Comportamiento en LingQ | Prio |
|---|---|---|---|
| LEC-01 | Colorear cada palabra según su estado | Azul = nueva (nunca vista), amarillo = guardada (estados 1–4), sin resaltar = conocida. Las frases guardadas se resaltan en otro color (naranja) | P0 |
| LEC-02 | Panel al pulsar una palabra | Muestra hasta 3 significados sugeridos, acceso a diccionarios, barra de estado, etiquetas, notas y audio de la palabra | P0 |
| LEC-03 | Guardar una palabra ("crear un LingQ") | Se guarda el término, el significado elegido y la frase donde apareció, como contexto | P0 |
| LEC-04 | Estados de palabra | 1 Nueva, 2 Reconocida, 3 Familiar, 4 Aprendida, Conocida, Ignorada. Se puede cambiar en cualquier dirección en cualquier momento | P0 |
| LEC-05 | El estado es global por idioma | Marcar una palabra la actualiza en todo el contenido de ese idioma | P0 |
| LEC-06 | Varios significados por término | Se pueden añadir significados propios o tomarlos de un diccionario | P0 |
| LEC-07 | Guardar frases | Selección arrastrando, hasta 8 palabras. Las palabras dentro de una frase también se guardan por separado. LingQ además sugiere frases relacionadas (subrayado gris) | P0 |
| LEC-08 | Ignorar palabras | Nombres propios, números, etc.: salen del vocabulario y de las estadísticas | P0 |
| LEC-09 | Pasar de página marca las azules restantes como conocidas | Configurable; existe un artículo de ayuda dedicado a qué hacer cuando ocurre por accidente, así que necesita deshacer | P0 |
| LEC-10 | Recordar la posición de lectura | Vuelve al punto exacto donde se dejó | P0 |
| LEC-11 | Idioma de los significados configurable | El usuario elige en qué idioma ve las traducciones | P0 |
| LEC-12 | Contadores por lección | Palabras nuevas (cantidad y porcentaje), guardadas y conocidas; sirve para estimar dificultad antes de leer | P1 |
| LEC-13 | Vista por oración | Una oración a la vez, con traducción, audio y lista del vocabulario de esa oración | P1 |
| LEC-19 | Seleccionar frases de cualquier longitud y oraciones completas | Arrastrar resalta el rango en vivo; doble clic selecciona la oración. Se traducen solas (local, y con IA a petición). Solo las de hasta 8 palabras se pueden guardar como término, como en LingQ: las oraciones se traducen para entenderlas, no se repasan. Petición del 2026-10-04 | P0 |
| LEC-20 | Traductor local sin IA | LibreTranslate (Argos Translate) en su propio contenedor, sin conexión tras descargar los modelos. Intercambiable con la IA en Ajustes | P0 |
| LEC-14 | Traducción de oración y de lección completa | "Translate sentence" y "Translate lesson" (la traducción aparece debajo de cada línea) | P1 |
| LEC-15 | Atajos de teclado | ←/→ palabra resaltada anterior/siguiente · ↑/↓ recorrer significados · Enter guardar · 1–4 estado · K conocida · X ignorar · B siguiente azul · H escribir significado · D diccionario · T etiqueta · S audio de palabra · A audio de oración · Shift+T traducir oración · Shift+←/→ página | P1 |
| LEC-16 | Modo automático | Al salir de una palabra azul se guarda sola con el significado sugerido. Viene activado por defecto | P1 |
| LEC-17 | Ajustes del lector | Tamaño de fuente, interlineado, tema claro/oscuro, voz TTS, mostrar vocabulario en vista por oración, activar/desactivar etiquetas automáticas | P1 |
| LEC-18 | Marcar lección como terminada | Al terminar muestra resumen y la envía a la lista de reproducción | P1 |

### Phrasal verbs

Petición del 2026-10-04. LingQ no los detecta: resalta palabra por palabra y deja que el usuario seleccione la frase a mano, sin indicar dónde empieza o termina. Van en P0 porque cambian el modelo de datos: un término puede ocupar varias palabras no contiguas, y añadirlo después obliga a rehacer el lector y el vocabulario.

| ID | Requerimiento | Detalle | Prio |
|---|---|---|---|
| PV-01 | Detectar phrasal verbs automáticamente al procesar el texto | El sistema marca inicio y fin sin que el usuario seleccione nada | P0 |
| PV-02 | Distinguir el uso phrasal del literal según el contexto | "She looked up the word" es phrasal; "she looked up the chimney" es verbo + preposición. Se decide por aparición, no por lista de palabras | P0 |
| PV-03 | Detectar phrasal verbs separados | "turn the light off" → "turn off": las dos partes forman una unidad aunque haya palabras en medio | P0 |
| PV-04 | Mostrar la unidad en el lector | Marca visual que une las partes. Al pulsar cualquiera de ellas el panel abre el phrasal verb completo, con opción de ver la palabra suelta | P0 |
| PV-05 | Guardar por forma base | "turned off", "turns off" y "turning it off" son el mismo término "turn off", con un solo estado | P0 |
| PV-06 | Corregir la detección | El usuario puede marcar "no es phrasal verb" o ajustar los límites; la detección no será perfecta | P1 |
| PV-07 | Detectar expresiones automáticamente | Modismos, frases hechas y locuciones de Wiktionary (~13.000 en inglés, sin conexión): "in spite of", "by and large", "make up one's mind" (encaja con "made up her mind"). Se filtran combinaciones que casi siempre son literales ("on the floor", "of his", "come to") | P0 |
| PV-08 | Clics en capas | Primer clic: la unidad más amplia que contiene la palabra (expresión, luego phrasal verb); cada clic más sobre la misma palabra baja un nivel hasta la palabra sola | P0 |

### Diccionario

Petición del 2026-10-04: un diccionario que sirva para varios idiomas y al que se puedan añadir más. Por ahora, solo inglés.

| ID | Requerimiento | Detalle | Prio |
|---|---|---|---|
| DIC-01 | Significados sugeridos en el idioma de significados | Como los "Popular Meanings" de LingQ: traducciones cortas ("turn off" → apagar), no definiciones. Pulsar una la guarda. Se busca la forma del texto, su forma base y la forma a la que remite el diccionario ("led" → lead), priorizando la categoría gramatical que tiene la palabra en la oración | P0 |
| DIC-02 | Diccionarios por idioma, intercambiables | Cada idioma declara sus diccionarios; añadir uno no toca el resto de la app. Inglés: Wiktionary vía Kaikki (traducciones a muchos idiomas y definiciones en inglés, incluye phrasal verbs) | P0 |
| DIC-06 | Ordenar los significados por cómo encajan en la oración, sin IA | Señales: la traducción local de la oración contiene el candidato ("…han llevado a…" → llevar a), la forma flexionada pertenece a la entrada ("led" es de lead/guiar, no de lead/plomo, que hace "leaded"), categoría gramatical, verbo + preposición ("led to"), transitividad, parecido con un modelo local de embeddings y frecuencia en el idioma de significados. El ganador claro se marca "encaja mejor" | P0 |
| DIC-03 | Enlaces a diccionarios externos | Como los diccionarios integrados de LingQ: WordReference, Cambridge y Google Translate, según tu idioma | P0 |
| DIC-04 | Guardar en caché las consultas | Cada término se pide una sola vez al servicio externo | P0 |
| DIC-05 | Diccionario bilingüe sin conexión | Hoy la traducción al español viene de la IA o de los enlaces; falta una fuente bilingüe local | P2 |

### Gramática

Petición del 2026-10-04. LingQ no la detecta; solo tiene guías de gramática aparte.

| ID | Requerimiento | Detalle | Prio |
|---|---|---|---|
| GRA-01 | Detectar estructuras gramaticales en cada oración | Inglés: tiempos continuos y perfectos, futuro con will y going to, condicional, modales, used to, pasiva, condicionales con if, oraciones de relativo, comparativo, superlativo, there is/are | P0 |
| GRA-02 | Mostrarlas desde la palabra seleccionada | El panel lista las estructuras de la oración con su fragmento, el verbo base ("led" → lead) y una explicación con su equivalente en el idioma de explicaciones ("have led" = han llevado). Al pulsar una se resaltan sus palabras en el texto | P0 |
| GRA-05 | Explicar la gramática de la oración con IA | En el idioma de explicaciones, usando las estructuras detectadas como guía | P1 |
| GRA-03 | Reglas por idioma | Cada idioma aporta sus propias reglas y explicaciones | P0 |
| GRA-04 | Repasar por estructura | Filtrar oraciones guardadas por tipo de estructura | P2 |

## 2. Importación

| ID | Requerimiento | Comportamiento en LingQ | Prio |
|---|---|---|---|
| IMP-01 | Importar archivos de libro | EPUB, PDF, DOCX, TXT, MOBI. Sin soporte de DRM | P0 |
| IMP-02 | Partir contenido largo automáticamente | Un libro se divide en varias lecciones consecutivas | P0 |
| IMP-03 | Pegar texto manualmente | Formulario con título, texto, imagen opcional y audio opcional | P0 |
| IMP-04 | Importar un artículo desde una URL | En la app: URL, texto, archivo o escaneo | P1 |
| IMP-05 | Extensión de navegador | Importa la página actual en dos clics (Chrome, Firefox, Safari, Edge) | P2 |
| IMP-06 | Importar YouTube | Requiere subtítulos; crea lección con video, transcripción y audio | P2 |
| IMP-07 | Importar audio y transcribirlo | Whisper, 99 idiomas. Límites: 60 min y 60 MB por archivo; 600 min/mes en Premium | P2 |
| IMP-08 | Adjuntar audio a un texto | Archivo subido o URL externa | P2 |
| IMP-09 | Importar vocabulario desde CSV | Columnas: `term, phrase, tag1, tag2, meaninglanguage1, meaning1, meaninglanguage2, meaning2` | P2 |
| IMP-10 | Escanear texto impreso (OCR) | Opción "scan" en la app móvil | P2 |
| IMP-11 | Netflix y otros sitios de streaming | Vía extensión, a partir de los subtítulos | P2 |

## 3. Vocabulario

| ID | Requerimiento | Comportamiento en LingQ | Prio |
|---|---|---|---|
| VOC-01 | Lista de todo lo guardado | Pestañas: todo, frases, pendientes de repaso | P0 |
| VOC-02 | Editar un término | Significados, estado, etiquetas, notas | P0 |
| VOC-03 | Buscar y filtrar | Por estado, etiqueta, libro, lección y fecha de repaso | P1 |
| VOC-04 | Cambiar el estado de varios términos a la vez | Acción en lote sobre la lista | P1 |
| VOC-05 | Etiquetas propias | Se añaden a mano a cualquier término | P1 |
| VOC-06 | Exportar | CSV y mazo de Anki | P1 |
| VOC-07 | Etiquetas gramaticales automáticas | Para verbos: infinitivo, tiempo, persona. Solo en algunos idiomas | P2 |
| VOC-08 | Filtrar por tipo de término | Palabra, frase o phrasal verb. LingQ solo distingue términos y frases | P1 |

## 4. Repaso

| ID | Requerimiento | Comportamiento en LingQ | Prio |
|---|---|---|---|
| REP-01 | Repetición espaciada según el estado | Estado 1 → 1 día · 2 → 3 días · 3 → 1 semana · 4 → 2 semanas, luego 1 mes, luego 3 meses. Las conocidas nunca vuelven | P0 |
| REP-02 | Tarjetas | Término → significado + frase de contexto | P0 |
| REP-03 | Subida de estado al acertar | Dos aciertos seguidos en una sesión suben un nivel; también se cambia a mano desde la tarjeta | P0 |
| REP-04 | Elegir qué repasar | Pendientes del día, una lección, una página, una oración o cualquier lista filtrada | P1 |
| REP-05 | Más tipos de actividad | Tarjeta inversa, completar hueco (cloze), opción múltiple, dictado. Se elige cuáles entran en la sesión | P1 |
| REP-06 | Tamaño de sesión configurable | Número de términos por sesión | P1 |
| REP-07 | Actividades de oración | Ordenar la oración, emparejar, dictado de oración, hablar con evaluación | P2 |
| REP-08 | Recordatorio diario | Correo "LingQs del día", hasta 200 términos | P2 |

## 5. Audio y video

| ID | Requerimiento | Comportamiento en LingQ | Prio |
|---|---|---|---|
| AUD-01 | Reproductor por lección | Con velocidad ajustable | P1 |
| AUD-02 | TTS de palabra y de oración | Se usa cuando no hay audio real; la voz se elige en ajustes | P1 |
| AUD-03 | Sincronizar texto y audio | "Generate audio timestamps" alinea automáticamente; la precisión depende de que el texto coincida con el audio | P2 |
| AUD-04 | Modo karaoke | El texto se resalta mientras suena el audio | P2 |
| AUD-05 | Audio real por oración | Con marcas de tiempo, la vista por oración reproduce el audio original en vez de TTS | P2 |
| AUD-06 | Listas de reproducción | Las lecciones terminadas entran solas; listas propias, reproducción continua y aleatoria | P2 |
| AUD-07 | Lección con video | Video de YouTube con transcripción que avanza | P2 |

## 6. Estadísticas y metas

| ID | Requerimiento | Comportamiento en LingQ | Prio |
|---|---|---|---|
| EST-01 | Palabras conocidas | Cuenta las marcadas conocidas más las de estado 4. Es la métrica principal | P0 |
| EST-02 | Términos guardados y aprendidos | Totales y por día | P1 |
| EST-03 | Palabras leídas | Automático al leer | P1 |
| EST-04 | Meta diaria y racha | La racha se mantiene cumpliendo la meta del día; la meta es configurable | P1 |
| EST-05 | Historial filtrable | Por rango de fechas y por métrica | P1 |
| EST-06 | Tiempo de escucha | Automático desde el reproductor y las listas | P2 |
| EST-07 | Registro manual de actividad externa | Lectura, escucha, habla y escritura hechas fuera de la app | P2 |

## 7. Inteligencia artificial

| ID | Requerimiento | Comportamiento en LingQ | Prio |
|---|---|---|---|
| IA-01 | Significado según el contexto | El significado sugerido tiene en cuenta la oración donde aparece la palabra | P1 |
| IA-02 | "Explícame esto" | Explicación de una palabra o frase, guardada en las notas del término | P1 |
| IA-03 | Simplificar una lección | Un clic genera una versión con vocabulario y estructura más simples | P2 |
| IA-04 | Chat tutor (Lynx) | Conversa en el idioma meta y corrige; las palabras de sus respuestas se pueden guardar; la conversación se puede convertir en lección; modos estándar, coach y tutor | P2 |
| IA-05 | Voces TTS naturales | Voces de proveedores externos; la calidad baja en idiomas poco comunes | P2 |
| IA-06 | Pantalla de configuración de modelos | Elegir proveedor, modelo y clave por tipo de función (texto, voz, transcripción). LingQ no lo permite: el proveedor es fijo y va incluido en la suscripción. Llega con la primera función de IA | P1 |

## 8. Idiomas

| ID | Requerimiento | Comportamiento en LingQ | Prio |
|---|---|---|---|
| IDI-01 | Varios idiomas por usuario | Vocabulario, estadísticas y metas separados por idioma | P0 |
| IDI-04 | Tres idiomas independientes, como en LingQ | Interfaz (LingQ: General → Interface language), significados y explicaciones (LingQ: Reader → Dictionary languages) e idioma que se estudia. Petición del 2026-10-04 | P0 |
| IDI-02 | Segmentar idiomas sin espacios | Chino y japonés necesitan separador de palabras | P2 |
| IDI-03 | Escritura de derecha a izquierda y transliteración | Añadido en la versión 6.0 | P2 |

## 9. No funcionales

| ID | Requerimiento | Origen | Prio |
|---|---|---|---|
| NF-01 | Auto-hospedable, sin suscripción | README de glosa | P0 |
| NF-02 | Los datos son del usuario: exportación completa de vocabulario, estados y contenido | README de glosa | P0 |
| NF-03 | Lectura fluida en libros largos | LingQ lo resuelve partiendo en lecciones | P0 |
| NF-04 | Sincronizar progreso entre dispositivos | LingQ sincroniza web y móvil | P1 |
| NF-05 | Uso sin conexión | LingQ descarga lecciones y audio en móvil y sincroniza al reconectar | P2 |
| NF-06 | Apps móviles nativas | LingQ tiene iOS y Android | P2 |
| NF-08 | Paquetes de idioma: todo lo que depende del idioma (separar palabras, phrasal verbs, gramática, diccionarios) vive en un paquete por idioma. Añadir un idioma es escribir un paquete y registrarlo | Petición del 2026-10-04 | P0 |
| NF-07 | Capa de abstracción de IA: las funciones hablan con una interfaz interna y nunca con un proveedor concreto, de modo que cambiar de modelo es configuración y no cambio de código. Debe admitir modelos locales además de servicios en la nube (lo de locales es propuesta) | Petición del 2026-10-04 | P0 |

## Puntos débiles de LingQ

Quejas repetidas en reseñas de uso prolongado, más una de uso propio. Cada una es una oportunidad de hacerlo mejor.

- **No detecta phrasal verbs.** Se puede seleccionar una frase y la IA la traduce, pero nada indica dónde empieza o termina el verbo. Experiencia propia, no de reseñas. Origen de PV-01 a PV-05.
- **La cola de repaso se desborda.** Todo lo que se consulta entra al SRS y a los pocos días hay cientos de pendientes sin forma de acotarlos. Afecta a REP-01 y REP-04.
- **El conteo de palabras conocidas se infla.** Cada forma conjugada o declinada cuenta como palabra distinta, lo que distorsiona la métrica en idiomas con mucha flexión. Afecta a EST-01.
- **La segmentación de chino falla.** Palabras mal cortadas que el diccionario no encuentra. Afecta a IDI-02.
- **El audio de palabra usa TTS aunque exista audio real.** Afecta a AUD-02 y AUD-05.
- **Las transcripciones automáticas cortan oraciones a la mitad**, y entonces la traducción de oración deja de servir. Afecta a IMP-07.
- **No hay repetición en bucle del audio.** Afecta a AUD-01.
- **Demasiados ajustes sin explicar** y búsqueda poco fiable. Afecta a LEC-17 y VOC-03.

## Decisiones abiertas

1. **¿Contar palabras por forma o por lema?** LingQ cuenta por forma. Por lema es más fiel, pero exige un lematizador por idioma. PV-05 ya obliga a llevar los verbos a su forma base, lo que inclina hacia lema al menos en inglés.
2. **¿De dónde salen los significados en español?** LingQ usa los que eligieron otros usuarios; glosa no tiene comunidad. Hoy: Wiktionary (en inglés), IA y enlaces externos. Falta una fuente bilingüe local (DIC-05).
3. **¿Audio en el MVP?** El README solo habla de libros; aquí todo el audio quedó en P1/P2.

**Resueltas**

- **Proveedor de IA** (2026-10-04): configurable por el usuario, detrás de una capa de abstracción. Ver IA-06 y NF-07.
- **Primer idioma** (2026-10-04): inglés; el resto se añade como paquetes de idioma (NF-08).
- **Cómo detectar phrasal verbs** (2026-10-04): el analizador sintáctico (spaCy) marca las partículas, incluidas las separadas, y una lista curada añade los verbos preposicionales ("look after"). La IA confirma o descarta el uso phrasal al explicar. Límite conocido: "looked up the chimney" tiene la misma sintaxis que "looked up the address", así que el analizador la marca como phrasal y queda en manos de la IA y del usuario.

## Fuentes

Consultadas el 2026-10-04.

- Centro de ayuda de LingQ: [crear LingQs](https://lingq-support.groovehq.com/help/how-do-i-create-lingqs) · [estados](https://lingq-support.groovehq.com/help/can-you-explain-a-lingqs-status) · [SRS](https://lingq-support.groovehq.com/help/how-does-the-lingq-srs-review-work) · [estado en tarjetas](https://lingq-support.groovehq.com/help/how-does-the-lingq-status-change-when-i-use-flashcards) · [frases](https://lingq-support.groovehq.com/help/can-i-save-or-create-lingqs-for-phrases) · [filtros de vocabulario](https://lingq-support.groovehq.com/help/how-and-why-to-filter-your-vocabulary-list-like-a-pro) · [etiquetas gramaticales](https://lingq-support.groovehq.com/help/grammar-tagging-and-filtering-vocabulary) · [exportar](https://lingq-support.groovehq.com/help/how-to-export-all-of-your-vocabulary) · [importar vocabulario](https://lingq-support.groovehq.com/help/how-to-import-vocabulary) · [marcas de tiempo](https://lingq-support.groovehq.com/help/how-does-timestamping-work-in-sentence-view) · [registro de lectura y escucha](https://lingq-support.groovehq.com/help/how-do-i-record-my-listening-and-reading) · [estadísticas](https://lingq-support.groovehq.com/help/understanding-lingq-statistics)
- LingQ: [guía de importación](https://www.lingq.com/blog/complete-guide-importing-lingq/) · [reseña propia 2026](https://www.lingq.com/blog/lingq-review/) · [soporte de la app iOS](https://www.lingq.com/en/ios-app-support/) · [lecciones con IA](https://www.lingq.com/en/news/lingq-launches-ai-lessons/) · [noticias](https://www.lingq.com/en/news/) · [ficha en App Store](https://apps.apple.com/us/app/language-learning-lingq/id379385811)
- Foro de LingQ: [qué es Lynx AI](https://forum.lingq.com/t/what-is-lynx-ai-in-lingq/2609825) · [changelog 2025-10-21](https://forum.lingq.com/t/changelog-october-21-2025-plus-tier-enhanced-chat-modes-ai-voices-ai-explain/2213712)
- Reseñas: [All Language Resources](https://www.alllanguageresources.com/lingq-review/) · [Lingtuitive](https://lingtuitive.com/blog/lingq-review) · [Actual Fluency](https://actualfluency.com/lingq) · [Languavibe](https://languavibe.com/lingq-review/)
- Atajos de teclado: [Tutorial Tactic](https://tutorialtactic.com/blog/lingq-shortcuts/)
