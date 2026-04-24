from django.core.files.base import ContentFile

from .models import File
from .utils import extract_text_from_file


def import_yandex_file(user, filename, content, folder=None):
    file_obj = File(
        title=filename,
        uploaded_by=user,
        visibility="private",
        folder=folder,
        is_folder=False,
    )
    file_obj.file.save(filename, ContentFile(content), save=True)
    try:
        file_obj.extracted_text = extract_text_from_file(file_obj.file.path)
        file_obj.save(update_fields=["extracted_text"])
    except Exception:
        pass
    return file_obj
