# safesrcbot

Bot que publica 4 notícias por dia sobre segurança no desenvolvimento de software no X, em português. Ele pesquisa com a API do Claude e roda no GitHub Actions.

Detalhes de arquitetura, configuração e decisões estão no [CLAUDE.md](CLAUDE.md).

## Setup (uma vez)

1. **API do Claude:** crie uma chave em <https://console.anthropic.com> e adicione créditos.
2. **API do X:**
   1. No portal de desenvolvedor do X, crie um app (plano pay-per-use) e compre créditos.
   2. Em *User authentication settings*, defina a permissão como **Read and write**.
   3. Copie a *API Key* e o *API Key Secret*.
   4. Gere o *Access Token* e o *Access Token Secret* **logado na conta que vai postar**. Gere-os depois de mudar a permissão; tokens antigos ficam só com leitura.
3. **GitHub:** em *Settings → Secrets and variables → Actions*, crie os secrets `ANTHROPIC_API_KEY`, `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN` e `X_ACCESS_TOKEN_SECRET`.
4. **Permissões do Actions:** em *Settings → Actions → General → Workflow permissions*, marque **Read and write permissions**.
5. **Teste:** em *Actions → Gerar post → Run workflow*, escolha o modo `simulacao`. O post gerado aparece no resumo da execução e nada é publicado.

## Uso no dia a dia (modo revisão)

- 4 vezes por dia surge uma issue `[rascunho] ...`. Ela é atribuída a você, então o GitHub te notifica, inclusive pelo app no celular.
- Se quiser, edite o texto dentro do bloco `~~~text`. Para publicar, adicione a label **`aprovado`**. Para descartar, feche a issue.
- Quando os rascunhos estiverem bons, crie a variável `MODO=automatico` para o bot publicar sozinho.
