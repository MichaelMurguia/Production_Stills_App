from __future__ import annotations

import threading
import webbrowser
from pathlib import Path

import uvicorn

HOST = "127.0.0.1"
PORT = 8765


def main() -> None:
    threading.Timer(1.2, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
    # Reload watches only the code directories — data/ writes (candidates,
    # settings, references) must never restart the server mid-generation.
    root = Path(__file__).resolve().parents[1]
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info",
                reload=True, reload_dirs=[str(root / "app"), str(root / "scripts")])


if __name__ == "__main__":
    main()
