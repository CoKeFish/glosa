"""How this glosa runs. One codebase, two modes:

- selfhost (default): one person on their own computer. No sign-in; everything belongs to
  the local user. Extras can be installed through Docker.
- hosted: a web service (app.glosa.suchima.com). Accounts by invitation, sign-in required,
  Docker extras disabled, cloud AI with the server's keys.

Read on every call rather than at import, so tests can switch modes.
"""

import os


def mode() -> str:
    return "hosted" if os.environ.get("GLOSA_MODE", "selfhost").strip().lower() == "hosted" else "selfhost"


def hosted() -> bool:
    return mode() == "hosted"


def public_url() -> str:
    """Where invitation links point, e.g. https://app.glosa.suchima.com."""
    return os.environ.get("GLOSA_PUBLIC_URL", "http://localhost:5174").rstrip("/")


def secure_cookies() -> bool:
    """Cookies only over HTTPS. On by default when hosted; off for local development."""
    default = "true" if hosted() else "false"
    return os.environ.get("GLOSA_SECURE_COOKIES", default).lower() == "true"
