from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("file_manager", "0002_externalstorageconnection"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="file",
            name="importance",
            field=models.CharField(
                choices=[("main", "Основное"), ("important", "Важное"), ("secondary", "Второстепенное")],
                default="main",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="FavoriteCollection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorite_collections", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["title"], "unique_together": {("user", "title")}},
        ),
        migrations.CreateModel(
            name="SharedWorkspace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("files", models.ManyToManyField(blank=True, related_name="workspaces", to="file_manager.file")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="owned_workspaces", to=settings.AUTH_USER_MODEL)),
                ("participants", models.ManyToManyField(related_name="shared_workspaces", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="FavoriteCollectionItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("collection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="file_manager.favoritecollection")),
                ("file", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorite_collection_items", to="file_manager.file")),
            ],
            options={"unique_together": {("collection", "file")}},
        ),
    ]
