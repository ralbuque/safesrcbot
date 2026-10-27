# safesrcbot

Bot que gera posts para 4 contas do X (@ralbuque, que internamente é a conta `safesrc`, @ancapsu, @palacioassombra e @mundoemrevo) usando a API do Claude. Roda no GitHub Actions e é aprovado por issues.

Arquitetura, configuração de cada conta e decisões estão no [CLAUDE.md](CLAUDE.md).

## Setup

1. **API do Claude:** crie a chave em <https://console.anthropic.com> e adicione créditos.
2. **App do X** (o mesmo app para todas as contas), no portal de desenvolvedor:
   - deixe a permissão em **Read and write**;
   - copie a *API Key*, o *API Key Secret* e o *Bearer Token*.
3. **Tokens de cada conta:**
   - para a conta dona do app, gere pelo portal;
   - para as outras contas, rode localmente `pip install tweepy` e depois `python scripts/autorizar_conta.py`, autorizando com o navegador **logado na conta certa**.
4. **GitHub:**
   - em *Settings → Secrets and variables → Actions*, crie os secrets `ANTHROPIC_API_KEY`, `X_API_KEY`, `X_API_SECRET` e `X_BEARER_TOKEN`;
   - em *Settings → Environments*, crie um Environment por conta (`safesrc`, `ancapsu`, `palacioassombra`, `mundoemrevo`), cada um com `X_ACCESS_TOKEN` e `X_ACCESS_TOKEN_SECRET`;
   - em *Settings → Actions → General → Workflow permissions*, marque **Read and write**.
5. **Teste:** em *Actions → Gerar post → Run workflow*, informe a conta e o modo `simulacao`.

## Dia a dia

- **Rascunhos:** cada post vira uma issue `[@conta] ...`, com a label `conta:<id>` para você filtrar.
- **Aprovar:** edite o texto no bloco `~~~text`, se quiser, e adicione a label **`aprovado`**. Feche o menu de labels para a escolha ser salva.
- **Descartar:** feche a issue.
- **Contas políticas:** sempre passam por revisão. Confira o fato na fonte indicada na issue antes de aprovar.
