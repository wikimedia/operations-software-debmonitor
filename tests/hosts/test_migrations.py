import pytest

from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from hosts.models import Host


@pytest.mark.django_db(transaction=True)
def test_migration_20180621_backward():
    """Migrating backward should have a Host object with the old properties."""
    existing = Host.objects.first()
    executor = MigrationExecutor(connection)
    migrate_to = [('hosts', '0001_initial')]
    executor.migrate(migrate_to)  # Migrate backwards
    old_apps = executor.loader.project_state(migrate_to).apps
    old_host = old_apps.get_model('hosts', 'Host').objects.first()

    assert old_host.running_kernel == existing.kernel.name
    assert old_host.running_kernel_slug == existing.kernel.slug


@pytest.mark.django_db(transaction=True)
def test_migration_20180621_forward():
    """Migrating backward and then forward again should result in the same host object."""
    migrate_to = [('hosts', '0005_auto_20180621_0620')]
    executor = MigrationExecutor(connection)
    apps = executor.loader.project_state(migrate_to).apps

    executor.migrate(migrate_to)  # Migrate backward to this point
    executor.loader.build_graph()  # Reload the graph
    existing = apps.get_model('hosts', 'Host').objects.first()

    executor.migrate([('hosts', '0001_initial')])  # Migrate backwards
    executor.loader.build_graph()  # Reload the graph
    executor.migrate([('hosts', '0005_auto_20180621_0620')])  # Migrate forward

    assert apps.get_model('hosts', 'Host').objects.first() == existing
