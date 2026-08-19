"""Board + feeds, in one process, on :8080. GIVEN.

    python -m board.serve

./run starts this for you, along with the naive pieces.
"""
from board.api import PORT, serve
from feeds.stream import start


def main():
    start()
    print(f"board listening on :{PORT}   feeds streaming", flush=True)
    print(f"  ->  http://localhost:{PORT}/   the live board, in a browser", flush=True)
    print("  GET  /board  /now  /unassigned  /log", flush=True)
    print("  POST /claim  /slot /release     /flag", flush=True)
    serve()


if __name__ == "__main__":
    main()
