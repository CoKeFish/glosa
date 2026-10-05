"""Optional components the reader installs from the app: local voices, translators, the
offline dictionary. The core (database, API, web) is small; everything heavy is an extra.

Container extras run next to the API on its Docker network, under the network alias the
rest of the code already uses (`tts-kokoro`, `translator`, `ollama`…). The API reaches
Docker through its socket, and only ever touches the images and containers listed in
CATALOG: each one is labelled `glosa.extra=<id>`, and nothing without that label is
stopped or removed.
"""

import os
import socket
import threading
import time
from dataclasses import dataclass, field

import httpx

LABEL = "glosa.extra"
IMAGE_PREFIX = os.environ.get("GLOSA_IMAGE_PREFIX", "ghcr.io/cokefish/glosa")
HOST_OLLAMA = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434").rstrip("/")


@dataclass(frozen=True)
class ContainerSpec:
    image: str
    alias: str  # hostname the API uses to reach it
    env: dict[str, str] = field(default_factory=dict)
    volumes: dict[str, str] = field(default_factory=dict)  # named volume → path


@dataclass(frozen=True)
class Extra:
    id: str
    group: str  # voice | translation | dictionary | runtime
    size_mb: int  # approximate download
    container: ContainerSpec | None = None
    model: str | None = None  # an Ollama model
    requires: tuple[str, ...] = ()
    hidden: bool = False  # installed as a dependency, never listed on its own


CATALOG: dict[str, Extra] = {e.id: e for e in (
    Extra("voice-kokoro", "voice", 4950, ContainerSpec("ghcr.io/remsky/kokoro-fastapi-cpu:latest", "tts-kokoro")),
    Extra("voice-supertonic", "voice", 900, ContainerSpec(
        os.environ.get("GLOSA_SUPERTONIC_IMAGE", f"{IMAGE_PREFIX}-tts-supertonic:latest"), "tts-supertonic",
        volumes={"glosa-tts-supertonic-cache": "/root/.cache"})),
    Extra("translator-basic", "translation", 1300, ContainerSpec(
        "libretranslate/libretranslate:latest", "translator", env={"LT_LOAD_ONLY": "en,es,fr,pt,it"},
        volumes={"glosa-translator-models": "/home/libretranslate/.local"})),
    Extra("ollama", "runtime", 3500, ContainerSpec(
        "ollama/ollama:latest", "ollama", volumes={"glosa-ollama": "/root/.ollama"}), hidden=True),
    Extra("model-translategemma", "translation", 3300, model="translategemma:4b", requires=("ollama",)),
    Extra("dictionary-offline", "dictionary", 530),
)}

# Two one-click choices. Light: small and still fully offline for the basics. Recommended:
# the best reading experience, at a few gigabytes.
PRESETS = {
    "light": ("translator-basic", "voice-supertonic"),
    "recommended": ("model-translategemma", "voice-kokoro", "translator-basic", "dictionary-offline"),
}


class ExtrasError(Exception):
    pass


# --- Docker -----------------------------------------------------------------------------

def _docker():
    try:
        import docker

        client = docker.from_env(timeout=20)
        client.ping()
        return client
    except Exception as exc:  # the socket is not mounted, or Docker is not running
        raise ExtrasError("La app no puede usar Docker: monta /var/run/docker.sock en el servicio api") from exc


def docker_available() -> bool:
    try:
        _docker()
        return True
    except ExtrasError:
        return False


def _network(client) -> str:
    """The Docker network the API itself is on, so extras share it."""
    if os.environ.get("GLOSA_NETWORK"):
        return os.environ["GLOSA_NETWORK"]
    me = client.containers.get(socket.gethostname())
    return next(iter(me.attrs["NetworkSettings"]["Networks"]))


def _container(client, extra_id: str):
    found = client.containers.list(all=True, filters={"label": f"{LABEL}={extra_id}"})
    return found[0] if found else None


def _pull(client, image: str, report) -> None:
    try:
        client.images.get(image)
        return  # already here (built locally, or pulled before)
    except Exception:
        pass
    repo, _, tag = image.rpartition(":") if ":" in image.split("/")[-1] else (image, "", "latest")
    layers: dict[str, tuple[int, int]] = {}
    try:
        for event in client.api.pull(repo, tag=tag or "latest", stream=True, decode=True):
            detail = event.get("progressDetail") or {}
            if event.get("id") and detail.get("total"):
                layers[event["id"]] = (detail.get("current", 0), detail["total"])
            if layers:
                done, total = sum(c for c, _ in layers.values()), sum(t for _, t in layers.values())
                report(min(0.95, done / total), "downloading")
            if event.get("error"):
                raise ExtrasError(event["error"])
    except ExtrasError:
        raise
    except Exception as exc:
        raise ExtrasError(f"No se pudo descargar {image}: {exc}") from exc


def _start_container(extra: Extra, report) -> None:
    client = _docker()
    spec = extra.container
    _pull(client, spec.image, report)
    report(0.97, "starting")
    old = _container(client, extra.id)
    if old is not None:
        old.remove(force=True)
    network = _network(client)
    container = client.containers.create(
        spec.image,
        name=f"glosa-{extra.id}",
        environment=spec.env,
        volumes={name: {"bind": path, "mode": "rw"} for name, path in spec.volumes.items()},
        labels={LABEL: extra.id},
        restart_policy={"Name": "unless-stopped"},
        network=network,
        networking_config={network: client.api.create_endpoint_config(aliases=[spec.alias])},
    )
    container.start()


