"""Grammar structure detection for English, from the dependency parse.

Each rule labels the tokens that make up the structure ("has been working" →
present perfect continuous) so the reader can highlight them. Labels and
explanations come in each explanation language the app supports.
"""

from spacy.tokens import Doc, Token

from app.languages.base import GrammarType

# id: (es label, es explanation, en label, en explanation)
_TEXTS = {
    "present_continuous": ("Presente continuo", "am/is/are + verbo en -ing. Algo que está pasando ahora o un plan cercano. «She is reading» = ella está leyendo.",
                           "Present continuous", "am/is/are + -ing verb. Something happening now or a near plan."),
    "past_continuous": ("Pasado continuo", "was/were + verbo en -ing. Algo que estaba pasando en un momento del pasado. «He was sleeping» = él estaba durmiendo.",
                        "Past continuous", "was/were + -ing verb. Something in progress at a moment in the past."),
    "future_continuous": ("Futuro continuo", "will be + verbo en -ing. Algo que estará pasando en un momento del futuro. «I will be working» = estaré trabajando.",
                          "Future continuous", "will be + -ing verb. Something in progress at a moment in the future."),
    "present_perfect": ("Presente perfecto", "have/has + participio. Equivale a «he/ha + participio»: un pasado que sigue conectado con el presente. «which have led» = que han llevado.",
                        "Present perfect", "have/has + past participle. A past action connected to the present."),
    "present_perfect_continuous": ("Presente perfecto continuo", "have/has been + verbo en -ing. Algo que empezó antes y sigue (o acaba de terminar). «She has been working» = ha estado trabajando.",
                                   "Present perfect continuous", "have/has been + -ing verb. Started in the past and still going (or just finished)."),
    "past_perfect": ("Pasado perfecto", "had + participio. Equivale a «había + participio»: algo anterior a otro momento del pasado. «had moved» = se había mudado.",
                     "Past perfect", "had + past participle. Something before another moment in the past."),
    "past_perfect_continuous": ("Pasado perfecto continuo", "had been + verbo en -ing. Algo que venía pasando hasta un momento del pasado. «had been looking» = había estado buscando.",
                                "Past perfect continuous", "had been + -ing verb. In progress up to a moment in the past."),
    "future_perfect": ("Futuro perfecto", "will have + participio. Equivale a «habrá + participio». «will have finished» = habrá terminado.",
                       "Future perfect", "will have + past participle. Finished by a moment in the future."),
    "conditional_perfect": ("Condicional perfecto", "would have + participio. Equivale a «habría + participio»: lo que habría pasado. «would have helped» = habría ayudado.",
                            "Conditional perfect", "would have + past participle. What would have happened."),
    "modal_perfect": ("Modal en pasado", "could/should/might/must have + participio. «should have gone» = debería haber ido; «might have seen» = pudo haber visto.",
                      "Modal perfect", "could/should/might/must have + past participle. Possibility, obligation or deduction about the past."),
    "future_will": ("Futuro con will", "will + verbo. Es el futuro simple: «will create» = creará. Predicción, decisión del momento o promesa.",
                    "Future with will", "will + verb. Prediction, on-the-spot decision or promise."),
    "going_to": ("Futuro con going to", "am/is/are going to + verbo. Equivale a «voy a / va a + verbo»: un plan o algo que se ve venir.",
                 "Future with going to", "be going to + verb. A plan or a prediction based on evidence."),
    "conditional_would": ("Condicional (would)", "would + verbo. Es el condicional: «would go» = iría. Situación hipotética o petición cortés.",
                          "Conditional (would)", "would + verb. Hypothetical situation or polite request."),
    "modal": ("Verbo modal", "can (poder), could (podría), may/might (puede que), must (deber), should (debería) + verbo sin «to».",
              "Modal verb", "can, could, may, might, must, should + base verb. Ability, permission, possibility or obligation."),
    "used_to": ("Used to", "used to + verbo. Equivale a «solía + verbo»: un hábito del pasado que ya no ocurre.",
                "Used to", "used to + verb. A past habit or state that is no longer true."),
    "passive": ("Voz pasiva", "be + participio. Equivale a «ser + participio» o «se + verbo»: importa lo que recibe la acción. «were sent» = fueron enviadas.",
                "Passive voice", "be + past participle. The focus is on what receives the action."),
    "conditional_clause": ("Oración condicional", "if (si) / unless (a menos que) + condición. Mira el tiempo de cada parte para saber si es real o hipotética.",
                           "Conditional clause", "if/unless + condition. The tenses of both parts tell real from hypothetical."),
    "relative_clause": ("Oración de relativo", "who/which/that (que, quien, el cual) + oración. Da información sobre el sustantivo que va justo antes. «the circumstances which have led…» = las circunstancias que han llevado…",
                        "Relative clause", "who/which/that + clause. Describes or identifies the noun right before it."),
    "comparative": ("Comparativo", "adjetivo + -er o more + adjetivo (+ than). Equivale a «más … (que)». «better than» = mejor que.",
                    "Comparative", "-er or more + adjective (+ than). Compares two things."),
    "superlative": ("Superlativo", "the + adjetivo + -est o the most + adjetivo. Equivale a «el más …». «the tallest» = el más alto.",
                    "Superlative", "the -est or the most + adjective. The extreme of a group."),
    "there_be": ("There is / there are", "Equivale a «hay» (there is / there are) o «había» (there was / there were).",
                 "There is / there are", "Says that something exists or is somewhere."),
}
GRAMMAR_TYPES = {
    "es": {k: GrammarType(k, v[0], v[1]) for k, v in _TEXTS.items()},
    "en": {k: GrammarType(k, v[2], v[3]) for k, v in _TEXTS.items()},
}

