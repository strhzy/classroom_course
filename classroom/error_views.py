from django.shortcuts import render


ERROR_META = {
    400: {
        "title": "Некорректный запрос",
        "message": "Запрос не удалось обработать. Проверьте данные и попробуйте снова.",
    },
    403: {
        "title": "Доступ запрещен",
        "message": "У вас нет прав для просмотра этой страницы.",
    },
    404: {
        "title": "Страница не найдена",
        "message": "Похоже, такой страницы не существует или она была перемещена.",
    },
    500: {
        "title": "Внутренняя ошибка сервера",
        "message": "На сервере произошла ошибка. Попробуйте обновить страницу немного позже.",
    },
}


def _render_http_error(request, status_code):
    meta = ERROR_META.get(status_code, ERROR_META[500])
    context = {
        "status_code": status_code,
        "error_title": meta["title"],
        "error_message": meta["message"],
    }
    return render(request, "errors/http_error.html", context=context, status=status_code)


def http_400(request, exception):
    return _render_http_error(request, 400)


def http_403(request, exception):
    return _render_http_error(request, 403)


def http_404(request, exception):
    return _render_http_error(request, 404)


def http_500(request):
    return _render_http_error(request, 500)
