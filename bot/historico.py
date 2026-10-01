"""Histórico de posts (data/historico.json), versionado no próprio repositório.

Serve para evitar repetir notícias e para dar ao modelo contexto do que já
foi publicado (variar categorias).
"""

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

ARQUIVO = Path(__file__).resolve().parent.parent / "data" / "historico.json"
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


def carregar(caminho: Path = ARQUIVO) -> dict:
    if not caminho.exists():
        return {"posts": []}
    return json.loads(caminho.read_text(encoding="utf-8"))


def salvar(hist: dict, caminho: Path = ARQUIVO) -> None:
    hist["posts"] = hist["posts"][-MAX_ENTRADAS:]
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _cves(lista) -> set[str]:
    return {c.upper() for c in (lista or []) if re.fullmatch(r"CVE-\d{4}-\d{4,}", c, re.I)}


def verificar_duplicado(hist: dict, fonte_url: str, cves: list[str], agora: datetime | None = None) -> str | None:
    """Retorna o motivo se for duplicado, senão None."""
    agora = agora or datetime.now(timezone.utc)
    novo_id = id_para(fonte_url)
    novos_cves = _cves(cves)
    for p in hist["posts"]:
        if p.get("id") == novo_id:
            return f"esta fonte já foi usada em {p.get('data', '?')[:10]}"
        if novos_cves:
            data = datetime.fromisoformat(p["data"]) if p.get("data") else None
            if data and agora - data <= timedelta(days=JANELA_CVE_DIAS):
                repetidos = novos_cves & _cves(p.get("cves"))
                if repetidos:
                    return f"{', '.join(sorted(repetidos))} já foi tema em {p['data'][:10]}"
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
            f"- {p.get('data', '')[:10]} [{p.get('categoria', '?')}] {p.get('titulo', '')} "
            f"({', '.join(p.get('cves') or []) or 'sem CVE'}) — {p.get('fonte_url', '')}"
        )
    return "\n".join(linhas) or "(nenhum post ainda)"
