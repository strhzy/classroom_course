from pathlib import PurePosixPath

from .models import ExternalStorageConnection, File
from .yandex_disk import upload_file_bytes


def import_yandex_file(user, filename, content, folder=None):
    connection = ExternalStorageConnection.objects.filter(user=user, provider="yandex_disk").first()
    if not connection:
        raise RuntimeError("Yandex Disk is not connected")

    remote_path = f"app:/Classroom/{user.id}/{PurePosixPath(filename).name}"
    upload_file_bytes(connection.access_token, remote_path, content, overwrite=True)

    file_obj = File(
        title=filename,
        uploaded_by=user,
        visibility="private",
        folder=folder,
        is_folder=False,
        storage_provider="yandex_disk",
        yandex_path=remote_path,
        file_size=len(content),
    )
    file_obj.save()
    return file_obj
