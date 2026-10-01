from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bot import historico, issue
from bot.contagem import contar
from bot.gerador import gerar
from bot.validador import montar_texto_final, validar_aprovado, validar_gerado

URL = "https://github.com/advisories/GHSA-xxxx-yyyy-zzzz"


# ---------- contagem ----------

def test_contagem_url_vale_23():
    assert contar("abc https://exemplo.com/um/caminho/bem/comprido/mesmo") == 4 + 23


def test_contagem_acentos_valem_1_e_emoji_vale_2():
    assert contar("ação") == 4
    assert contar("🔒") == 2


# ---------- validador ----------

def test_validador_aceita_post_normal():
    assert validar_gerado("Falha crítica no pacote foo 1.2.3. Atualize para 1.2.4.", URL, True) == []


def test_validador_rejeita_url_mencao_hashtags_e_tamanho():
    erros = validar_gerado("veja https://x.com @fulano #a #b #c " + "x" * 300, URL, True)
    texto = " ".join(erros)
    assert "URL" in texto and "@" in texto and "hashtags" in texto and "caracteres" in texto


def test_validador_exige_fonte_https():
    assert any("https" in e for e in validar_gerado("ok", "http://inseguro.com", True))


def test_texto_final_com_e_sem_link():
    assert montar_texto_final(" oi ", URL, True) == f"oi\n\n{URL}"
    assert montar_texto_final(" oi ", URL, False) == "oi"


def test_validar_aprovado():
    assert validar_aprovado("ok") == []
    assert validar_aprovado("x" * 281)


# ---------- histórico ----------

def test_duplicado_por_url_normalizada():
    hist = {"posts": []}
    historico.registrar(hist, {"id": historico.id_para(URL + "/?utm_source=x"), "data": "2026-09-01T00:00:00+00:00"})
    assert historico.verificar_duplicado(hist, "https://www.github.com/advisories/GHSA-xxxx-yyyy-zzzz", [])


def test_duplicado_por_cve_dentro_da_janela():
    agora = datetime(2026, 9, 30, tzinfo=timezone.utc)
    hist = {"posts": [{"id": "a", "data": (agora - timedelta(days=2)).isoformat(), "cves": ["CVE-2026-1234"]}]}
    assert historico.verificar_duplicado(hist, "https://outra.com/x", ["cve-2026-1234"], agora)
    hist["posts"][0]["data"] = (agora - timedelta(days=30)).isoformat()
    assert historico.verificar_duplicado(hist, "https://outra.com/x", ["CVE-2026-1234"], agora) is None


def test_salvar_e_carregar(tmp_path):
    arq = tmp_path / "h.json"
    historico.salvar({"posts": [{"id": "1", "titulo": "ação"}]}, arq)
    assert historico.carregar(arq)["posts"][0]["titulo"] == "ação"


# ---------- issue ----------

def test_issue_ida_e_volta_com_edicao():
    meta = {"id": "abc", "fonte_url": URL, "cves": ["CVE-2026-1"], "titulo": "T --> estranho"}
    corpo = issue.montar_corpo(f"Texto original\n\n{URL}", meta)
    editado = corpo.replace("Texto original", "Texto editado por mim").replace("\n", "\r\n")
    texto, meta_lida = issue.ler_corpo(editado)
    assert texto == f"Texto editado por mim\n\n{URL}"
    assert meta_lida == meta


# ---------- gerador (cliente falso) ----------

class ClienteFalso:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []
        self.messages = self

    def create(self, **kw):
        self.chamadas.append(kw)
        return self.respostas.pop(0)


def _tool(id_, **entrada):
    return SimpleNamespace(type="tool_use", name="registrar_post", id=id_, input=entrada)


def _resp(stop, *blocos):
    return SimpleNamespace(stop_reason=stop, content=list(blocos))


def test_gerador_corrige_apos_erro_e_lida_com_pause_turn():
    ruim = _tool("t1", pular=False, texto="x" * 400, fonte_url=URL, titulo="T", categoria="vulnerabilidade")
    bom = _tool("t2", pular=False, texto="Post bom.", fonte_url=URL, titulo="T", categoria="vulnerabilidade")
    cli = ClienteFalso([_resp("pause_turn"), _resp("tool_use", ruim), _resp("tool_use", bom)])
    res = gerar(cli, "modelo", {"posts": []}, datetime(2026, 9, 30), True)
    assert not res.pular and res.dados["texto"] == "Post bom."
    ultima = cli.chamadas[-1]["messages"][-2]["content"][0]  # [-1] é a resposta final anexada depois
    assert ultima["type"] == "tool_result" and ultima["is_error"]


def test_gerador_pular():
    cli = ClienteFalso([_resp("tool_use", _tool("t1", pular=True, motivo_pular="nada novo"))])
    res = gerar(cli, "modelo", {"posts": []}, datetime(2026, 9, 30), True)
    assert res.pular and res.motivo == "nada novo"


def test_gerador_rejeita_tema_repetido():
    hist = {"posts": [{"id": historico.id_para(URL), "data": "2026-09-29T00:00:00+00:00"}]}
    rep = _tool("t1", pular=False, texto="ok", fonte_url=URL, titulo="T", categoria="vulnerabilidade")
    novo = _tool("t2", pular=False, texto="ok", fonte_url="https://nova.com/a", titulo="T2", categoria="pesquisa")
    cli = ClienteFalso([_resp("tool_use", rep), _resp("tool_use", novo)])
    res = gerar(cli, "modelo", hist, datetime(2026, 9, 30), True)
    assert res.dados["fonte_url"] == "https://nova.com/a"
