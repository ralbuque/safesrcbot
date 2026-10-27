"""Histórico de posts (contas/<id>/historico.json), versionado no próprio repositório.

Serve para evitar repetir notícias e para dar ao modelo contexto do que já
foi publicado (variar categorias).
"""

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

MAX_ENTRADAS = 500
JANELA_CVE_DIAS = 7


def normalizar_url(url: str) -> str:
    p = urlparse(url.strip())
    host = p.netloc.lower().removeprefix("www.")
    caminho = p.path.rstrip("/")
    # descarta query de rastreamento (utm etc.) e fragmento
    return urlunparse(("https", host, caminho, "", "", ""))


def id_para(url: str) -> str:
    return hashlib.sha256(normalizar_url(url).encode()).hexdigest()[:16]


def normalizar_tema(tema: str) -> str:
    """'Impeachment do Collor (1992)' -> 'impeachment-do-collor-1992'."""
    t = unicodedata.normalize("NFKD", tema or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def carregar(caminho: Path) -> dict:
    if not caminho.exists():
        return {"posts": []}
    return json.loads(caminho.read_text(encoding="utf-8"))


def salvar(hist: dict, caminho: Path) -> None:
    hist["posts"] = hist["posts"][-MAX_ENTRADAS:]
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _cves(lista) -> set[str]:
    return {c.upper() for c in (lista or []) if re.fullmatch(r"CVE-\d{4}-\d{4,}", c, re.I)}


def verificar_duplicado(
    hist: dict,
    fonte_url: str,
    cves: list[str],
    agora: datetime | None = None,
    tema_chave: str | None = None,
    janela_tema_dias: int = 7,
) -> str | None:
    """Retorna o motivo se for duplicado, senão None."""
    agora = agora or datetime.now(timezone.utc)
    novo_id = id_para(fonte_url)
    novos_cves = _cves(cves)
    novo_tema = normalizar_tema(tema_chave or "")
    for p in hist["posts"]:
        if p.get("id") == novo_id:
            return f"esta fonte já foi usada em {p.get('data', '?')[:10]}"
        data = datetime.fromisoformat(p["data"]) if p.get("data") else None
        if not data:
            continue
        idade = agora - data
        if novos_cves and idade <= timedelta(days=JANELA_CVE_DIAS):
            repetidos = novos_cves & _cves(p.get("cves"))
            if repetidos:
                return f"{', '.join(sorted(repetidos))} já foi tema em {p['data'][:10]}"
        if novo_tema and idade <= timedelta(days=janela_tema_dias):
            if novo_tema == normalizar_tema(p.get("tema_chave") or ""):
                return f"o tema '{novo_tema}' já foi usado em {p['data'][:10]} (janela de {janela_tema_dias} dias)"
    return None


def registrar(hist: dict, entrada: dict) -> None:
    for p in hist["posts"]:
        if p["id"] == entrada["id"]:
            p.update(entrada)
            return
    hist["posts"].append(entrada)


def resumo_recente(hist: dict, n: int = 25) -> str:
    linhas = []
    for p in hist["posts"][-n:]:
        linhas.append(
            f"- {p.get('data', '')[:10]} [{p.get('categoria', '?')}] tema={p.get('tema_chave') or '?'} "
            f"| {p.get('titulo', '')}"
            + (f" ({', '.join(p['cves'])})" if p.get("cves") else "")
        )
    return "\n".join(linhas) or "(nenhum post ainda)"
