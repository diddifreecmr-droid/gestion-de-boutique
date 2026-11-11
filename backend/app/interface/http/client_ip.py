"""Adresse IP du client, pour la limitation de débit (specs § 8.1).

Par défaut : `request.client.host`, l'adresse de la connexion TCP. `X-Forwarded-For` est
**ignoré** (n'importe quel client peut l'écrire) sauf si l'adresse directe appartient à un
proxy de confiance déclaré (`AUTH_TRUSTED_PROXIES`, liste d'IP/CIDR, vide par défaut).

Proxy de confiance : on lit `X-Forwarded-For` **de droite à gauche** (chaque proxy ajoute à
droite l'adresse qu'il a vue) en sautant les proxys de confiance ; la première adresse non
fiable est le client. Ce qui est plus à gauche a pu être forgé par le client et n'est pas lu.
Une entrée illisible arrête la lecture : on garde alors le dernier proxy de confiance vu.

Production (T25) : l'adresse de Caddy (réseau Docker) **doit** être déclarée, sinon tous les
clients partagent le compteur de l'IP du proxy. Si uvicorn réécrit déjà l'adresse
(`--proxy-headers` + `--forwarded-allow-ips`), `request.client.host` est le vrai client, non
fiable, et il est pris tel quel : les deux mécanismes ne se cumulent pas.
"""

from collections.abc import Sequence
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address

from starlette.requests import Request

IpNetwork = IPv4Network | IPv6Network
FORWARDED_FOR = "x-forwarded-for"


def _parse(text: str) -> IPv4Address | IPv6Address | None:
    try:
        return ip_address(text.strip())
    except ValueError:  # entrée illisible : le motif est traité par l'appelant (voir docstring)
        return None


class ClientIpResolver:
    def __init__(self, trusted_proxies: Sequence[IpNetwork] = ()) -> None:
        self._trusted = tuple(trusted_proxies)

    def _is_trusted(self, address: IPv4Address | IPv6Address | None) -> bool:
        return address is not None and any(address in network for network in self._trusted)

    def resolve(self, request: Request) -> str:
        direct = request.client.host if request.client else ""
        if not self._is_trusted(_parse(direct)):
            return direct
        hops = [
            entry
            for header in request.headers.getlist(FORWARDED_FOR)
            for entry in header.split(",")
        ]
        client = direct
        for entry in reversed(hops):
            address = _parse(entry)
            if address is None:
                return client
            client = str(address)
            if not self._is_trusted(address):
                return client
        return client
