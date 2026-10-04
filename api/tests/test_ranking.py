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


def test_inflected_and_multiword_matching():
    assert _appears_in("llevar", "las circunstancias que han llevado a mi confinamiento")
    assert _appears_in("llevar a", "que han llevado a mi confinamiento")
    assert not _appears_in("mirar hacia arriba", "Ella miró la palabra en el diccionario.")


def test_part_of_speech_wins_for_base_form():
    ranked = rank([LEAD_GUIDE, LEAD_NOUN], surface="lead", usage=Usage(pos="noun"), context="a pipe made of lead")
    assert ranked[0]["text"] == "plomo"
