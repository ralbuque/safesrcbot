"""Contagem de caracteres no estilo do X (twitter-text v3).

O X não conta caracteres "puros": cada URL vale 23, e caracteres fora de
algumas faixas (emojis, CJK etc.) valem 2. Acentos do português valem 1.
"""

import re
import unicodedata

LIMITE_X = 280
PESO_URL = 23

# Faixas de code points que pesam 1 (o resto pesa 2), conforme twitter-text v3.
_FAIXAS_PESO_1 = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))

_RE_URL = re.compile(r"https?://\S+", re.IGNORECASE)


def _peso(ch: str) -> int:
    cp = ord(ch)
    for ini, fim in _FAIXAS_PESO_1:
        if ini <= cp <= fim:
            return 1
    return 2


def contar(texto: str) -> int:
    """Retorna o tamanho do texto como o X conta."""
    texto = unicodedata.normalize("NFC", texto)
    total = 0
    pos = 0
    for m in _RE_URL.finditer(texto):
        total += sum(_peso(c) for c in texto[pos : m.start()])
        total += PESO_URL
        pos = m.end()
    total += sum(_peso(c) for c in texto[pos:])
    return total
