from django.shortcuts import render ,redirect ,get_object_or_404 
from django.urls import reverse
from django.contrib.auth.decorators import login_required 
from django.contrib import messages 
from django.http import HttpResponse ,Http404 ,JsonResponse 
from django.core.files.base import ContentFile
from django.core.exceptions import PermissionDenied ,ValidationError 
from django.db.models import Q, Count, Exists, OuterRef
from django.core.paginator import Paginator 
from django.contrib.auth.models import User
from . models import File ,Tag ,FileComment ,FileVersion ,FileActivity ,UserStorageQuota 
from . forms import FileEditForm ,FileVersionForm ,FileCommentForm ,TagForm ,FileSearchForm, BulkPermissionForm 
from . utils import extract_text_from_file ,generate_preview ,search_files ,get_user_storage_usage 
from . office_pdf import (
    EXTENSIONS_LIBREOFFICE_TO_PDF,
    convert_office_file_to_pdf_bytes,
    is_convertapi_configured,
    is_libreoffice_available,
    is_office_pdf_conversion_available,
)
from . clamav import flash_scan_followup ,scan_upload_bytes 
import logging 
import os 
import requests
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from web_messages import flash_form_errors
from .models import ExternalStorageConnection
from .wordfilter import find_banned_match

logger = logging.getLogger(__name__)
from .models import SharedWorkspace
from .yandex_disk import (
    get_authorize_url,
    exchange_code_for_token,
    list_files,
    get_disk_info,
    resource_exists,
    get_download_url,
    upload_file_bytes,
    delete_resource,
)
from .import_pipeline import import_yandex_file
import zipfile
import io
import json
import tempfile
import hashlib
import difflib
import mimetypes
import xml.etree.ElementTree as ET
from pathlib import Path
from pathlib import PurePosixPath


def get_yandex_connection(user, autocreate_from_social=False):
    connection = ExternalStorageConnection.objects.filter(
        user=user, provider="yandex_disk"
    ).first()
    if connection or not autocreate_from_social:
        return connection

    try:
        from allauth.socialaccount.models import SocialToken
    except Exception:
        return None

    social_token = (
        SocialToken.objects.filter(account__user=user, account__provider="yandex")
        .order_by("-id")
        .first()
    )
    if not social_token or not social_token.token:
        return None

    expires_at = social_token.expires_at if social_token.expires_at else timezone.now() + timezone.timedelta(days=30)
    connection, _ = ExternalStorageConnection.objects.update_or_create(
        user=user,
        provider="yandex_disk",
        defaults={
            "access_token": social_token.token,
            "refresh_token": social_token.token_secret or "",
            "expires_at": expires_at,
        },
    )
    return connection


def _user_role(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "role", "")


def is_admin_user(user):
    role = _user_role(user)
    return user.is_superuser or user.is_staff or role in {"admin", "staff"}


def is_teacher_user(user):
    return _user_role(user) == "teacher"


def can_manage_reference_data(user):
    return is_admin_user(user) or is_teacher_user(user)


def can_edit_file_object(user, file_obj):
    """Редактирование метаданных, доступа и тегов (владелец файла или админ)."""
    return file_obj.uploaded_by_id == user.id or is_admin_user(user)


def is_file_workspace_collaborator(user, file_obj):
    """Участник workspace, в котором состоит этот файл."""
    if not getattr(user, "is_authenticated", False):
        return False
    return SharedWorkspace.objects.filter(participants=user, files=file_obj).exists()


def can_upload_file_version(user, file_obj):
    """
    Загрузка новой версии (замена файла): владелец/админ или участник общего workspace с этим файлом.
    Нужен доступ к просмотру файла.
    """
    if not file_obj.can_access(user):
        return False
    if can_edit_file_object(user, file_obj):
        return True
    return is_file_workspace_collaborator(user, file_obj)


def can_delete_file_object(user, file_obj):
    return file_obj.uploaded_by_id == user.id or is_admin_user(user)


def get_share_users_queryset(exclude_user_id=None):
    qs = User.objects.filter(is_active=True).order_by("username").select_related("profile")
    if exclude_user_id:
        qs = qs.exclude(pk=exclude_user_id)
    return qs


def get_editable_files_queryset(user):
    if is_admin_user(user):
        return File.objects.filter(is_folder=False).order_by("-uploaded_at")
    return File.objects.filter(uploaded_by=user, is_folder=False).order_by("-uploaded_at")


def build_unique_title(user, original_name):
    base_name = (original_name or "").strip() or "file"
    stem, ext = os.path.splitext(base_name)
    stem = stem or "file"
    ext = ext or ""
    candidate = f"{stem}{ext}"
    counter = 1
    while File.objects.filter(uploaded_by=user, title=candidate).exists():
        candidate = f"{stem}{counter}{ext}"
        counter += 1
    return candidate


def sync_deleted_yandex_files_for_user(user):
    connection = get_yandex_connection(user, autocreate_from_social=True)
    if not connection:
        return
    yandex_files = File.objects.filter(
        uploaded_by=user,
        storage_provider="yandex_disk",
    ).exclude(yandex_path="")
    for file_obj in yandex_files:
        try:
            exists = resource_exists(connection.access_token, file_obj.yandex_path)
        except Exception:
            continue
        if not exists:
            file_obj.delete()


def extract_text_from_uploaded_content(file_name, content):
    if not content:
        return ""
    suffix = Path(file_name).suffix or ".tmp"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        return extract_text_from_file(tmp_path)
    except Exception:
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def build_structured_snapshot(file_name, content):
    ext = (Path(file_name).suffix or "").lower().lstrip(".")
    snapshot = {
        "schema_version": "v1",
        "ext": ext,
        "size_bytes": len(content or b""),
    }
    if not content:
        snapshot["kind"] = "empty"
        return snapshot

    text_like = {"txt", "md", "csv", "json", "xml", "yml", "yaml", "log"}
    if ext in text_like:
        text = (content[:500_000]).decode("utf-8", errors="replace")
        lines = text.splitlines()
        snapshot.update(
            {
                "kind": "text_lines",
                "line_count": len(lines),
                "preview_lines": lines[:500],
                "truncated": len(content) > 500_000 or len(lines) > 500,
            }
        )
        return snapshot

    if ext == "docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                xml_bytes = zf.read("word/document.xml")
            root = ET.fromstring(xml_bytes)
            paragraphs = []
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            for p in root.findall(".//w:p", ns):
                texts = [t.text or "" for t in p.findall(".//w:t", ns)]
                text = "".join(texts).strip()
                if text:
                    paragraphs.append({"text": text})
                if len(paragraphs) >= 500:
                    break
            snapshot.update(
                {
                    "kind": "docx_paragraphs",
                    "paragraph_count": len(paragraphs),
                    "paragraphs": paragraphs,
                }
            )
            return snapshot
        except Exception as exc:
            snapshot.update({"kind": "docx_parse_error", "error": str(exc)})
            return snapshot

    if ext == "xlsx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                sheet_files = sorted(
                    [name for name in zf.namelist() if name.startswith("xl/worksheets/sheet")]
                )
                sheets = []
                ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                for sheet_file in sheet_files[:20]:
                    xml_bytes = zf.read(sheet_file)
                    root = ET.fromstring(xml_bytes)
                    rows = root.findall(".//x:row", ns)
                    cells = root.findall(".//x:c", ns)
                    sheets.append(
                        {
                            "sheet_file": sheet_file,
                            "row_count": len(rows),
                            "cell_count": len(cells),
                        }
                    )
            snapshot.update({"kind": "xlsx_sheets", "sheets": sheets, "sheet_count": len(sheets)})
            return snapshot
        except Exception as exc:
            snapshot.update({"kind": "xlsx_parse_error", "error": str(exc)})
            return snapshot

    mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    snapshot.update({"kind": "binary", "mime_type": mime_type})
    return snapshot


def _store_revision_blob(file_obj, uploaded_by, content, original_name, version_number):
    sha256 = hashlib.sha256(content).hexdigest()
    safe_name = PurePosixPath(original_name).name or f"v{version_number}.bin"
    revision_file_name = f"v{version_number}_{sha256[:10]}_{safe_name}"

    if file_obj.storage_provider == "yandex_disk":
        connection = get_yandex_connection(file_obj.uploaded_by, autocreate_from_social=True)
        if not connection:
            raise ValidationError("Не найдено подключение Яндекс.Диска владельца файла")
        yandex_path = f"disk:/revisions/{file_obj.id}/{revision_file_name}"
        upload_file_bytes(connection.access_token, yandex_path, content, overwrite=False)
        return {
            "has_blob": True,
            "blob_storage_provider": "yandex_disk",
            "blob_storage_path": yandex_path,
            "blob_size": len(content),
            "blob_sha256": sha256,
            "version_file_name": "",
        }

    storage_name = default_storage.save(
        f"file_versions/{file_obj.id}/{revision_file_name}",
        ContentFile(content),
    )
    return {
        "has_blob": True,
        "blob_storage_provider": "local",
        "blob_storage_path": storage_name,
        "blob_size": len(content),
        "blob_sha256": sha256,
        "version_file_name": storage_name,
    }


