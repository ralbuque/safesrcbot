"""Gera o Access Token e o Access Token Secret de uma conta do X (fluxo OAuth 1.0a com PIN).

Use uma vez para cada conta que não é a dona do app no portal de desenvolvedor.
Rode no SEU computador, nunca no GitHub Actions:

    pip install tweepy
    python scripts/autorizar_conta.py

O script pede a API Key e a API Key Secret do app (sem mostrar na tela), abre um
link para você autorizar o app LOGADO NA CONTA DESEJADA e pede o PIN mostrado
pelo X. Depois imprime os dois tokens: cole-os nos secrets do Environment da
conta no GitHub e feche o terminal. Não salve os tokens em arquivo.
"""

import getpass
import os
import webbrowser


def main() -> None:
    import tweepy

    chave = os.environ.get("X_API_KEY") or getpass.getpass("API Key do app: ").strip()
    segredo = os.environ.get("X_API_SECRET") or getpass.getpass("API Key Secret do app: ").strip()

    auth = tweepy.OAuth1UserHandler(chave, segredo, callback="oob")
    url = auth.get_authorization_url()
    print("\n1) Num navegador LOGADO NA CONTA QUE VAI POSTAR, abra e autorize o app:\n")
    print(f"   {url}\n")
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass
    pin = input("2) Digite o PIN que o X mostrou: ").strip()
    token, token_secret = auth.get_access_token(pin)

    cliente = tweepy.Client(
        consumer_key=chave, consumer_secret=segredo, access_token=token, access_token_secret=token_secret
    )
    usuario = cliente.get_me(user_auth=True).data.username

    print(f"\nTokens da conta @{usuario}. Cadastre no Environment dessa conta no GitHub:\n")
    print(f"   X_ACCESS_TOKEN        = {token}")
    print(f"   X_ACCESS_TOKEN_SECRET = {token_secret}\n")
    print("Feche este terminal depois de copiar (não salve em arquivo).")


if __name__ == "__main__":
    main()
