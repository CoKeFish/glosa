from app.dictionary.ranking import Usage, _appears_in, rank

LEAD_METAL = {"text": "emplomar", "sense": "to cover, fill, or affect with lead", "tags": ["transitive"],
              "word": "lead", "part_of_speech": "verb", "forms": ["leads", "leading", "leaded"]}
LEAD_GUIDE = {"text": "llevar", "sense": "guide or conduct in a certain course", "tags": ["transitive"],
              "word": "lead", "part_of_speech": "verb", "forms": ["leads", "leading", "led"]}
LEAD_NOUN = {"text": "plomo", "sense": "chemical element", "tags": [], "word": "lead",
             "part_of_speech": "noun", "forms": ["leads"]}


def test_inflected_form_rules_out_other_entry():
    ranked = rank([LEAD_METAL, LEAD_NOUN, LEAD_GUIDE], surface="led", usage=Usage(pos="verb"),
                  context="the circumstances which have led to my confinement")
    assert ranked[0]["text"] == "llevar"
    assert ranked[0].get("fits")


def test_sentence_translation_picks_the_sense():
    run_race = {"text": "correr", "sense": "to move swiftly", "word": "run", "part_of_speech": "verb", "forms": ["runs"]}
    run_office = {"text": "postularse", "sense": "to be a candidate", "word": "run", "part_of_speech": "verb",
                  "forms": ["runs"]}
    ranked = rank([run_office, run_race], surface="run", usage=Usage(pos="verb"),
                  context="The children run to school.", context_translation="Los niños corren a la escuela.")
    assert ranked[0]["text"] == "correr"


def test_partial_match_on_the_verb_beats_no_match():
    lie_untruth = {"text": "mentir", "sense": "tell an intentional untruth", "word": "lie", "part_of_speech": "verb",
                   "forms": ["lies", "lied"]}
    lie_situated = {"text": "estar ubicado", "sense": "be situated", "word": "lie", "part_of_speech": "verb",
                    "forms": ["lies", "lay", "lain"]}
    ranked = rank([lie_untruth, lie_situated], surface="lie", usage=Usage(pos="verb"),
                  context="phenomena which lie outside its common experience",
                  context_translation="fenómenos que están fuera de su experiencia común")
    assert ranked[0]["text"] == "estar ubicado"


def test_part_of_speech_used_in_the_sentence_wins():
    slang = {"text": "piba", "sense": "(slang) woman or girl", "word": "broad", "part_of_speech": "noun", "forms": []}
    wide = {"text": "amplio en extensión", "sense": "Wide in extent or scope.", "word": "broad",
            "part_of_speech": "adj", "forms": ["broader"], "from_definition": True}
    ranked = rank([slang, wide], surface="broader", usage=Usage(pos="adj"),
                  context="Men of broader intellect know", context_translation="Los hombres de intelecto más amplio saben")
    assert ranked[0]["text"] == "amplio en extensión"


def test_comparative_form_gets_its_own_meaning():
    wide = {"text": "abierto", "sense": "Extended; open.", "word": "broad", "term": "broad",
            "part_of_speech": "adj", "forms": ["broader"], "from_definition": True}
    more = {"text": "más amplio", "sense": "comparative form of broad: more broad", "word": "broader",
            "term": "broader", "part_of_speech": "adj", "forms": [], "from_definition": True, "degree_form": True}
    ranked = rank([wide, more], surface="broader", usage=Usage(pos="adj"), context="Men of broader intellect know")
    assert ranked[0]["text"] == "más amplio"


def test_stem_needs_a_real_ending():
    assert not _appears_in("mentir", "en su visión mental")  # "mental" is not a form of "mentir"
    assert _appears_in("mentir", "me mintió") is False  # stem change: not detected, but no false match
    assert _appears_in("mentir", "nos mienten") is False
    assert _appears_in("mentir", "le estaba mintiendo") is False
    assert _appears_in("duda", "tengo dudas")
    assert _appears_in("correr", "los niños corren a la escuela")


def test_inflected_and_multiword_matching():
    assert _appears_in("llevar", "las circunstancias que han llevado a mi confinamiento")
    assert _appears_in("llevar a", "que han llevado a mi confinamiento")
    assert not _appears_in("mirar hacia arriba", "Ella miró la palabra en el diccionario.")


def test_part_of_speech_wins_for_base_form():
    ranked = rank([LEAD_GUIDE, LEAD_NOUN], surface="lead", usage=Usage(pos="noun"), context="a pipe made of lead")
    assert ranked[0]["text"] == "plomo"
