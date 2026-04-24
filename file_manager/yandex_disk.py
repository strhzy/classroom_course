import requests


YANDEX_OAUTH_URL = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"
YANDEX_DISK_API = "https://cloud-api.yandex.net/v1/disk/resources"


def get_authorize_url(client_id, redirect_uri, state):
    return (
        f"{YANDEX_OAUTH_URL}?response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}&state={state}"
    )


def exchange_code_for_token(client_id, client_secret, code):
    response = requests.post(
        YANDEX_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def list_files(access_token, limit=100):
    response = requests.get(
        YANDEX_DISK_API,
        params={"limit": limit},
        headers={"Authorization": f"OAuth {access_token}"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("_embedded", {}).get("items", [])


def get_download_url(access_token, path):
    response = requests.get(
        f"{YANDEX_DISK_API}/download",
        params={"path": path},
        headers={"Authorization": f"OAuth {access_token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("href")
