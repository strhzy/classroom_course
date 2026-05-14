from django.db import migrations


class Migration(migrations.Migration):
    """
    B-tree по TextField (extracted_text) в PostgreSQL ограничен размером ключа (~2704 байта);
    длинный извлечённый текст ломает INSERT/UPDATE. Поиск __icontains всё равно не опирается на этот индекс.
    """

    dependencies = [
        ("file_manager", "0008_remove_file_category_folder_fields"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="file",
            name="file_manage_extract_20066c_idx",
        ),
    ]
