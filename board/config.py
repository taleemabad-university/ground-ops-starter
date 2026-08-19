"""Where everything lives. GIVEN.

There is ONE board for the whole team. Your four pieces run in four different
places and all point at it — that is the entire idea, and it is why nothing here
is allowed to assume localhost.

Set it once, in `team.env` at the root of the repo, and everybody uses the same
file:

    BOARD_URL=http://192.168.1.42:8080
    ASSIGNER_A_URL=http://192.168.1.11:8101
    ASSIGNER_B_URL=http://192.168.1.12:8101
    REPLANNER_URL=http://192.168.1.13:8103
    MONITOR_URL=http://192.168.1.14:8104

Anything not set falls back to localhost, so a single laptop still works for
trying things out. Environment variables win over the file.
"""
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / "team.env"


def _load():
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


_load()

BOARD_URL = os.environ.get("BOARD_URL", "http://127.0.0.1:8080").rstrip("/")
BOARD_PORT = int(os.environ.get("PORT", os.environ.get("BOARD_PORT", "8080")))

# name -> (env var, localhost fallback)
_PIECES = {
    "assigner-A": ("ASSIGNER_A_URL", "http://127.0.0.1:8101"),
    "assigner-B": ("ASSIGNER_B_URL", "http://127.0.0.1:8102"),
    "replanner":  ("REPLANNER_URL",  "http://127.0.0.1:8103"),
    "monitor":    ("MONITOR_URL",    "http://127.0.0.1:8104"),
}

PIECES = {name: os.environ.get(env, default).rstrip("/")
          for name, (env, default) in _PIECES.items()}


def describe():
    lines = [f"board      {BOARD_URL}"]
    lines += [f"{n:<10} {u}" for n, u in PIECES.items()]
    return "\n".join("  " + ln for ln in lines)
