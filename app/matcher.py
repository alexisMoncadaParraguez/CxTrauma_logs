"""Clasifica una IP según los rangos CIDR de los bots conocidos."""

import ipaddress
from dataclasses import dataclass
from functools import lru_cache

from app.sources import BotRanges


@dataclass(frozen=True)
class Coincidencia:
    bot: str
    empresa: str


class Matcher:
    """Índice por longitud de prefijo: {versión: {prefijo: {red_int: (prioridad, coincidencia)}}}.

    Para buscar se prueba cada longitud de prefijo presente; así los rangos solapados se resuelven
    por prioridad (bot específico antes que nube genérica) sin depender del orden de carga.
    """

    def __init__(self, bots: list[BotRanges]):
        self._indice: dict[int, dict[int, dict[int, tuple[int, Coincidencia]]]] = {4: {}, 6: {}}
        for b in bots:
            coincidencia = Coincidencia(b.bot, b.empresa)
            for cidr in b.cidrs:
                try:
                    red = ipaddress.ip_network(cidr.strip(), strict=False)
                except ValueError:
                    continue
                por_prefijo = self._indice[red.version].setdefault(red.prefixlen, {})
                clave = int(red.network_address)
                actual = por_prefijo.get(clave)
                if actual is None or b.prioridad < actual[0]:
                    por_prefijo[clave] = (b.prioridad, coincidencia)
        self.buscar = lru_cache(maxsize=100_000)(self._buscar)

    def _buscar(self, ip: str) -> Coincidencia | None:
        try:
            direccion = ipaddress.ip_address(ip)
        except ValueError:
            return None
        if direccion.version == 6 and direccion.ipv4_mapped:
            direccion = direccion.ipv4_mapped
        bits = direccion.max_prefixlen
        valor = int(direccion)
        mejor: tuple[int, int, Coincidencia] | None = None  # (prioridad, -prefijo, coincidencia)
        for prefijo, redes in self._indice[direccion.version].items():
            mascara = ((1 << prefijo) - 1) << (bits - prefijo) if prefijo else 0
            hallado = redes.get(valor & mascara)
            if hallado:
                candidato = (hallado[0], -prefijo, hallado[1])
                if mejor is None or candidato[:2] < mejor[:2]:
                    mejor = candidato
        return mejor[2] if mejor else None