def _remove_container(extra: Extra) -> None:
    client = _docker()
    container = _container(client, extra.id)
    if container is not None:
        container.remove(force=True)
    for volume in extra.container.volumes:
        try:
            client.volumes.get(volume).remove(force=True)
        except Exception:
            pass
    try:  # free the disk; an image another container still uses stays
        client.images.remove(extra.container.image)
    except Exception:
        pass


# --- Ollama -----------------------------------------------------------------------------

_ollama_cache: tuple[float, str] = (0.0, HOST_OLLAMA)


def ollama_url() -> str:
    """Our own Ollama when it is installed as an extra, otherwise the host's."""
    global _ollama_cache
    if time.monotonic() - _ollama_cache[0] < 15:
        return _ollama_cache[1]
    url = HOST_OLLAMA
    try:
        if _container(_docker(), "ollama") is not None:
            url = "http://ollama:11434"
    except ExtrasError:
        pass
    _ollama_cache = (time.monotonic(), url)
    return url


def _host_ollama() -> bool:
    try:
        return httpx.get(f"{HOST_OLLAMA}/api/tags", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def _ollama_models(url: str) -> list[str]:
    try:
        return [m["name"] for m in httpx.get(f"{url}/api/tags", timeout=5).json().get("models", [])]
    except (httpx.HTTPError, ValueError):
        return []


def _pull_model(name: str, report) -> None:
    url = ollama_url()
    for _ in range(30):  # a fresh Ollama container takes a moment to answer
        if _ollama_models(url) or httpx.get(f"{url}/api/version", timeout=3).status_code == 200:
            break
        time.sleep(1)
    with httpx.stream("POST", f"{url}/api/pull", json={"model": name}, timeout=None) as resp:
        import json

        for line in resp.iter_lines():
            if not line:
                continue
            event = json.loads(line)
            if event.get("error"):
                raise ExtrasError(event["error"])
            if event.get("total"):
                report(min(0.99, event.get("completed", 0) / event["total"]), "downloading")


def _delete_model(name: str) -> None:
    httpx.request("DELETE", f"{ollama_url()}/api/delete", json={"model": name}, timeout=60)


# --- Status and jobs --------------------------------------------------------------------

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _set_job(extra_id: str, **fields) -> None:
    with _lock:
        _jobs.setdefault(extra_id, {}).update(fields)


def installed(extra_id: str) -> bool:
    extra = CATALOG[extra_id]
    if extra.container is not None:
        try:
            return _container(_docker(), extra_id) is not None
        except ExtrasError:
            return False
    if extra.model is not None:
        return extra.model in _ollama_models(ollama_url())
    if extra_id == "dictionary-offline":
        from app import offline_dictionary

        return offline_dictionary.ready()
    return False


def status() -> dict:
    with _lock:
        jobs = {k: dict(v) for k, v in _jobs.items()}
    docker_ok = docker_available()
    items = []
    for extra in CATALOG.values():
        if extra.hidden:
            continue
        job = jobs.get(extra.id, {})
        busy = job.get("state") in ("installing", "uninstalling")
        items.append({
            "id": extra.id, "group": extra.group, "size_mb": extra.size_mb,
            "installed": installed(extra.id) if not busy else job.get("state") == "uninstalling",
            "job": job or None,
            # A model needs an Ollama: the host's, or the one we install.
            "uses_host_ollama": extra.model is not None and _host_ollama(),
        })
    return {"docker": docker_ok, "items": items, "presets": PRESETS}


def _run(extra_id: str, action: str) -> None:
    extra = CATALOG[extra_id]

    def report(progress: float, phase: str) -> None:
        _set_job(extra_id, progress=round(progress, 3), phase=phase)

    try:
        if action == "install":
            for dep in extra.requires:
                if dep == "ollama" and _host_ollama():
                    continue  # the host already runs one
                if not installed(dep):
                    _run_dependency(dep)
            if extra.container is not None:
                _start_container(extra, report)
            elif extra.model is not None:
                _pull_model(extra.model, report)
            elif extra_id == "dictionary-offline":
                from app import offline_dictionary

                offline_dictionary.install(report)
        else:
            if extra.container is not None:
                _remove_container(extra)
            elif extra.model is not None:
                _delete_model(extra.model)
            elif extra_id == "dictionary-offline":
                from app import offline_dictionary

                offline_dictionary.uninstall()
        _set_job(extra_id, state="done", progress=1.0, phase=None, error=None)
    except Exception as exc:
        _set_job(extra_id, state="error", error=str(exc)[:300])


def _run_dependency(extra_id: str) -> None:
    extra = CATALOG[extra_id]
    _start_container(extra, lambda p, phase: None)


def start(extra_id: str, action: str) -> None:
    if extra_id not in CATALOG or CATALOG[extra_id].hidden:
        raise ExtrasError(f"Extra desconocido: {extra_id}")
    with _lock:
        if _jobs.get(extra_id, {}).get("state") in ("installing", "uninstalling"):
            return
        _jobs[extra_id] = {"state": "installing" if action == "install" else "uninstalling", "progress": 0.0,
                           "phase": None, "error": None}
    threading.Thread(target=_run, args=(extra_id, action), daemon=True).start()


def start_preset(name: str) -> list[str]:
    if name not in PRESETS:
        raise ExtrasError(f"Instalación desconocida: {name}")
    queued = [e for e in PRESETS[name] if not installed(e)]

    def run_in_order() -> None:  # one at a time: parallel downloads would only compete
        for extra_id in queued:
            start(extra_id, "install")
            while _jobs.get(extra_id, {}).get("state") == "installing":
                time.sleep(1)

    for extra_id in queued:
        _set_job(extra_id, state="queued", progress=0.0, phase=None, error=None)
    threading.Thread(target=run_in_order, daemon=True).start()
    return queued