def _read_revision_blob_bytes(version_obj):
    if version_obj.blob_storage_provider == "yandex_disk" and version_obj.blob_storage_path:
        connection = get_yandex_connection(version_obj.file.uploaded_by, autocreate_from_social=True)
        if not connection:
            raise ValidationError("Нет подключения Яндекс.Диска владельца файла")
        download_url = get_download_url(connection.access_token, version_obj.blob_storage_path)
        response = requests.get(download_url, timeout=120)
        response.raise_for_status()
        return response.content
    if version_obj.blob_storage_provider == "local" and version_obj.blob_storage_path:
        if default_storage.exists(version_obj.blob_storage_path):
            with default_storage.open(version_obj.blob_storage_path, "rb") as fh:
                return fh.read()
    if version_obj.version_file and default_storage.exists(version_obj.version_file.name):
        with default_storage.open(version_obj.version_file.name, "rb") as fh:
            return fh.read()
    raise ValidationError("Для этой версии нет сохранённого blob")


def create_user_uploaded_file(user, uploaded_file):
    """
    Сохраняет загруженный файл так же, как страница загрузки в файловом менеджере
    (Яндекс.Диск при успешном API, иначе локально на сервере).
    Перед сохранением — проверка ClamAV (если включена) и словаря «запрещённых» слов
    (static/file_manager/words.txt) по извлечённому тексту.

    Returns:
        (File, None, scan_info) при успехе,
        (None, str, scan_info) при ошибке; scan_info — результат clamav.scan_upload_bytes.
    """
    storage_quota = get_user_storage_usage(user)
    file_size = uploaded_file.size
    file_name = PurePosixPath(uploaded_file.name).name
    if not storage_quota.has_enough_space(file_size):
        logger.warning(
            "file upload rejected (quota) user_id=%s filename=%r size_bytes=%s",
            user.id,
            file_name,
            file_size,
        )
        return None, (
            f"Недостаточно места в хранилище. Доступно: {storage_quota.get_quota_display()}"
        ), {"performed": False, "clean": None, "skipped": "quota"}
    unique_title = build_unique_title(user, file_name)
    uploaded_content = uploaded_file.read()
    scan = scan_upload_bytes(
        uploaded_content,
        user_id=user.id,
        filename=file_name,
    )

    if scan.get("performed") and scan.get("clean") is False:
        threat = scan.get("threat") or "неизвестная угроза"
        return None, (
            f"Файл не загружен: антивирус ClamAV обнаружил угрозу «{threat}». "
            "Выберите другой файл или проверьте данные на компьютере."
        ), scan

    if getattr(settings, "CLAMAV_ENABLED", False) and not scan.get("performed"):
        if not getattr(settings, "CLAMAV_FAIL_OPEN", True):
            err = scan.get("error") or "проверка не выполнена"
            logger.warning(
                "file upload rejected (clamav required, unavailable) user_id=%s filename=%r err=%s",
                user.id,
                file_name,
                err,
            )
            return None, (
                f"Загрузка запрещена политикой безопасности: требуется ClamAV, "
                f"но антивирус недоступен ({err})."
            ), scan

    extracted_text = extract_text_from_uploaded_content(unique_title, uploaded_content)
    banned_match = find_banned_match(extracted_text)
    if banned_match:
        logger.warning(
            "file upload rejected (wordfilter) user_id=%s filename=%r matched=%r",
            user.id,
            file_name,
            banned_match,
        )
        return None, (
            "Файл не принят: в содержимом обнаружен запрещённый фрагмент по словарю модерации. "
            "Загрузите другой файл."
        ), scan

    yandex_connection = get_yandex_connection(user, autocreate_from_social=True)
    file_obj = None

    if yandex_connection:
        yandex_path = f"disk:/{unique_title}"
        try:
            upload_file_bytes(yandex_connection.access_token, yandex_path, uploaded_content, overwrite=True)
            file_obj = File.objects.create(
                title=unique_title,
                description="",
                uploaded_by=user,
                visibility="private",
                importance="main",
                is_folder=False,
                storage_provider="yandex_disk",
                yandex_path=yandex_path,
                file_size=file_size,
                extracted_text=extracted_text,
            )
        except Exception:
            file_obj = None

    if not file_obj:
        try:
            file_obj = File(
                title=unique_title,
                description="",
                uploaded_by=user,
                visibility="private",
                importance="main",
                is_folder=False,
                storage_provider="local",
                yandex_path="",
                file_size=file_size,
                extracted_text=extracted_text,
            )
            file_obj.file.save(unique_title, ContentFile(uploaded_content), save=True)
        except Exception as exc:
            logger.error(
                "file upload save failed user_id=%s title=%r",
                user.id,
                unique_title,
                exc_info=exc,
            )
            return None, f"Не удалось сохранить файл: {exc}", scan

    try:
        FileActivity.log_activity(
            file=file_obj,
            user=user,
            activity_type="upload",
            description=f"File uploaded: {file_obj.title}",
        )
    except Exception:
        pass

    # Автосоздание первой ревизии (v1) сразу при загрузке файла.
    try:
        if not FileVersion.objects.filter(file=file_obj, version_number=1).exists():
            structured_snapshot = build_structured_snapshot(unique_title, uploaded_content)
            blob_info = _store_revision_blob(
                file_obj=file_obj,
                uploaded_by=user,
                content=uploaded_content,
                original_name=unique_title,
                version_number=1,
            )
            FileVersion.objects.create(
                file=file_obj,
                changed_by=user,
                version_number=1,
                change_description="Initial upload",
                snapshot_title=file_obj.title,
                snapshot_size=file_obj.file_size,
                snapshot_storage_provider=file_obj.storage_provider,
                snapshot_storage_path=file_obj.yandex_path if file_obj.storage_provider == "yandex_disk" else (file_obj.file.name if file_obj.file else ""),
                has_blob=blob_info["has_blob"],
                blob_storage_provider=blob_info["blob_storage_provider"],
                blob_storage_path=blob_info["blob_storage_path"],
                blob_size=blob_info["blob_size"],
                blob_sha256=blob_info["blob_sha256"],
                extracted_text_snapshot=extracted_text or "",
                structured_snapshot=structured_snapshot,
                structured_schema_version=structured_snapshot.get("schema_version", "v1"),
                version_file=blob_info["version_file_name"] or None,
            )
    except Exception:
        logger.exception("failed to create initial file version file_id=%s", getattr(file_obj, "id", None))

    try:
        storage_quota.update_usage()
    except Exception:
        pass

    logger.info(
        "file upload stored file_id=%s title=%r storage_provider=%s user_id=%s size_bytes=%s "
        "clamav_performed=%s clamav_clean=%s clamav_skipped=%s",
        file_obj.id,
        file_obj.title,
        file_obj.storage_provider,
        user.id,
        file_size,
        scan.get("performed"),
        scan.get("clean"),
        scan.get("skipped"),
    )

    return file_obj, None, scan


