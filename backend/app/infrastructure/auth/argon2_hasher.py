"""`PasswordHasher` Argon2id (argon2-cffi), sel aléatoire de 16 octets par empreinte.

Paramètres par défaut : profil **RFC 9106 « deuxième choix recommandé »** (mémoire réduite),
celui d'argon2-cffi : `time_cost=3`, `memory_cost=65 536 Kio` (64 Mio), `parallelism=4`,
`hash_len=32`, `salt_len=16`, type `ID`. Environ 50 ms par empreinte sur un VPS courant ; les
tests passent des paramètres réduits. L'empreinte encode ses paramètres : `needs_rehash` signale
une empreinte plus faible que les paramètres courants, et `Login` la remplace.

- secret différent → `False` (cas normal) ;
- empreinte illisible ou corrompue → **exception** (`InvalidHashError`), jamais `False` : une
  base abîmée doit se voir, pas ressembler à un code faux.
"""

from argon2 import PasswordHasher as _Argon2
from argon2 import Type
from argon2.exceptions import VerifyMismatchError

from app.application.identity.ports import PasswordHasher

DEFAULT_TIME_COST = 3
DEFAULT_MEMORY_COST_KIB = 65_536
DEFAULT_PARALLELISM = 4
HASH_LENGTH = 32
SALT_LENGTH = 16


class Argon2PasswordHasher(PasswordHasher):
    def __init__(
        self,
        *,
        time_cost: int = DEFAULT_TIME_COST,
        memory_cost_kib: int = DEFAULT_MEMORY_COST_KIB,
        parallelism: int = DEFAULT_PARALLELISM,
    ) -> None:
        self._argon2 = _Argon2(
            time_cost=time_cost,
            memory_cost=memory_cost_kib,
            parallelism=parallelism,
            hash_len=HASH_LENGTH,
            salt_len=SALT_LENGTH,
            type=Type.ID,
        )

    def hash(self, secret: str) -> str:
        return self._argon2.hash(secret)

    def verify(self, secret_hash: str, secret: str) -> bool:
        try:
            return self._argon2.verify(secret_hash, secret)
        except VerifyMismatchError:
            return False

    def needs_rehash(self, secret_hash: str) -> bool:
        return self._argon2.check_needs_rehash(secret_hash)
