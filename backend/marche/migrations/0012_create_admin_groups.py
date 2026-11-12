"""運営スタッフの権限グループ（管理者・CS・審査担当）を作る

グループの名前は api/common/permissions.py の ADMIN_GROUP・CS_GROUP・REVIEWER_GROUP と同じ。
最初の管理者は python manage.py create_admin で作る。
"""
from django.db import migrations

GROUPS = ["管理者", "CS", "審査担当"]


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in GROUPS:
        Group.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("marche", "0011_notification_listing_status"),
    ]

    operations = [
        migrations.RunPython(create_groups, migrations.RunPython.noop),
    ]
