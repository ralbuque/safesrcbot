"""Regras que todo post precisa cumprir antes de ser publicado.

Isto é a última barreira contra texto ruim vindo do modelo (inclusive
conteúdo injetado por páginas web lidas na pesquisa). Mantenha simples e
determinístico.
"""

import re
from urllib.parse import urlparse

from .contagem import LIMITE_X, contar

_RE_MENCAO = re.compile(r"(?<![\w@])@\w+")
_RE_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_RE_HASHTAG = re.compile(r"(?<!\w)#\w+")
MAX_HASHTAGS = 2


def montar_texto_final(texto: str, fonte_url: str | None, incluir_link: bool) -> str:
    texto = texto.strip()
    if incluir_link and fonte_url:
        return f"{texto}\n\n{fonte_url.strip()}"
    return texto


def validar_gerado(texto: str, fonte_url: str, incluir_link: bool) -> list[str]:
    """Validação estrita para texto escrito pelo modelo. Retorna lista de erros."""
    erros: list[str] = []
    if not texto or not texto.strip():
        return ["texto vazio"]
    if _RE_URL.search(texto):
        erros.append("o texto não pode conter URLs (o link da fonte é anexado automaticamente)")
    if _RE_MENCAO.search(texto):
        erros.append("o texto não pode mencionar contas com @")
    if len(_RE_HASHTAG.findall(texto)) > MAX_HASHTAGS:
        erros.append(f"no máximo {MAX_HASHTAGS} hashtags")
    url = urlparse(fonte_url or "")
    if url.scheme != "https" or not url.netloc:
        erros.append("fonte_url precisa ser uma URL https válida")
    final = montar_texto_final(texto, fonte_url, incluir_link)
    tamanho = contar(final)
    if tamanho > LIMITE_X:
        erros.append(
            f"post final tem {tamanho} caracteres (limite {LIMITE_X}, link conta 23); "
            f"corte pelo menos {tamanho - LIMITE_X}"
        )
    return erros


def validar_aprovado(texto_final: str) -> list[str]:
    """Validação leve para texto revisado/editado por você na issue."""
    if not texto_final or not texto_final.strip():
        return ["texto vazio"]
    tamanho = contar(texto_final)
    if tamanho > LIMITE_X:
        return [f"post tem {tamanho} caracteres (limite {LIMITE_X})"]
    return []