@login_required 
def file_list(request ):
    sync_deleted_yandex_files_for_user(request.user)
    storage_quota =get_user_storage_usage(request.user )
    yandex_connection = get_yandex_connection(request.user, autocreate_from_social=True)

    raw_tag_ids = request.GET.getlist("tags")
    tag_ids = []
    for x in raw_tag_ids:
        try:
            tag_ids.append(int(x))
        except (TypeError, ValueError):
            continue
    tag_objects = list(Tag.objects.filter(id__in=tag_ids)) if tag_ids else None

    if is_admin_user(request.user):
        files = File.objects.filter(is_folder=False)
        query = request.GET.get('query')
        if query:
            files = files.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(extracted_text__icontains=query)
            )
        if request.GET.get('file_type'):
            files = files.filter(file_type=request.GET.get('file_type'))
        if request.GET.get('date_from'):
            files = files.filter(uploaded_at__date__gte=request.GET.get('date_from'))
        if request.GET.get('date_to'):
            files = files.filter(uploaded_at__date__lte=request.GET.get('date_to'))
        if tag_objects:
            for t in tag_objects:
                files = files.filter(tags=t)
    else:
        files = search_files(
            query=request.GET.get('query'),
            user=request.user,
            file_types=[request.GET.get('file_type')] if request.GET.get('file_type') else None,
            tags=tag_objects,
            date_from=request.GET.get('date_from'),
            date_to=request.GET.get('date_to'),
        )
    if request.GET.get('favorites_only'):
        files = files.filter(favorite=request.user)

    favorite_through = File.favorite.through
    files = (
        files.annotate(
            is_favorite_for_user=Exists(
                favorite_through.objects.filter(
                    file_id=OuterRef("pk"),
                    user_id=request.user.id,
                )
            )
        )
        .prefetch_related("tags")
    )
    sort_by = request.GET.get("sort", "-uploaded_at")
    files = files.order_by(sort_by)

    paginator =Paginator(files ,20 )
    page_number =request.GET.get('page')
    page_obj =paginator.get_page(page_number )
    for file_obj in page_obj:
        file_obj.can_edit = can_edit_file_object(request.user, file_obj)
        file_obj.can_delete = can_delete_file_object(request.user, file_obj)

    total_files =files.count()
    total_size =sum(f.file_size for f in files )

    filter_params = request.GET.copy()
    if 'page' in filter_params:
        del filter_params['page']
    filter_querystring = filter_params.urlencode()

    context ={
    'page_obj':page_obj ,
    'search_form':FileSearchForm(request.GET ),
    'total_files':total_files ,
    'total_size':total_size ,
    'tags':Tag.objects.all(),
    'selected_tag_ids': tag_ids,
    'filter_querystring': filter_querystring,
    'storage_quota':storage_quota ,
    'yandex_connected': bool(yandex_connection),
    'can_manage_reference_data': can_manage_reference_data(request.user),
    'is_admin_user': is_admin_user(request.user),
    }

    return render(request ,'file_manager/file_list.html',context )

@login_required 
def file_upload(request ):
    if request.method != 'POST':
        return redirect('file_manager:file_list')

    def respond_redirect(res):
        if request.headers.get("X-Upload-Json-Redirect") != "1":
            return res
        return JsonResponse({"redirect": res.url})

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        messages.error(request, "Файл не выбран — выберите файл и попробуйте снова.")
        return respond_redirect(redirect('file_manager:file_list'))

    file_obj, err, scan = create_user_uploaded_file(request.user, uploaded_file)
    if err:
        messages.error(request, err)
        return respond_redirect(redirect('file_manager:file_list'))

    if file_obj.storage_provider == "yandex_disk":
        messages.success(request, "Файл успешно загружен на Яндекс.Диск.")
    else:
        messages.success(request, "Файл успешно загружен в локальное хранилище.")
    flash_scan_followup(request, scan)

    return respond_redirect(redirect("file_manager:file_list"))

@login_required
def file_detail(request ,file_id ):
    file_obj = get_object_or_404(
        File.objects.prefetch_related("tags"),
        id=file_id,
    )

    if not file_obj.can_access(request.user ):
        raise PermissionDenied 

    comments =file_obj.comments.filter(parent =None )
    versions = file_obj.versions.select_related("changed_by").order_by("-version_number")

    comment_form =FileCommentForm()

    if request.user !=file_obj.uploaded_by :
        FileActivity.log_activity(
        file =file_obj ,
        user =request.user ,
        activity_type ='view',
        description =f'File viewed: {file_obj.title }'
        )

    context ={
    'file':file_obj ,
    'comments':comments ,
    'comment_form':comment_form ,
    'can_edit':can_edit_file_object(request.user, file_obj),
    'can_delete':can_delete_file_object(request.user, file_obj),
    'can_upload_version': can_upload_file_version(request.user, file_obj),
    'is_favorite':file_obj.is_favorite(request.user ),
    'shared_workspaces': SharedWorkspace.objects.filter(participants=request.user).order_by("title"),
    'file_workspaces': SharedWorkspace.objects.filter(files=file_obj, participants=request.user).order_by("title"),
    'versions': versions,
    }

    return render(request ,'file_manager/file_detail.html',context )

