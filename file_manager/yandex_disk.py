import requests
from pathlib import PurePosixPath


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


def get_disk_info(access_token):
    response = requests.get(
        "https://cloud-api.yandex.net/v1/disk",
        headers={"Authorization": f"OAuth {access_token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_resource_info(access_token, path):
    response = requests.get(
        YANDEX_DISK_API,
        params={"path": path},
        headers={"Authorization": f"OAuth {access_token}"},
        timeout=20,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def resource_exists(access_token, path):
    return get_resource_info(access_token, path) is not None


def get_download_url(access_token, path):
    response = requests.get(
        f"{YANDEX_DISK_API}/download",
        params={"path": path},
        headers={"Authorization": f"OAuth {access_token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("href")


def get_upload_url(access_token, path, overwrite=True):
    response = requests.get(
        f"{YANDEX_DISK_API}/upload",
        params={"path": path, "overwrite": str(overwrite).lower()},
        headers={"Authorization": f"OAuth {access_token}"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("href")


def ensure_folder(access_token, path):
    response = requests.put(
        YANDEX_DISK_API,
        params={"path": path},
        headers={"Authorization": f"OAuth {access_token}"},
        timeout=20,
    )
    # 201 created, 409 already exists
    if response.status_code not in (201, 409):
        response.raise_for_status()


def ensure_parent_folders(access_token, file_path):
    path_str = str(file_path)
    if "/" not in path_str:
        return

    if path_str.startswith("app:/"):
        root = "app:"
        rootless_file = path_str.replace("app:/", "", 1)
    elif path_str.startswith("disk:/"):
        root = "disk:"
        rootless_file = path_str.replace("disk:/", "", 1)
    else:
        root = "disk:"
        rootless_file = path_str.lstrip("/")

    if "/" not in rootless_file:
        return

    parent_path = rootless_file.rsplit("/", 1)[0]
    parts = [part for part in PurePosixPath(parent_path).parts if part not in ("", ".")]
    current = root
    for part in parts:
        current = f"{current}/{part}"
        ensure_folder(access_token, current)


def upload_file_bytes(access_token, path, content, overwrite=True):
    ensure_parent_folders(access_token, path)
    upload_url = get_upload_url(access_token, path, overwrite=overwrite)
    if not upload_url:
        raise RuntimeError("Не удалось получить upload URL Яндекс.Диска")
    response = requests.put(upload_url, data=content, timeout=60)
    response.raise_for_status()


def delete_resource(access_token, path, permanently=False):
    response = requests.delete(
        YANDEX_DISK_API,
        params={"path": path, "permanently": str(permanently).lower()},
        headers={"Authorization": f"OAuth {access_token}"},
        timeout=20,
    )
    # 202 accepted or 204 no content are successful variants
    if response.status_code not in (202, 204):
        response.raise_for_status()