MODAL_FUTURE = {"will", "shall"}
RELATIVE_WORDS = {"who", "whom", "whose", "which", "that", "where", "when", "why"}


def _verb_structures(verb: Token) -> list[tuple[str, list[Token]]]:
    aux = sorted((c for c in verb.children if c.dep_ in ("aux", "auxpass")), key=lambda t: t.i)
    if not aux and verb.tag_ != "VBD":
        return []
    found = []
    modals = [a for a in aux if a.tag_ == "MD"]
    have = [a for a in aux if a.dep_ == "aux" and a.lemma_ == "have"]
    be_progressive = [a for a in aux if a.dep_ == "aux" and a.lemma_ == "be"] if verb.tag_ == "VBG" else []
    passive = [a for a in aux if a.dep_ == "auxpass"]
    core = [*aux, verb]

    # "be going to + verb" and "used to + verb" are their own structures.
    xcomp = next((c for c in verb.children if c.dep_ == "xcomp"), None)
    has_to = xcomp is not None and any(c.lower_ == "to" for c in xcomp.children)
    if verb.lemma_ == "go" and verb.tag_ == "VBG" and has_to and be_progressive:
        to = next(c for c in xcomp.children if c.lower_ == "to")
        return [("going_to", [*be_progressive, verb, to, xcomp])]
    if verb.lower_ == "used" and verb.tag_ == "VBD" and has_to:
        to = next(c for c in xcomp.children if c.lower_ == "to")
        return [("used_to", [verb, to, xcomp])]

    modal = modals[0].lemma_.lower() if modals else None
    if have:
        if modal in MODAL_FUTURE:
            kind = "future_perfect"
        elif modal == "would":
            kind = "conditional_perfect"
        elif modal:
            kind = "modal_perfect"
        elif have[0].tag_ == "VBD":
            kind = "past_perfect"
        else:
            kind = "present_perfect"
        if be_progressive and kind in ("present_perfect", "past_perfect"):
            kind += "_continuous"
        found.append((kind, core))
    elif be_progressive:
        if modal in MODAL_FUTURE:
            found.append(("future_continuous", core))
        elif be_progressive[0].tag_ == "VBD":
            found.append(("past_continuous", core))
        elif not modal:
            found.append(("present_continuous", core))
    elif modal:
        if modal in MODAL_FUTURE:
            found.append(("future_will", core))
        elif modal == "would":
            found.append(("conditional_would", core))
        else:
            found.append(("modal", core))

    if passive:
        found.append(("passive", [*passive, verb]))
    return found


def detect_grammar(doc: Doc, sentence_of: dict[int, int]) -> list[dict]:
    found: list[tuple[str, list[Token]]] = []
    for tok in doc:
        if tok.pos_ in ("VERB", "AUX") and tok.dep_ not in ("aux", "auxpass"):
            found.extend(_verb_structures(tok))
        if tok.lower_ in ("if", "unless") and tok.dep_ == "mark":
            found.append(("conditional_clause", [tok, tok.head]))
        if tok.dep_ == "relcl":
            rel = [c for c in tok.subtree if c.lower_ in RELATIVE_WORDS and c.i < tok.i]
            found.append(("relative_clause", [*rel[:1], tok]))
        if tok.tag_ in ("JJR", "RBR", "JJS", "RBS"):
            kind = "comparative" if tok.tag_ in ("JJR", "RBR") else "superlative"
            parts = [tok]
            if tok.lower_ in ("more", "most", "less", "least") and tok.head.pos_ in ("ADJ", "ADV"):
                parts.append(tok.head)
            than = next((t for t in doc[tok.i + 1 : tok.sent.end] if t.lower_ == "than"), None)
            if kind == "comparative" and than is not None:
                parts.append(than)
            found.append((kind, parts))
        if tok.dep_ == "expl" and tok.lower_ == "there" and tok.head.lemma_ == "be":
            found.append(("there_be", [tok, tok.head]))

    result, seen = [], set()
    for kind, tokens in found:
        indices = sorted({t.i for t in tokens})
        if (kind, tuple(indices)) in seen:
            continue
        seen.add((kind, tuple(indices)))
        result.append({"type": kind, "s": sentence_of.get(indices[0], 0), "i": indices})
    return result