@login_required 
def file_download(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_access(request.user ):
        raise PermissionDenied 

    if file_obj.storage_provider == "yandex_disk" and file_obj.yandex_path:
        connection = get_yandex_connection(file_obj.uploaded_by, autocreate_from_social=True)
        if not connection:
            raise Http404
        download_url = get_download_url(connection.access_token, file_obj.yandex_path)
        response = requests.get(download_url, timeout=60)
        response.raise_for_status()
        FileActivity.log_activity(
            file=file_obj,
            user=request.user,
            activity_type='download',
            description=f'File downloaded: {file_obj.title }',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        file_obj.increment_download()
        output = HttpResponse(response.content, content_type="application/octet-stream")
        output['Content-Disposition'] = f'attachment; filename="{file_obj.title}"'
        return output

    if file_obj.file and os.path.exists(file_obj.file.path):
        FileActivity.log_activity(file=file_obj, user=request.user, activity_type='download', description=f'File downloaded: {file_obj.title }', ip_address=request.META.get('REMOTE_ADDR'))
        file_obj.increment_download()
        with open(file_obj.file.path ,'rb')as fh :
            response =HttpResponse(fh.read(),content_type ="application/octet-stream")
            response ['Content-Disposition']=f'attachment; filename="{os.path.basename(file_obj.file.path)}"'
            return response
    raise Http404

@login_required 
def file_preview(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_access(request.user ):
        raise PermissionDenied 

    file_ext = (file_obj.get_extension() or "").lower()
    content_type = 'application/octet-stream'
    if file_ext in ['txt', 'csv', 'log', 'md', 'json', 'xml', 'yaml', 'yml']:
        content_type = 'text/plain; charset=utf-8'
    elif file_ext in ['pdf']:
        content_type ='application/pdf'
    elif file_ext in ['jpg','jpeg']:
        content_type ='image/jpeg'
    elif file_ext in ['png']:
        content_type ='image/png'
    elif file_ext in ['gif']:
        content_type = 'image/gif'
    elif file_ext in ['webp']:
        content_type = 'image/webp'
    elif file_ext in ['svg']:
        content_type = 'image/svg+xml'
    elif file_ext in ['mp4']:
        content_type = 'video/mp4'
    elif file_ext in ['webm']:
        content_type = 'video/webm'
    elif file_ext in ['mp3']:
        content_type = 'audio/mpeg'
    elif file_ext in ['wav']:
        content_type = 'audio/wav'
    elif file_ext in ['ogg']:
        content_type = 'audio/ogg'

    if file_obj.storage_provider == "yandex_disk" and file_obj.yandex_path:
        connection = get_yandex_connection(file_obj.uploaded_by, autocreate_from_social=True)
        if not connection:
            raise Http404
        download_url = get_download_url(connection.access_token, file_obj.yandex_path)
        resp = requests.get(download_url, timeout=60)
        resp.raise_for_status()
        response = HttpResponse(resp.content, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{file_obj.title}"'
        return response

    if file_obj.file and os.path.exists(file_obj.file.path):
        with open(file_obj.file.path ,'rb')as fh :
            response =HttpResponse(fh.read(),content_type =content_type )
            response ['Content-Disposition']=f'inline; filename="{os.path.basename(file_obj.file.path )}"'
            return response
    raise Http404


@login_required
def office_pdf_preview(request, file_id):
    """Отдаёт PDF из Office: ConvertAPI (если есть ключ) и/или LibreOffice."""
    file_obj = get_object_or_404(File, id=file_id)
    if not file_obj.can_access(request.user):
        raise PermissionDenied
    ext = (file_obj.get_extension() or "").lower()
    if ext not in EXTENSIONS_LIBREOFFICE_TO_PDF:
        raise Http404
    if not is_office_pdf_conversion_available():
        return HttpResponse(
            "Конвертация Office→PDF недоступна: задайте CONVERTAPI_SECRET (ConvertAPI) "
            "или установите LibreOffice / LIBREOFFICE_PATH.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    path, cleanup = _resolve_path_for_viewing(file_obj)
    if not path:
        raise Http404
    try:
        try:
            pdf_bytes = convert_office_file_to_pdf_bytes(path)
        except Exception as exc:
            return HttpResponse(
                f"Не удалось сконвертировать в PDF: {exc}",
                status=502,
                content_type="text/plain; charset=utf-8",
            )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="preview.pdf"'
        return response
    finally:
        if cleanup:
            try:
                os.unlink(path)
            except OSError:
                pass


def _resolve_path_for_viewing(file_obj):
    """
    Возвращает (абсолютный_путь, удалить_после_использования).
    Для Яндекс.Диска скачивает во временный файл.
    """
    if file_obj.is_folder:
        return None, False
    if file_obj.storage_provider == "yandex_disk" and file_obj.yandex_path:
        connection = get_yandex_connection(file_obj.uploaded_by, autocreate_from_social=True)
        if not connection:
            return None, False
        download_url = get_download_url(connection.access_token, file_obj.yandex_path)
        try:
            resp = requests.get(download_url, timeout=120)
        except requests.RequestException:
            return None, False
        if resp.status_code != 200:
            return None, False
        ext = (file_obj.get_extension() or "bin").lower()
        suffix = f".{ext}" if ext else ".bin"
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        with open(temp_path, "wb") as f:
            f.write(resp.content)
        return temp_path, True
    if file_obj.file and file_obj.file.path and os.path.exists(file_obj.file.path):
        return file_obj.file.path, False
    return None, False


_MAX_VIEWER_TEXT = 500_000


@login_required
def file_viewer(request, file_id):
    """
    Просмотр: Office как PDF через ConvertAPI и/или LibreOffice;
    без конвертера — docx (docx-preview) и xlsx (SheetJS) в браузере, прочий Office — текст на сервере.
    """
    file_obj = get_object_or_404(File, id=file_id)
    if not file_obj.can_access(request.user):
        raise PermissionDenied
    if file_obj.is_folder:
        messages.error(request, "Папки нельзя открыть в просмотрщике.")
        return redirect("file_manager:file_list")

    ext = (file_obj.get_extension() or "").lower()
    download_url = reverse("file_manager:file_download", args=[file_obj.id])
    detail_url = reverse("file_manager:file_detail", args=[file_obj.id])
    preview_path = reverse("file_manager:file_preview", args=[file_obj.id])
    office_pdf_path = reverse("file_manager:office_pdf_preview", args=[file_obj.id])
    pdf_conversion_ready = is_office_pdf_conversion_available()

    if request.user != file_obj.uploaded_by:
        FileActivity.log_activity(
            file=file_obj,
            user=request.user,
            activity_type="view",
            description=f"File opened in viewer: {file_obj.title}",
        )

    EMBED_IMAGE = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"}
    EMBED_VIDEO = {"mp4", "webm", "ogv"}
    EMBED_AUDIO = {"mp3", "wav", "ogg", "m4a", "flac", "opus"}
    TEXT_EXTS = {
        "txt", "csv", "tsv", "log", "md", "json", "xml", "yaml", "yml", "toml", "ini", "cfg", "env",
        "py", "js", "mjs", "ts", "tsx", "jsx", "css", "scss", "sass", "less", "html", "htm", "vue", "svelte",
        "sh", "bash", "zsh", "bat", "ps1", "sql", "r", "rb", "go", "rs", "java", "c", "h", "cpp", "hpp", "cc",
        "cs", "php", "kt", "swift", "pl", "dockerfile", "gitignore", "lock", "gitattributes", "srt", "vtt",
    }
    OFFICE_TEXT_EXTRACT_EXTS = {"doc", "xls", "ppt", "pptx"}
    ARCHIVE_EXTS = {"zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "xz", "iso"}

    context = {
        "file": file_obj,
        "viewer_mode": "fallback",
        "download_url": download_url,
        "detail_url": detail_url,
        "text_content": "",
        "text_truncated": False,
        "viewer_note": "",
        "viewer_config": None,
        "viewer_hint": "",
        "libreoffice_available": is_libreoffice_available(),
        "convertapi_configured": is_convertapi_configured(),
        "office_pdf_conversion_available": pdf_conversion_ready,
    }

    if ext == "pdf":
        context["viewer_mode"] = "js_pdf"
        context["viewer_config"] = {"previewUrl": preview_path, "ext": ext, "mode": "js_pdf"}
    elif ext in EXTENSIONS_LIBREOFFICE_TO_PDF and pdf_conversion_ready:
        context["viewer_mode"] = "js_pdf"
        context["viewer_config"] = {
            "previewUrl": office_pdf_path,
            "ext": "pdf",
            "mode": "js_pdf",
        }
        context["viewer_hint"] = (
            "Вид как у PDF: конвертация на сервере (сначала ConvertAPI при наличии CONVERTAPI_SECRET, "
            "иначе LibreOffice)."
        )
    elif ext == "docx":
        context["viewer_mode"] = "js_docx"
        context["viewer_config"] = {"previewUrl": preview_path, "ext": ext, "mode": "js_docx"}
        context["viewer_hint"] = (
            "Без ConvertAPI/LibreOffice — просмотр бинарного .docx в браузере (docx-preview: стили и вёрстка ближе к Word). "
            "Для постраничного PDF как при печати задайте CONVERTAPI_SECRET или LibreOffice."
        )
    elif ext == "xlsx":
        context["viewer_mode"] = "js_xlsx"
        context["viewer_config"] = {"previewUrl": preview_path, "ext": ext, "mode": "js_xlsx"}
        context["viewer_hint"] = (
            "Без ConvertAPI/LibreOffice таблица показывается в браузере (SheetJS). "
            "Для вида как PDF — CONVERTAPI_SECRET или LibreOffice."
        )
    elif ext in TEXT_EXTS:
        context["viewer_mode"] = "js_text"
        context["viewer_config"] = {"previewUrl": preview_path, "ext": ext, "mode": "js_text"}
    elif ext in EMBED_IMAGE:
        context["viewer_mode"] = "embed_image"
    elif ext in EMBED_VIDEO:
        context["viewer_mode"] = "embed_video"
    elif ext in EMBED_AUDIO:
        context["viewer_mode"] = "embed_audio"
    elif ext in OFFICE_TEXT_EXTRACT_EXTS:
        path, cleanup = _resolve_path_for_viewing(file_obj)
        if not path:
            messages.error(request, "Не удалось получить файл для просмотра.")
            return redirect(detail_url)
        try:
            text = extract_text_from_file(path) or ""
            if not text.strip():
                context["viewer_note"] = (
                    "Текст не извлечён (пустой файл или ограничение парсера). "
                    "Скачайте файл или установите LibreOffice для просмотра как PDF."
                )
            if len(text) > _MAX_VIEWER_TEXT:
                text = text[:_MAX_VIEWER_TEXT]
                context["text_truncated"] = True
            context["text_content"] = text
            context["viewer_mode"] = "office"
        finally:
            if cleanup:
                try:
                    os.unlink(path)
                except OSError:
                    pass
    elif ext in ARCHIVE_EXTS:
        context["viewer_mode"] = "archive"
    else:
        context["viewer_mode"] = "fallback"
        if ext in EXTENSIONS_LIBREOFFICE_TO_PDF:
            context["viewer_note"] = (
                "Для просмотра как PDF задайте CONVERTAPI_SECRET (ConvertAPI) "
                "или установите LibreOffice / LIBREOFFICE_PATH."
            )
        else:
            context["viewer_note"] = (
                f"Встроенный просмотр для типа «.{ext or '?'}» не настроен. "
                "Скачайте файл или откройте сырой поток (если браузер умеет)."
            )

    context["viewer_needs_office_pdf_hint"] = (not pdf_conversion_ready) and (
        ext in EXTENSIONS_LIBREOFFICE_TO_PDF
    )

    return render(request, "file_manager/file_viewer.html", context)


@login_required 
def file_edit(request ,file_id ):
    """Редактирование файла"""
    file_obj =get_object_or_404(File ,id =file_id )

    if not can_edit_file_object(request.user, file_obj):
        raise PermissionDenied 

    share_users_queryset = get_share_users_queryset(exclude_user_id=file_obj.uploaded_by_id)

    if request.method =='POST':
        form =FileEditForm(request.POST ,instance =file_obj )
        form.fields["shared_with"].queryset = share_users_queryset
        if form.is_valid():
            form.save()

            FileActivity.log_activity(
            file =file_obj ,
            user =request.user ,
            activity_type ='edit',
            description =f'File edited: {file_obj.title }'
            )

            messages.success(request ,'Файл успешно обновлен')
            return redirect('file_manager:file_detail',file_id =file_obj.id )
        else:
            flash_form_errors(request, form)
    else :
        form =FileEditForm(instance =file_obj )
        form.fields["shared_with"].queryset = share_users_queryset

    return render(request ,'file_manager/file_form.html',{
    'form':form ,
    'title':'Редактировать файл',
    'file':file_obj 
    })


@login_required
def files_bulk_permissions(request):
    editable_files_qs = get_editable_files_queryset(request.user)
    share_users_qs = get_share_users_queryset(exclude_user_id=request.user.id)
    if request.method == "POST":
        form = BulkPermissionForm(
            request.POST,
            editable_files_qs=editable_files_qs,
            share_users_qs=share_users_qs,
        )
        if form.is_valid():
            files = form.cleaned_data["files"]
            visibility = form.cleaned_data["visibility"]
            shared_with = form.cleaned_data["shared_with"]
            updated = 0
            for file_obj in files:
                file_obj.visibility = visibility
                file_obj.save(update_fields=["visibility", "updated_at"])
                if visibility == "shared":
                    file_obj.shared_with.set(shared_with)
                else:
                    file_obj.shared_with.clear()
                FileActivity.log_activity(
                    file=file_obj,
                    user=request.user,
                    activity_type="share",
                    description=f"Bulk permissions update: visibility={visibility}",
                )
                updated += 1
            messages.success(request, f"Права обновлены для {updated} файлов")
            return redirect("file_manager:file_list")
        flash_form_errors(request, form)
    else:
        form = BulkPermissionForm(
            editable_files_qs=editable_files_qs,
            share_users_qs=share_users_qs,
        )
    return render(request, "file_manager/files_bulk_permissions.html", {"form": form})

@login_required 
def file_delete(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not can_delete_file_object(request.user, file_obj):
        raise PermissionDenied 

    if request.method =='POST':
        file_title =file_obj.title 
        file_size =file_obj.file_size 
        file_uploaded_by =file_obj.uploaded_by 

        yandex_path = file_obj.yandex_path
        local_path = file_obj.file.path if file_obj.file else None
        owner = file_obj.uploaded_by

        file_obj.delete()

        FileActivity.objects.create(
        user =request.user ,
        activity_type ='delete',
        description =f'File deleted: {file_title }'
        )

        if yandex_path:
            connection = get_yandex_connection(owner, autocreate_from_social=True)
            if connection:
                try:
                    delete_resource(connection.access_token, yandex_path, permanently=False)
                except Exception:
                    pass

        if local_path and os.path.exists(local_path):
            try :
                os.remove(local_path)
            except OSError :
                pass 

        storage_quota =get_user_storage_usage(request.user )
        storage_quota.update_usage()

        messages.success(request ,'Файл успешно удален')
        return redirect('file_manager:file_list')

    return render(request ,'file_manager/file_confirm_delete.html',{
    'file':file_obj 
    })

@login_required 
def file_version_create(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not can_upload_file_version(request.user, file_obj):
        raise PermissionDenied

    owner = file_obj.uploaded_by
    storage_quota = get_user_storage_usage(owner)

    if request.method =='POST':
        form =FileVersionForm(request.POST ,request.FILES )
        if form.is_valid():
            uploaded_file = request.FILES["version_file"]
            uploaded_content = uploaded_file.read()
            file_size = len(uploaded_content)
            old_size = file_obj.file_size or 0
            extra_required = max(0, file_size - old_size)
            if file_obj.storage_provider == "local" and not storage_quota.has_enough_space(extra_required):
                messages.error(
                    request,
                    f"Недостаточно места в хранилище владельца файла для новой версии. Доступно: {storage_quota.get_quota_display()}",
                )
                return redirect('file_manager:file_version_create',file_id =file_id )

            scan = scan_upload_bytes(
                uploaded_content,
                user_id=request.user.id,
                filename=uploaded_file.name,
            )
            if scan.get("performed") and scan.get("clean") is False:
                threat = scan.get("threat") or "неизвестная угроза"
                messages.error(request, f"Новая версия не загружена: ClamAV обнаружил угрозу «{threat}».")
                return redirect('file_manager:file_version_create', file_id=file_id)
            if getattr(settings, "CLAMAV_ENABLED", False) and not scan.get("performed") and not getattr(settings, "CLAMAV_FAIL_OPEN", True):
                err = scan.get("error") or "проверка не выполнена"
                messages.error(request, f"Новая версия отклонена: ClamAV недоступен ({err}).")
                return redirect('file_manager:file_version_create', file_id=file_id)

            extracted_text = extract_text_from_uploaded_content(uploaded_file.name, uploaded_content)
            banned_match = find_banned_match(extracted_text)
            if banned_match:
                messages.error(
                    request,
                    "Новая версия отклонена: в содержимом обнаружен запрещённый фрагмент по словарю модерации.",
                )
                return redirect('file_manager:file_version_create', file_id=file_id)

            version_number = file_obj.version + 1
            snapshot_path = file_obj.yandex_path if file_obj.storage_provider == "yandex_disk" else (file_obj.file.name if file_obj.file else "")
            structured_snapshot = build_structured_snapshot(uploaded_file.name, uploaded_content)
            try:
                blob_info = _store_revision_blob(
                    file_obj=file_obj,
                    uploaded_by=request.user,
                    content=uploaded_content,
                    original_name=uploaded_file.name,
                    version_number=version_number,
                )
            except Exception as exc:
                messages.error(request, f"Не удалось сохранить blob ревизии: {exc}")
                return redirect('file_manager:file_version_create', file_id=file_id)

            FileVersion.objects.create(
                file=file_obj,
                changed_by=request.user,
                version_number=version_number,
                change_description=form.cleaned_data.get("change_description", ""),
                snapshot_title=file_obj.title,
                snapshot_size=file_obj.file_size,
                snapshot_storage_provider=file_obj.storage_provider,
                snapshot_storage_path=snapshot_path,
                has_blob=blob_info["has_blob"],
                blob_storage_provider=blob_info["blob_storage_provider"],
                blob_storage_path=blob_info["blob_storage_path"],
                blob_size=blob_info["blob_size"],
                blob_sha256=blob_info["blob_sha256"],
                extracted_text_snapshot=extracted_text,
                structured_snapshot=structured_snapshot,
                structured_schema_version=structured_snapshot.get("schema_version", "v1"),
                version_file=blob_info["version_file_name"] or None,
            )

            old_file_path = file_obj.file.path if (file_obj.storage_provider == "local" and file_obj.file) else None
            if file_obj.storage_provider == "yandex_disk":
                connection = get_yandex_connection(owner, autocreate_from_social=True)
                if not connection:
                    messages.error(request, "Не найдено подключение Яндекс.Диска владельца файла")
                    return redirect('file_manager:file_version_create', file_id=file_id)
                target_yandex_path = file_obj.yandex_path or f"disk:/{file_obj.title}"
                upload_file_bytes(connection.access_token, target_yandex_path, uploaded_content, overwrite=True)
                file_obj.yandex_path = target_yandex_path
            else:
                file_obj.file.save(file_obj.title, ContentFile(uploaded_content), save=False)
                if old_file_path and os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                    except OSError:
                        pass

            file_obj.file_size = file_size
            file_obj.extracted_text = extracted_text
            file_obj.version = version_number
            file_obj.save()

            FileActivity.log_activity(
            file =file_obj ,
            user =request.user ,
            activity_type ='version_create',
            description =f'New version {file_obj.version } created: {form.cleaned_data.get("change_description","")}'
            )

            storage_quota.update_usage()

            messages.success(request ,'Новая версия файла создана')
            return redirect('file_manager:file_detail',file_id =file_obj.id )
        else:
            flash_form_errors(request, form)
    else :
        form =FileVersionForm()

    return render(request ,'file_manager/file_version_form.html',{
    'form':form ,
    'file':file_obj ,
    'storage_quota':storage_quota ,
    })


@login_required
def file_version_compare(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    if not file_obj.can_access(request.user):
        raise PermissionDenied

    versions = list(file_obj.versions.select_related("changed_by").order_by("-version_number"))
    from_version_id = request.GET.get("from")
    to_version_id = request.GET.get("to")
    selected_from = None
    selected_to = None
    text_diff = []
    structured_diff = []

    if from_version_id and to_version_id:
        selected_from = get_object_or_404(FileVersion, file=file_obj, id=from_version_id)
        selected_to = get_object_or_404(FileVersion, file=file_obj, id=to_version_id)
        from_text = selected_from.extracted_text_snapshot or ""
        to_text = selected_to.extracted_text_snapshot or ""
        if from_text or to_text:
            text_diff = list(
                difflib.unified_diff(
                    from_text.splitlines(),
                    to_text.splitlines(),
                    fromfile=f"v{selected_from.version_number}",
                    tofile=f"v{selected_to.version_number}",
                    lineterm="",
                )
            )
        from_structured = selected_from.structured_snapshot or {}
        to_structured = selected_to.structured_snapshot or {}
        if from_structured or to_structured:
            structured_diff = list(
                difflib.unified_diff(
                    json.dumps(from_structured, ensure_ascii=False, indent=2).splitlines(),
                    json.dumps(to_structured, ensure_ascii=False, indent=2).splitlines(),
                    fromfile=f"structured-v{selected_from.version_number}",
                    tofile=f"structured-v{selected_to.version_number}",
                    lineterm="",
                )
            )

    return render(
        request,
        "file_manager/file_version_compare.html",
        {
            "file": file_obj,
            "versions": versions,
            "selected_from": selected_from,
            "selected_to": selected_to,
            "text_diff": text_diff,
            "structured_diff": structured_diff,
        },
    )


@login_required
@require_http_methods(["POST"])
def file_version_restore(request, file_id, version_id):
    file_obj = get_object_or_404(File, id=file_id)
    if not can_upload_file_version(request.user, file_obj):
        raise PermissionDenied
    target_version = get_object_or_404(FileVersion, file=file_obj, id=version_id)
    if not target_version.has_blob and not target_version.version_file:
        messages.error(request, "Эта версия legacy и не содержит blob для восстановления.")
        return redirect("file_manager:file_detail", file_id=file_id)

    try:
        restored_content = _read_revision_blob_bytes(target_version)
    except Exception as exc:
        messages.error(request, f"Не удалось прочитать blob версии: {exc}")
        return redirect("file_manager:file_detail", file_id=file_id)

    restored_text = target_version.extracted_text_snapshot or ""
    owner = file_obj.uploaded_by
    old_file_path = file_obj.file.path if (file_obj.storage_provider == "local" and file_obj.file) else None
    if file_obj.storage_provider == "yandex_disk":
        connection = get_yandex_connection(owner, autocreate_from_social=True)
        if not connection:
            messages.error(request, "Не найдено подключение Яндекс.Диска владельца файла")
            return redirect("file_manager:file_detail", file_id=file_id)
        target_yandex_path = file_obj.yandex_path or f"disk:/{file_obj.title}"
        upload_file_bytes(connection.access_token, target_yandex_path, restored_content, overwrite=True)
        file_obj.yandex_path = target_yandex_path
    else:
        file_obj.file.save(file_obj.title, ContentFile(restored_content), save=False)
        if old_file_path and os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except OSError:
                pass

    new_version_number = file_obj.version + 1
    try:
        blob_info = _store_revision_blob(
            file_obj=file_obj,
            uploaded_by=request.user,
            content=restored_content,
            original_name=file_obj.title,
            version_number=new_version_number,
        )
    except Exception as exc:
        messages.error(request, f"Текущий файл восстановлен, но commit версии не записан: {exc}")
        return redirect("file_manager:file_detail", file_id=file_id)

    FileVersion.objects.create(
        file=file_obj,
        changed_by=request.user,
        version_number=new_version_number,
        change_description=f"Restore from version {target_version.version_number}",
        snapshot_title=file_obj.title,
        snapshot_size=file_obj.file_size,
        snapshot_storage_provider=file_obj.storage_provider,
        snapshot_storage_path=file_obj.yandex_path if file_obj.storage_provider == "yandex_disk" else (file_obj.file.name if file_obj.file else ""),
        has_blob=blob_info["has_blob"],
        blob_storage_provider=blob_info["blob_storage_provider"],
        blob_storage_path=blob_info["blob_storage_path"],
        blob_size=blob_info["blob_size"],
        blob_sha256=blob_info["blob_sha256"],
        extracted_text_snapshot=restored_text,
        structured_snapshot=target_version.structured_snapshot,
        structured_schema_version=target_version.structured_schema_version or "v1",
        version_file=blob_info["version_file_name"] or None,
    )

    file_obj.file_size = len(restored_content)
    file_obj.extracted_text = restored_text
    file_obj.version = new_version_number
    file_obj.save()

    FileActivity.log_activity(
        file=file_obj,
        user=request.user,
        activity_type="version_create",
        description=f"Restored from version {target_version.version_number} to new version {new_version_number}",
    )
    messages.success(request, f"Файл восстановлен из версии {target_version.version_number}.")
    return redirect("file_manager:file_detail", file_id=file_id)

@login_required 
def favorite_toggle(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_access(request.user ):
        raise PermissionDenied 

    if file_obj.is_favorite(request.user ):
        file_obj.remove_from_favorites(request.user )
        messages.success(request ,'Файл удален из избранного')
        activity_type ='favorite_remove'
    else :
        file_obj.add_to_favorites(request.user )
        messages.success(request ,'Файл добавлен в избранное')
        activity_type ='favorite_add'

    FileActivity.log_activity(
    file =file_obj ,
    user =request.user ,
    activity_type =activity_type ,
    description =f'Favorite status toggled for: {file_obj.title }'
    )

    return redirect(request.META.get('HTTP_REFERER','file_manager:file_list'))

@login_required 
def file_comment_create(request ,file_id ):
    file_obj =get_object_or_404(File ,id =file_id )

    if not file_obj.can_access(request.user ):
        raise PermissionDenied 

    if request.method =='POST':
        form =FileCommentForm(request.POST )
        if form.is_valid():
            comment =form.save(commit =False )
            comment.file =file_obj 
            comment.author =request.user 
            comment.save()

            FileActivity.log_activity(
            file =file_obj ,
            user =request.user ,
            activity_type ='comment',
            description =f'Comment added to: {file_obj.title }'
            )

            messages.success(request ,'Комментарий добавлен')
        else:
            flash_form_errors(request, form)

        return redirect('file_manager:file_detail',file_id =file_id )

    return redirect('file_manager:file_detail',file_id =file_id )

@login_required 
def file_comment_delete(request ,comment_id ):
    comment =get_object_or_404(FileComment ,id =comment_id )

    if not comment.can_delete(request.user ):
        raise PermissionDenied 

    file_id =comment.file.id 
    comment.delete()

    FileActivity.log_activity(
    file =comment.file ,
    user =request.user ,
    activity_type ='comment',
    description =f'Comment deleted from: {comment.file.title }'
    )

    messages.success(request ,'Комментарий удален')
    return redirect('file_manager:file_detail',file_id =file_id )

@login_required 
def activity_log(request ):
    if is_admin_user(request.user):
        activities = FileActivity.objects.all().select_related('file', 'user')
    else:
        activities =FileActivity.objects.filter(user =request.user ).select_related('file','user')

    activity_type =request.GET.get('activity_type')
    if activity_type :
        activities =activities.filter(activity_type =activity_type )

    paginator =Paginator(activities ,20 )
    page_number =request.GET.get('page')
    page_obj =paginator.get_page(page_number )

    context ={
    'page_obj':page_obj ,
    'activity_types':FileActivity.ACTIVITY_TYPES ,
    'selected_activity_type':activity_type ,
    }

    return render(request ,'file_manager/activity_log.html',context )

@login_required 
def tag_list(request ):
    if not can_manage_reference_data(request.user):
        raise PermissionDenied
    tags = (
        Tag.objects.annotate(
            file_count=Count("files", filter=Q(files__is_folder=False))
        )
        .order_by("name")
    )
    return render(request, "file_manager/tag_list.html", {"tags": tags})

@login_required 
def tag_create(request ):
    if not can_manage_reference_data(request.user):
        raise PermissionDenied
    if request.method =='POST':
        form =TagForm(request.POST )
        if form.is_valid():
            form.save()
            messages.success(request ,'Тег создан')
            return redirect('file_manager:tag_list')
        else:
            flash_form_errors(request, form)
    else :
        form =TagForm()

    return render(request ,'file_manager/tag_form.html',{'form':form })


@login_required
@require_http_methods(["POST"])
def tag_delete(request, tag_id):
    if not can_manage_reference_data(request.user):
        raise PermissionDenied
    tag = get_object_or_404(Tag, pk=tag_id)
    name = tag.name
    tag.delete()
    messages.success(
        request,
        f'Тег «{name}» удалён. С файлов он снят, сами файлы не изменены.',
    )
    return redirect("file_manager:tag_list")


@login_required 
def get_storage_quota(request ):
    if request.method =='GET':
        yandex_connection = get_yandex_connection(request.user, autocreate_from_social=True)
        if yandex_connection:
            try:
                disk_info = get_disk_info(yandex_connection.access_token)
                used_bytes = int(disk_info.get("used_space", 0))
                total_quota_bytes = int(disk_info.get("total_space", 0))
                used_percentage = (used_bytes / total_quota_bytes * 100) if total_quota_bytes > 0 else 0
                return JsonResponse({
                    'used_bytes': used_bytes,
                    'total_quota_bytes': total_quota_bytes,
                    'used_percentage': used_percentage,
                })
            except Exception:
                pass
        storage_quota =get_user_storage_usage(request.user )
        return JsonResponse({
        'used_bytes':storage_quota.used_bytes ,
        'total_quota_bytes':storage_quota.total_quota_bytes ,
        'used_percentage':storage_quota.get_used_percentage()
        })
    return JsonResponse({'error':'Method not allowed'},status =405 )


@login_required
def yandex_oauth_start(request):
    state = get_random_string(24)
    request.session["yandex_oauth_state"] = state
    authorize_url = get_authorize_url(
        settings.YANDEX_DISK_CLIENT_ID,
        settings.YANDEX_DISK_REDIRECT_URI or request.build_absolute_uri("/files/oauth/yandex/callback/"),
        state,
    )
    return redirect(authorize_url)


@login_required
def yandex_oauth_callback(request):
    state = request.GET.get("state")
    code = request.GET.get("code")
    if not state or state != request.session.get("yandex_oauth_state"):
        messages.error(request, "Неверный OAuth state")
        return redirect("file_manager:file_list")
    if not code:
        messages.error(request, "OAuth код не получен")
        return redirect("file_manager:file_list")

    try:
        token_data = exchange_code_for_token(
            settings.YANDEX_DISK_CLIENT_ID,
            settings.YANDEX_DISK_CLIENT_SECRET,
            code,
        )
    except Exception:
        messages.error(request, "Не удалось подключить Яндекс.Диск")
        return redirect("file_manager:file_list")

    expires_at = timezone.now() + timezone.timedelta(seconds=int(token_data.get("expires_in", 0)))
    ExternalStorageConnection.objects.update_or_create(
        user=request.user,
        provider="yandex_disk",
        defaults={
            "access_token": token_data.get("access_token", ""),
            "refresh_token": token_data.get("refresh_token", ""),
            "expires_at": expires_at,
        },
    )
    messages.success(request, "Яндекс.Диск подключен")
    return redirect("file_manager:file_list")


@login_required
def yandex_disconnect(request):
    ExternalStorageConnection.objects.filter(user=request.user, provider="yandex_disk").delete()
    messages.success(request, "Яндекс.Диск отключен")
    return redirect("file_manager:file_list")


@login_required
def yandex_file_picker(request):
    connection = get_yandex_connection(request.user, autocreate_from_social=True)
    if not connection:
        messages.error(request, "Сначала подключите Яндекс.Диск")
        return redirect("file_manager:file_list")

    files = []
    try:
        files = [f for f in list_files(connection.access_token) if f.get("type") == "file"]
    except Exception:
        messages.error(request, "Не удалось получить список файлов с Яндекс.Диска")
        return redirect("file_manager:file_list")

    if request.method == "POST":
        selected_raw = request.POST.get("selected_file", "")
        selected_path = ""
        selected_name = ""
        if "||" in selected_raw:
            selected_path, selected_name = selected_raw.split("||", 1)
        assignment_id = request.POST.get("assignment_id") or request.GET.get("assignment_id")
        section_id = request.POST.get("section_id") or request.GET.get("section_id")
        if not selected_path or not selected_name:
            messages.error(request, "Файл не выбран")
            return redirect("file_manager:yandex_picker")
        download_url = get_download_url(connection.access_token, selected_path)
        if not download_url:
            messages.error(request, "Не удалось получить ссылку на скачивание")
            return redirect("file_manager:yandex_picker")
        response = requests.get(download_url, timeout=60)
        response.raise_for_status()
        file_obj = import_yandex_file(request.user, selected_name, response.content)
        storage_quota = get_user_storage_usage(request.user)
        storage_quota.update_usage()
        if assignment_id:
            from classroom_core.models import Assignment, AssignmentFile
            assignment = Assignment.objects.filter(id=assignment_id).first()
            if assignment:
                AssignmentFile.objects.get_or_create(
                    assignment=assignment,
                    student=request.user,
                    file=file_obj,
                    defaults={"description": "Импортировано с Яндекс.Диска"},
                )
                messages.success(request, "Файл импортирован и прикреплен к заданию")
                return redirect("classroom_core:assignment_detail", assignment_id=assignment.id)
        if section_id:
            from classroom_core.models import CourseSection, CourseMaterial
            section = CourseSection.objects.filter(id=section_id).first()
            if section:
                CourseMaterial.objects.create(
                    section=section,
                    title=selected_name,
                    description="Импортировано с Яндекс.Диска",
                    material_type="link",
                    url=request.build_absolute_uri(file_obj.file.url),
                    is_visible=True,
                    status="published",
                )
                messages.success(request, "Файл импортирован и добавлен как материал курса")
                return redirect("classroom_core:course_detail", course_id=section.course_id)
        messages.success(request, "Файл импортирован из Яндекс.Диска")
        return redirect("file_manager:file_detail", file_id=file_obj.id)

    return render(request, "file_manager/yandex_picker.html", {"yandex_files": files})


@login_required
@require_http_methods(["POST"])
def yandex_export_file(request, file_id):
    file_obj = get_object_or_404(File, id=file_id)
    if not file_obj.can_access(request.user):
        raise PermissionDenied

    connection = get_yandex_connection(request.user, autocreate_from_social=True)
    if not connection:
        messages.error(request, "Сначала подключите Яндекс.Диск")
        return redirect("file_manager:file_detail", file_id=file_obj.id)

    if not file_obj.file:
        messages.error(request, "Нельзя экспортировать папку или пустой файл")
        return redirect("file_manager:file_detail", file_id=file_obj.id)

    yandex_path = f"disk:/{file_obj.title}"
    try:
        with open(file_obj.file.path, "rb") as fh:
            upload_file_bytes(connection.access_token, yandex_path, fh.read(), overwrite=True)
    except Exception:
        messages.error(request, "Не удалось выгрузить файл на Яндекс.Диск")
        return redirect("file_manager:file_detail", file_id=file_obj.id)

    messages.success(request, "Файл выгружен на Яндекс.Диск")
    return redirect("file_manager:file_detail", file_id=file_obj.id)


@login_required
def download_all_files_archive(request):
    files = File.objects.filter(uploaded_by=request.user, is_folder=False)
    if files.count() == 0:
        messages.error(request, "Нет файлов для скачивания")
        return redirect("file_manager:file_list")
    else:
        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_obj in files:
                try:
                    if file_obj.storage_provider == "yandex_disk" and file_obj.yandex_path:
                        connection = get_yandex_connection(file_obj.uploaded_by, autocreate_from_social=True)
                        if not connection:
                            continue
                        href = get_download_url(connection.access_token, file_obj.yandex_path)
                        content = requests.get(href, timeout=60).content
                        archive.writestr(file_obj.title, content)
                    elif file_obj.file:
                        file_path = Path(file_obj.file.path)
                        if file_path.exists():
                            archive.write(file_path, arcname=file_path.name)
                except Exception:
                    continue
        archive_buffer.seek(0)
        response = HttpResponse(archive_buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="portfolio_files.zip"'
        return response


@login_required
def workspace_user_search(request):
    """JSON: поиск пользователей для добавления в workspace (логин, имя, email)."""
    q = (request.GET.get("q") or "").strip()
    workspace_raw = (request.GET.get("workspace") or "").strip()
    exclude_ids = {request.user.pk}
    if workspace_raw:
        try:
            ws = SharedWorkspace.objects.filter(
                participants=request.user, pk=int(workspace_raw)
            ).first()
            if ws:
                exclude_ids |= set(ws.participants.values_list("pk", flat=True))
        except (ValueError, TypeError):
            pass
    if len(q) < 2:
        return JsonResponse({"users": []})
    qs = (
        User.objects.filter(is_active=True)
        .exclude(pk__in=exclude_ids)
        .filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
        .distinct()
        .order_by("username")[:40]
    )
    users = [
        {
            "id": u.pk,
            "username": u.username,
            "label": (u.get_full_name() or "").strip() or u.username,
        }
        for u in qs
    ]
    return JsonResponse({"users": users})


@login_required
def workspace_list(request):
    # Сначала id без annotate: иначе JOIN по participants + Count(files) даёт неверные
    # агрегаты (часто совпадающие с числом участников из‑за размножения строк в SQL).
    workspace_ids = (
        SharedWorkspace.objects.filter(
            Q(owner=request.user) | Q(participants=request.user)
        )
        .values_list("pk", flat=True)
        .distinct()
    )
    workspaces = (
        SharedWorkspace.objects.filter(pk__in=workspace_ids)
        .annotate(
            file_count=Count(
                "files",
                filter=Q(files__is_folder=False),
                distinct=True,
            )
        )
        .select_related("owner")
        .prefetch_related("participants")
        .order_by("-created_at")
    )
    return render(request, "file_manager/workspace_list.html", {"workspaces": workspaces})


@login_required
@require_http_methods(["POST"])
def workspace_create(request):
    title = (request.POST.get("title") or "").strip()
    raw_ids = request.POST.getlist("participant_ids")
    user_ids = []
    for x in raw_ids:
        try:
            user_ids.append(int(x))
        except (TypeError, ValueError):
            continue
    user_ids = list(dict.fromkeys(user_ids))
    if not title:
        messages.error(request, "Укажите название workspace")
        return redirect("file_manager:workspace_list")
    if not user_ids:
        messages.error(request, "Выберите хотя бы одного участника в списке после поиска")
        return redirect("file_manager:workspace_list")
    users = list(
        User.objects.filter(pk__in=user_ids, is_active=True).exclude(pk=request.user.pk)
    )
    if len(users) != len(user_ids):
        messages.warning(request, "Часть выбранных пользователей недоступна или не найдена")
    if not users:
        messages.error(request, "Не удалось добавить участников — выберите пользователей из поиска")
        return redirect("file_manager:workspace_list")
    workspace = SharedWorkspace.objects.create(title=title, owner=request.user)
    workspace.participants.add(request.user, *users)
    messages.success(
        request,
        "Workspace создан. Добавьте к нему файлы со страницы файла (владелец файла выбирает workspace).",
    )
    return redirect("file_manager:workspace_detail", workspace_id=workspace.id)


@login_required
def workspace_detail(request, workspace_id):
    ws = get_object_or_404(
        SharedWorkspace.objects.filter(participants=request.user)
        .select_related("owner")
        .prefetch_related("participants", "files__uploaded_by", "files__tags"),
        pk=workspace_id,
    )
    is_owner = ws.owner_id == request.user.id
    workspace_files = ws.files.filter(is_folder=False).order_by("title")
    return render(
        request,
        "file_manager/workspace_detail.html",
        {
            "workspace": ws,
            "is_owner": is_owner,
            "workspace_files": workspace_files,
        },
    )


@login_required
@require_http_methods(["POST"])
def workspace_add_participant(request, workspace_id):
    ws = get_object_or_404(
        SharedWorkspace.objects.filter(participants=request.user), pk=workspace_id
    )
    if ws.owner_id != request.user.id:
        raise PermissionDenied
    raw_ids = request.POST.getlist("participant_ids")
    user_ids = []
    for x in raw_ids:
        try:
            user_ids.append(int(x))
        except (TypeError, ValueError):
            continue
    user_ids = list(dict.fromkeys(user_ids))
    if not user_ids:
        messages.error(request, "Отметьте пользователей в результатах поиска")
        return redirect("file_manager:workspace_detail", workspace_id=ws.pk)
    added = 0
    skipped = 0
    for uid in user_ids:
        user = User.objects.filter(pk=uid, is_active=True).exclude(pk=request.user.pk).first()
        if not user:
            continue
        if ws.participants.filter(pk=user.pk).exists():
            skipped += 1
            continue
        ws.participants.add(user)
        added += 1
    if added:
        messages.success(request, f"Добавлено участников: {added}")
    if skipped:
        messages.info(request, f"Уже в workspace (пропущено): {skipped}")
    if not added and not skipped:
        messages.error(request, "Не удалось добавить выбранных пользователей")
    return redirect("file_manager:workspace_detail", workspace_id=ws.pk)


@login_required
@require_http_methods(["POST"])
def workspace_remove_participant(request, workspace_id):
    ws = get_object_or_404(
        SharedWorkspace.objects.filter(participants=request.user), pk=workspace_id
    )
    try:
        user_id = int(request.POST.get("user_id", 0))
    except ValueError:
        user_id = 0
    if not user_id:
        messages.error(request, "Не указан пользователь")
        return redirect("file_manager:workspace_detail", workspace_id=ws.pk)
    target = get_object_or_404(User, pk=user_id)
    is_owner = ws.owner_id == request.user.id
    if user_id == request.user.id:
        if is_owner:
            messages.error(
                request,
                "Владелец не может покинуть workspace без удаления. Удалите workspace целиком, если он больше не нужен.",
            )
            return redirect("file_manager:workspace_detail", workspace_id=ws.pk)
        ws.participants.remove(request.user)
        messages.success(request, "Вы вышли из workspace")
        return redirect("file_manager:workspace_list")
    if not is_owner:
        raise PermissionDenied
    if user_id == ws.owner_id:
        messages.error(request, "Нельзя исключить владельца")
        return redirect("file_manager:workspace_detail", workspace_id=ws.pk)
    ws.participants.remove(target)
    messages.success(request, "Участник исключён")
    return redirect("file_manager:workspace_detail", workspace_id=ws.pk)


@login_required
@require_http_methods(["POST"])
def workspace_remove_file(request, workspace_id):
    ws = get_object_or_404(
        SharedWorkspace.objects.filter(participants=request.user), pk=workspace_id
    )
    try:
        fid = int(request.POST.get("file_id", 0))
    except ValueError:
        fid = 0
    file_obj = get_object_or_404(File, pk=fid, is_folder=False)
    if not ws.files.filter(pk=file_obj.pk).exists():
        messages.error(request, "Этого файла нет в этом workspace")
        return redirect("file_manager:workspace_detail", workspace_id=ws.pk)
    if not (ws.owner_id == request.user.id or file_obj.uploaded_by_id == request.user.id):
        raise PermissionDenied
    ws.files.remove(file_obj)
    messages.success(request, "Файл убран из workspace (сам файл не удалён)")
    return redirect("file_manager:workspace_detail", workspace_id=ws.pk)


@login_required
@require_http_methods(["POST"])
def workspace_delete(request, workspace_id):
    ws = get_object_or_404(
        SharedWorkspace.objects.filter(participants=request.user), pk=workspace_id
    )
    if ws.owner_id != request.user.id:
        raise PermissionDenied
    title = ws.title
    ws.delete()
    messages.success(request, f"Workspace «{title}» удалён")
    return redirect("file_manager:workspace_list")


@login_required
@require_http_methods(["POST"])
def workspace_add_file(request, file_id):
    file_obj = get_object_or_404(File, id=file_id, is_folder=False)
    if not file_obj.can_access(request.user):
        raise PermissionDenied
    if not can_edit_file_object(request.user, file_obj):
        messages.error(
            request,
            "Добавлять файл в workspace может только владелец файла или администратор.",
        )
        return redirect("file_manager:file_detail", file_id=file_id)
    workspace_id = (request.POST.get("workspace_id") or "").strip()
    if not workspace_id:
        messages.error(request, "Выберите workspace из списка")
        return redirect("file_manager:file_detail", file_id=file_id)
    workspace = get_object_or_404(
        SharedWorkspace.objects.filter(participants=request.user), pk=workspace_id
    )
    workspace.files.add(file_obj)
    others = list(workspace.participants.exclude(pk=request.user.pk))
    if others:
        file_obj.shared_with.add(*others)
        if file_obj.visibility != "shared":
            file_obj.visibility = "shared"
            file_obj.save(update_fields=["visibility"])
    messages.success(
        request,
        f'Файл добавлен в workspace «{workspace.title}». Участникам выдан доступ «Общий».',
    )
    return redirect("file_manager:file_detail", file_id=file_id)


@login_required
def backup_compare(request):
    backups_dir = Path(settings.BASE_DIR) / "backups"
    first = request.GET.get("first")
    second = request.GET.get("second")
    backups = sorted([p.name for p in backups_dir.glob("snapshot_*.zip")], reverse=True)
    diff = {"added": [], "removed": []}
    if first and second:
        first_set, second_set = set(), set()
        with zipfile.ZipFile(backups_dir / first, "r") as z1:
            first_set = set(z1.namelist())
        with zipfile.ZipFile(backups_dir / second, "r") as z2:
            second_set = set(z2.namelist())
        diff["added"] = sorted(list(second_set - first_set))
        diff["removed"] = sorted(list(first_set - second_set))
    return render(request, "file_manager/backup_compare.html", {"backups": backups, "diff": diff, "first": first, "second": second})