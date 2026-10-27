"""CLI do bot multi-contas.

    python -m bot planejar                      # quais contas rodam agora (saída para o GitHub Actions)
    python -m bot gerar --conta ID              # pesquisa, escreve e publica/cria rascunho
    python -m bot ler-issue                     # descobre a conta de uma issue (lê ISSUE_BODY)
    python -m bot publicar-rascunho --conta ID  # publica a issue aprovada (lê ISSUE_BODY / ISSUE_NUMBER)

Variáveis de ambiente: veja CLAUDE.md.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import conta as contas
from . import historico, issue, sinais_x
from .publicador import publicar, url_do_post
from .validador import montar_texto_final, validar_aprovado

SAIDA = Path("saida")
FUSO = ZoneInfo("America/Sao_Paulo")
MODELO_PADRAO = "claude-sonnet-5-5"
CONTA_LEGADA = "safesrc"  # issues criadas antes do suporte a várias contas


def _saida_actions(nome: str, valor: str) -> None:
    caminho = os.environ.get("GITHUB_OUTPUT")
    if caminho:
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(f"{nome}={valor}\n")
    print(f"{nome}={valor}")


def _resumo_actions(texto: str) -> None:
    caminho = os.environ.get("GITHUB_STEP_SUMMARY")
    if caminho:
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(texto + "\n")


def cmd_planejar(_args) -> int:
    manual = os.environ.get("CONTA_MANUAL", "").strip().lower()
    if manual == "todas":
        lista = contas.listar()
    elif manual:
        lista = [contas.validar_id(manual)]
    else:
        hora = datetime.now(FUSO).hour
        lista = contas.contas_do_horario(hora)
        print(f"Hora em Brasília: {hora}h")
    _saida_actions("contas", json.dumps(lista))
    return 0


def cmd_gerar(args) -> int:
    import anthropic

    from .gerador import gerar

    conta = contas.carregar(args.conta)
    modo = conta.modo_efetivo(os.environ.get("MODO"))
    modelo = os.environ.get("ANTHROPIC_MODEL", "").strip() or conta.modelo or MODELO_PADRAO

    sinais = sinais_x.coletar(conta.sinais_x, os.environ.get("X_BEARER_TOKEN"))
    for aviso in sinais["avisos"]:
        print(f"[aviso] {aviso}")
    print(f"[{conta.id}] sinais do X: {len(sinais['tendencias'])} tendências, {len(sinais['posts'])} posts")

    hist = historico.carregar(conta.caminho_historico)
    agora_utc = datetime.now(timezone.utc)
    res = gerar(anthropic.Anthropic(), modelo, conta, hist, agora_utc.astimezone(FUSO), sinais_x.formatar(sinais))

    if res.pular:
        print(f"[{conta.id}] nenhum post agora: {res.motivo}")
        _resumo_actions(f"### @{conta.usuario_x}: sem post nesta rodada\n\n{res.motivo}")
        return 0

    d = res.dados
    texto_final = montar_texto_final(d["texto"], d["fonte_url"], conta.link_no_post)
    entrada = {
        "id": historico.id_para(d["fonte_url"]),
        "data": agora_utc.isoformat(timespec="seconds"),
        "categoria": d.get("categoria"),
        "tema_chave": historico.normalizar_tema(d.get("tema_chave", "")),
        "titulo": d.get("titulo"),
        "fonte_url": d["fonte_url"],
        "cves": d.get("cves") or [],
        "texto": texto_final,
    }
    if d.get("ano_evento"):
        entrada["ano_evento"] = d["ano_evento"]
    print(f"--- @{conta.usuario_x} (modo {modo}) ---\n{texto_final}\n---")
    _resumo_actions(
        f"### @{conta.usuario_x}: post gerado (modo `{modo}`)\n\n```text\n{texto_final}\n```\n\nFonte: {d['fonte_url']}"
    )

    if modo == "simulacao":
        return 0

    if modo == "automatico":
        post_id = publicar(texto_final, conta.usuario_x)
        entrada.update(status="publicado", post_id=post_id)
        print(f"Publicado: {url_do_post(post_id)}")
        _resumo_actions(f"Publicado: {url_do_post(post_id)}")
    else:  # revisao
        meta = {
            k: d.get(k)
            for k in ("fonte_url", "fonte_nome", "fontes_extras", "titulo", "data_publicacao", "categoria", "cves", "ano_evento", "justificativa")
        }
        meta.update(
            id=entrada["id"],
            conta=conta.id,
            usuario_x=conta.usuario_x,
            tema_chave=entrada["tema_chave"],
            revisao_obrigatoria=conta.revisao_obrigatoria,
        )
        SAIDA.mkdir(exist_ok=True)
        (SAIDA / "rascunho.md").write_text(issue.montar_corpo(texto_final, meta), encoding="utf-8")
        titulo = (d.get("titulo") or "post")[:80]
        (SAIDA / "titulo.txt").write_text(f"[@{conta.usuario_x}] {titulo}", encoding="utf-8")
        entrada["status"] = "rascunho"

    historico.registrar(hist, entrada)
    historico.salvar(hist, conta.caminho_historico)
    return 0


def cmd_ler_issue(_args) -> int:
    _texto, meta = issue.ler_corpo(os.environ.get("ISSUE_BODY", ""))
    _saida_actions("conta", contas.validar_id(meta.get("conta") or CONTA_LEGADA))
    return 0


def cmd_publicar_rascunho(args) -> int:
    conta = contas.carregar(args.conta)
    corpo = os.environ.get("ISSUE_BODY", "")
    numero = os.environ.get("ISSUE_NUMBER", "")
    texto_final, meta = issue.ler_corpo(corpo)
    if (meta.get("conta") or CONTA_LEGADA) != conta.id:
        print(f"A issue é da conta {meta.get('conta')!r}, não de {conta.id!r}.", file=sys.stderr)
        return 1
    erros = validar_aprovado(texto_final)
    if erros:
        print("Não publicado: " + "; ".join(erros), file=sys.stderr)
        return 1

    post_id = publicar(texto_final, conta.usuario_x)
    url = url_do_post(post_id)
    print(f"Publicado: {url}")

    hist = historico.carregar(conta.caminho_historico)
    entrada = {
        "id": meta.get("id") or historico.id_para(meta.get("fonte_url") or f"https://issue/{numero}"),
        "data": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "categoria": meta.get("categoria"),
        "tema_chave": meta.get("tema_chave"),
        "titulo": meta.get("titulo"),
        "fonte_url": meta.get("fonte_url"),
        "cves": meta.get("cves") or [],
        "texto": texto_final,
        "status": "publicado",
        "post_id": post_id,
        "issue": int(numero) if numero.isdigit() else None,
    }
    if meta.get("ano_evento"):
        entrada["ano_evento"] = meta["ano_evento"]
    historico.registrar(hist, entrada)
    historico.salvar(hist, conta.caminho_historico)

    SAIDA.mkdir(exist_ok=True)
    (SAIDA / "comentario.md").write_text(f"Publicado em @{conta.usuario_x}: {url}", encoding="utf-8")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m bot", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("planejar").set_defaults(func=cmd_planejar)
    p = sub.add_parser("gerar")
    p.add_argument("--conta", required=True)
    p.set_defaults(func=cmd_gerar)
    sub.add_parser("ler-issue").set_defaults(func=cmd_ler_issue)
    p = sub.add_parser("publicar-rascunho")
    p.add_argument("--conta", required=True)
    p.set_defaults(func=cmd_publicar_rascunho)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
