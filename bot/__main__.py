"""CLI do safesrcbot.

    python -m bot gerar               # pesquisa, escreve e publica/cria rascunho conforme MODO
    python -m bot publicar-rascunho   # publica a issue aprovada (lê ISSUE_BODY / ISSUE_NUMBER)

Variáveis de ambiente: veja CLAUDE.md.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import historico, issue
from .publicador import publicar, url_do_post
from .validador import montar_texto_final, validar_aprovado

SAIDA = Path("saida")
FUSO = ZoneInfo("America/Sao_Paulo")
MODOS = ("revisao", "automatico", "simulacao")


def _bool_env(nome: str, padrao: bool) -> bool:
    v = os.environ.get(nome, "").strip().lower()
    if not v:
        return padrao
    return v in ("1", "true", "sim", "yes", "on")


def _resumo_actions(texto: str) -> None:
    """Escreve no resumo do job do GitHub Actions (se houver)."""
    caminho = os.environ.get("GITHUB_STEP_SUMMARY")
    if caminho:
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(texto + "\n")


def cmd_gerar() -> int:
    import anthropic

    modo = os.environ.get("MODO", "revisao").strip().lower() or "revisao"
    if modo not in MODOS:
        print(f"MODO inválido: {modo!r}. Use um de {MODOS}.", file=sys.stderr)
        return 2
    modelo = os.environ.get("ANTHROPIC_MODEL", "").strip() or "claude-sonnet-5-5"
    incluir_link = _bool_env("INCLUIR_LINK", True)

    from .gerador import gerar

    hist = historico.carregar()
    agora_utc = datetime.now(timezone.utc)
    res = gerar(anthropic.Anthropic(), modelo, hist, agora_utc.astimezone(FUSO), incluir_link)

    if res.pular:
        print(f"Nenhum post agora: {res.motivo}")
        _resumo_actions(f"### Sem post nesta rodada\n\n{res.motivo}")
        return 0

    d = res.dados
    texto_final = montar_texto_final(d["texto"], d["fonte_url"], incluir_link)
    entrada = {
        "id": historico.id_para(d["fonte_url"]),
        "data": agora_utc.isoformat(timespec="seconds"),
        "categoria": d.get("categoria"),
        "titulo": d.get("titulo"),
        "fonte_url": d["fonte_url"],
        "cves": d.get("cves") or [],
        "texto": texto_final,
    }
    print(f"--- Post gerado (modo {modo}) ---\n{texto_final}\n---")
    _resumo_actions(f"### Post gerado (modo `{modo}`)\n\n```text\n{texto_final}\n```\n\nFonte: {d['fonte_url']}")

    if modo == "simulacao":
        return 0

    if modo == "automatico":
        post_id = publicar(texto_final)
        entrada.update(status="publicado", post_id=post_id)
        print(f"Publicado: {url_do_post(post_id)}")
        _resumo_actions(f"Publicado: {url_do_post(post_id)}")
    else:  # revisao
        meta = {k: d.get(k) for k in ("fonte_url", "fonte_nome", "titulo", "data_publicacao", "categoria", "cves", "justificativa")}
        meta["id"] = entrada["id"]
        SAIDA.mkdir(exist_ok=True)
        (SAIDA / "rascunho.md").write_text(issue.montar_corpo(texto_final, meta), encoding="utf-8")
        titulo = (d.get("titulo") or "post")[:90]
        (SAIDA / "titulo.txt").write_text(f"[rascunho] {titulo}", encoding="utf-8")
        entrada["status"] = "rascunho"

    historico.registrar(hist, entrada)
    historico.salvar(hist)
    return 0


def cmd_publicar_rascunho() -> int:
    corpo = os.environ.get("ISSUE_BODY", "")
    numero = os.environ.get("ISSUE_NUMBER", "")
    texto_final, meta = issue.ler_corpo(corpo)
    erros = validar_aprovado(texto_final)
    if erros:
        print("Não publicado: " + "; ".join(erros), file=sys.stderr)
        return 1

    post_id = publicar(texto_final)
    url = url_do_post(post_id)
    print(f"Publicado: {url}")

    hist = historico.carregar()
    entrada = {
        "id": meta.get("id") or historico.id_para(meta.get("fonte_url") or f"issue-{numero}"),
        "data": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "categoria": meta.get("categoria"),
        "titulo": meta.get("titulo"),
        "fonte_url": meta.get("fonte_url"),
        "cves": meta.get("cves") or [],
        "texto": texto_final,
        "status": "publicado",
        "post_id": post_id,
        "issue": int(numero) if numero.isdigit() else None,
    }
    historico.registrar(hist, entrada)
    historico.salvar(hist)

    SAIDA.mkdir(exist_ok=True)
    (SAIDA / "comentario.md").write_text(f"Publicado no X: {url}", encoding="utf-8")
    return 0


def main(argv: list[str]) -> int:
    comandos = {"gerar": cmd_gerar, "publicar-rascunho": cmd_publicar_rascunho}
    if len(argv) != 1 or argv[0] not in comandos:
        print(__doc__)
        return 2
    return comandos[argv[0]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
