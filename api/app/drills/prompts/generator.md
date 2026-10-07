# Generador de rondas

Este archivo es el prompt que glosa envía a la IA para crear una ronda de práctica. Puedes
editarlo: se lee de nuevo en cada ronda. También puedes guardar tu propia versión desde la
página Práctica (queda en tu cuenta y tiene prioridad sobre este archivo).

Marcadores que glosa rellena: {{native}} (idioma de las oraciones), {{plan}} (los 7 huecos
con sus temas), {{vocabulary}} (palabras que estás aprendiendo en el libro elegido).

---SYSTEM---
You write practice sentences for a {{native}} speaker who is learning English (level A2-B1).
Each sentence is written in {{native}}; the learner will translate it into English. Answer
only with a JSON object, no prose around it.

---PROMPT---
Write 7 sentences in {{native}}, one per slot below. Each sentence must force the learner to
use the slot's topics when translating it into English, without naming the rule. Sentences
are natural, everyday and varied (people, places, times), 8 to 20 words, and none of them
repeats another's structure. Do not translate anything for the learner.

Slots:
{{plan}}

Words the learner is studying in the book they are reading (use a few of them, in English
form, only where they fit naturally; it is fine to use none):
{{vocabulary}}

Return exactly:
{"items": [{"slot": 1, "spanish": "..."}, ... {"slot": 7, "spanish": "..."}]}
