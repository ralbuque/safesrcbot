"""Configuração de cada conta do X (pasta contas/<id>/).

Cada conta tem:
    contas/<id>/config.json     comportamento (horários, modo, link, sinais do X...)
    contas/<id>/prompt.md       linha editorial
    contas/<id>/historico.json  posts já feitos (gerado pelo bot)
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_CONTAS = RAIZ / "contas"
RE_ID = re.compile(r"^[a-z0-9_]{1,30}$")
MODOS = ("revisao", "automatico", "simulacao")


class ContaInvalida(ValueError):
    pass


@dataclass
class Conta:
    id: str
    usuario_x: str
    horarios: list[int]
    modo: str = "revisao"
    revisao_obrigatoria: bool = False
    link_no_post: bool = False
    categorias: list[str] = field(default_factory=list)
    idade_minima_anos: int | None = None
    janela_tema_dias: int = 7
    modelo: str | None = None
    sinais_x: dict = field(default_factory=dict)
    dir: Path = DIR_CONTAS

    @property
    def prompt(self) -> str:
        return (self.dir / "prompt.md").read_text(encoding="utf-8")

    @property
    def caminho_historico(self) -> Path:
        return self.dir / "historico.json"

    def modo_efetivo(self, override: str | None = None) -> str:
        """Modo desta execução. Contas com revisão obrigatória nunca publicam sozinhas."""
        modo = (override or "").strip().lower() or self.modo
        if modo not in MODOS:
            raise ContaInvalida(f"modo inválido: {modo!r}")
        if modo == "automatico" and self.revisao_obrigatoria:
            print(f"[{self.id}] revisão obrigatória: modo 'automatico' ignorado, usando 'revisao'")
            return "revisao"
        return modo


def validar_id(conta_id: str) -> str:
    conta_id = (conta_id or "").strip().lower()
    if not RE_ID.fullmatch(conta_id):
        raise ContaInvalida(f"id de conta inválido: {conta_id!r}")
    if not (DIR_CONTAS / conta_id / "config.json").is_file():
        raise ContaInvalida(f"conta não encontrada: {conta_id!r}")
    return conta_id


def carregar(conta_id: str, dir_contas: Path | None = None) -> Conta:
    base = dir_contas or DIR_CONTAS
    if dir_contas is None:
        conta_id = validar_id(conta_id)
    dados = json.loads((base / conta_id / "config.json").read_text(encoding="utf-8"))
    dados.pop("_comentario", None)
    horarios = sorted({int(h) for h in dados.get("horarios", [])})
    if any(h < 0 or h > 23 for h in horarios):
        raise ContaInvalida(f"[{conta_id}] horários devem estar entre 0 e 23")
    dados["horarios"] = horarios
    conta = Conta(id=conta_id, dir=base / conta_id, **dados)
    if conta.modo not in MODOS:
        raise ContaInvalida(f"[{conta_id}] modo inválido no config: {conta.modo!r}")
    return conta


def listar(dir_contas: Path | None = None) -> list[str]:
    base = dir_contas or DIR_CONTAS
    return sorted(p.parent.name for p in base.glob("*/config.json") if RE_ID.fullmatch(p.parent.name))


def contas_do_horario(hora_brt: int, dir_contas: Path | None = None) -> list[str]:
    return [c for c in listar(dir_contas) if hora_brt in carregar(c, dir_contas or None).horarios]
