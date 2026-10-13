import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("items", "0007_item_prefix"),
        ("search", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name="searchindex",
                    name="item",
                ),
                migrations.AddField(
                    model_name="searchindex",
                    name="id",
                    field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                migrations.AddField(
                    model_name="searchindex",
                    name="item",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="search_indexes",
                        to="items.item",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE search_index ADD COLUMN id uuid;
                        UPDATE search_index SET id = gen_random_uuid();
                        ALTER TABLE search_index ALTER COLUMN id SET NOT NULL;
                        ALTER TABLE search_index DROP CONSTRAINT search_index_pkey;
                        ALTER TABLE search_index ADD CONSTRAINT search_index_pkey PRIMARY KEY (id);
                        ALTER TABLE search_index ALTER COLUMN item_id DROP NOT NULL;
                    """,
                    reverse_sql="""
                        DELETE FROM search_index WHERE item_id IS NULL;
                        ALTER TABLE search_index DROP CONSTRAINT search_index_pkey;
                        ALTER TABLE search_index DROP COLUMN id;
                        ALTER TABLE search_index ALTER COLUMN item_id SET NOT NULL;
                        ALTER TABLE search_index ADD CONSTRAINT search_index_pkey PRIMARY KEY (item_id);
                    """,
                ),
            ],
        ),
    ]
