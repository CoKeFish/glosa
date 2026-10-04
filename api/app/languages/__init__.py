from functools import cache

from app.languages.base import Analysis, GrammarType, LanguagePack

__all__ = ["Analysis", "GrammarType", "LanguagePack", "available", "get_language", "UnsupportedLanguage"]


class UnsupportedLanguage(Exception):
    pass


def _english() -> LanguagePack:
    from app.languages.en import EnglishPack

    return EnglishPack()


# To add a language: write a pack under app/languages/<code>/ and register its factory here.
_FACTORIES = {
    "en": _english,
}


@cache
def get_language(code: str) -> LanguagePack:
    factory = _FACTORIES.get(code)
    if factory is None:
        raise UnsupportedLanguage(code)
    return factory()


def available() -> list[dict]:
    return [{"code": code, "name": get_language(code).name} for code in _FACTORIES]
