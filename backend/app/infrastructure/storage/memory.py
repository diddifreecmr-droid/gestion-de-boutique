"""`FileStorage` en mémoire : tests et démonstration (tout est perdu à l'arrêt).

`available = False` simule un stockage en panne (`StorageUnavailable`), pour prouver que
l'envoi échoue explicitement et n'inscrit rien en base.
"""

import threading

from app.application.attachments.ports import FileStorage, MissingFile, StorageUnavailable
from app.domain.attachments.values import FileFormat


class MemoryFileStorage(FileStorage):
    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, FileFormat]] = {}
        self._lock = threading.Lock()
        self.available = True

    def put(self, key: str, content: bytes, file_format: FileFormat) -> None:
        self._require_available()
        with self._lock:
            self._objects[key] = (bytes(content), FileFormat(file_format))

    def get(self, key: str) -> bytes:
        self._require_available()
        with self._lock:
            found = self._objects.get(key)
        if found is None:
            msg = f"Objet absent du stockage : {key}"
            raise MissingFile(msg)
        return found[0]

    def keys(self) -> list[str]:
        """Clés stockées (tests : vérifier qu'un envoi refusé n'a rien écrit)."""
        with self._lock:
            return sorted(self._objects)

    def _require_available(self) -> None:
        if not self.available:
            msg = "Stockage des fichiers indisponible : réessayer"
            raise StorageUnavailable(msg)
