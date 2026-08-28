"""How you start things. Works on macOS, Linux and Windows.

    python run.py                    EVERYTHING on this machine  (trying things out, solo)
    python run.py board              ONLY the board + feeds      (whoever hosts it for the team)
    python run.py mine assigner-A    ONLY your piece, pointed at $BOARD_URL from team.env
    python run.py fresh [mode]       same, but wipe board.db first (the board persists!)

On a four-person team you almost always want the last one. There is ONE board.

You normally do not type `python run.py` — use the wrapper for your machine:

    mac / linux      ./run
    windows          .\\run.ps1      (PowerShell)   or   run   (cmd)
"""
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time

# unbuffered, so you see the banners even when output is piped somewhere
try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:
    pass

ROOT = pathlib.Path(__file__).resolve().parent
PY = os.environ.get("PYTHON") or sys.executable

PIECES = {
    "assigner-A": ["assigners.naive", "A", "8101"],
    "assigner-B": ["assigners.naive", "B", "8102"],
    "replanner":  ["replanner.naive", "8103"],
    "monitor":    ["monitor.naive", "8104"],
}


def spawn(module_args):
    return subprocess.Popen([PY, "-m", *module_args], cwd=str(ROOT))


def describe():
    subprocess.call([PY, "-c", "import board.config as c; print(c.describe())"], cwd=str(ROOT))


def my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))          # nothing is sent; this just picks the LAN interface
        return s.getsockname()[0]
    except OSError:
        return socket.gethostname()
    finally:
        s.close()


def wait_on(procs):
    """Keep the children alive until ctrl-c, then stop them.

    A plain `kill` (SIGTERM) has to take the children down too, or the ports
    stay busy and the next `run` fails with 'address already in use'.
    """
    def on_term(*_):
        raise KeyboardInterrupt

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, on_term)
    try:
        while True:
            for p in procs:
                if p.poll() is not None:
                    print(f"\na piece exited (code {p.returncode}) — stopping the rest.")
                    raise KeyboardInterrupt
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("\nstopping…")
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


def main(argv):
    argv = list(argv)

    if argv and argv[0] == "fresh":
        argv.pop(0)
        db = ROOT / "board.db"
        if db.exists():
            db.unlink()
        print("board.db wiped — starting empty")

    mode = argv[0] if argv else "all"

    if mode in ("-h", "--help", "help"):
        print(__doc__)
        return 0

    if mode == "mine":
        piece = argv[1] if len(argv) > 1 else ""
        if piece not in PIECES:
            print("which piece? assigner-A | assigner-B | replanner | monitor")
            return 2
        print(f"running {piece} against the team board:")
        describe()
        print()
        return subprocess.call([PY, "-m", *PIECES[piece]], cwd=str(ROOT))

    if mode == "board":
        print("hosting the board for the team. everyone points BOARD_URL here.")
        procs = [spawn(["board.serve"])]
        time.sleep(1)
        print(f"  tell your team:  BOARD_URL=http://{my_ip()}:8080")
        wait_on(procs)
        return 0

    if mode != "all":
        print(f"unknown mode: {mode} — try: (nothing) | board | mine <piece> | --help")
        return 2

    procs = [spawn(["board.serve"])]
    time.sleep(1.2)
    for args in PIECES.values():
        procs.append(spawn(args))
    print("""
  everything is up ON THIS MACHINE. fine for trying things out — but a team of
  four needs ONE board with four pieces pointing at it. see `run --help`.
""")
    describe()
    print("""
  watch it:   http://localhost:8080/
  break it:   inject late   (or close-runway | race | bad-clock | no-gate | all)
  ctrl-c to stop.
""")
    wait_on(procs)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
