"""File watcher para el inbox (drop folder).

Detecta archivos nuevos en data/inbox/ y los procesa automáticamente.
Mueve los procesados a data/processed/ y los que fallan a data/rejected/.
"""
from __future__ import annotations

import json
import shutil
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .settings import settings


class InboxEventHandler(FileSystemEventHandler):
    """Handler que dispara `on_new_file` cuando se crea un archivo en inbox."""

    def __init__(self, on_new_file: Callable[[Path], None]):
        self.on_new_file = on_new_file

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        # Damos un pequeño delay para que el archivo termine de copiarse
        def _delayed():
            time.sleep(0.3)
            if path.exists() and path.stat().st_size > 0:
                self.on_new_file(path)
        threading.Thread(target=_delayed, daemon=True).start()


class InboxWatcher:
    """Watcher que monitorea el inbox y procesa automáticamente."""

    def __init__(self, on_new_file: Optional[Callable[[Path], None]] = None):
        self.observer: Optional[Observer] = None
        self._on_new_file = on_new_file
        self._running = False

    def start(self):
        if self._running:
            return
        handler = InboxEventHandler(
            self._on_new_file or self._default_handler
        )
        self.observer = Observer()
        self.observer.schedule(handler, str(settings.inbox_dir), recursive=False)
        self.observer.start()
        self._running = True
        print(f"[watcher] [OK] Watching {settings.inbox_dir}")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=2)
            self._running = False
            print("[watcher] stopped")

    def _default_handler(self, path: Path):
        """Handler por defecto: loguea y deja que el endpoint haga el resto."""
        print(f"[watcher] Nuevo archivo detectado: {path.name}")


# ----------------------------------------------------------------------
# Helpers de movimiento y parseo
# ----------------------------------------------------------------------

def parse_invoice_file(path: Path) -> Optional[dict]:
    """Parsea un archivo del inbox (.json o .txt con bloques clave:valor)."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")

    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError as e:
            print(f"[parse] ERROR JSON en {path.name}: {e}")
            return None

    if path.suffix.lower() == ".txt":
        # Formato simple:
        #   key: value
        #   (uno por línea)
        result = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                # Intentar castear amount
                if k == "amount":
                    try:
                        v = float(v.replace(",", "").replace(".", "").replace(" ", ""))
                        # Si tenía formato argentino (1.000,50), reinterpretar
                        if "," in text.split("amount:")[1].split("\n")[0]:
                            v = float(v / 100)  # muy naive, mejor regex
                    except ValueError:
                        pass
                result[k] = v
        return result or None

    return None


def move_file(src: Path, dst_dir: Path) -> Path:
    """Mueve `src` a `dst_dir` (sobrescribe si existe)."""
    dst = dst_dir / src.name
    if dst.exists():
        # Renombrar con timestamp para no pisar
        ts = time.strftime("%Y%m%d-%H%M%S")
        dst = dst_dir / f"{src.stem}.{ts}{src.suffix}"
    shutil.move(str(src), str(dst))
    return dst