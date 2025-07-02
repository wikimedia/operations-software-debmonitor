import pytest

from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from kubernetes.models import KubernetesImage


@pytest.mark.django_db(transaction=True)
def test_migration_20250702():
    """Migrating backward/forward should have a KubernetesImage object with the."""
    existing_k8s = KubernetesImage.objects.first()
    existing_containers = existing_k8s.containers
    existing_namespaces = existing_k8s.image.namespaces.all()
    assert existing_containers == 2
    assert len(existing_namespaces) == 1

    executor = MigrationExecutor(connection)
    migrate_to = [('kubernetes', '0001_initial')]
    executor.migrate(migrate_to)  # Migrate backwards
    executor.loader.build_graph()  # Reload the graph
    old_apps = executor.loader.project_state(migrate_to).apps
    old_k8s = old_apps.get_model('kubernetes', 'KubernetesImage').objects.first()

    assert old_k8s.instances == existing_containers
    old_instances = old_k8s.image.instances.all()
    assert len(old_instances) == 1
    assert old_instances[0].cluster == existing_namespaces[0].cluster
    assert old_instances[0].namespace == existing_namespaces[0].namespace
    assert old_instances[0].image.name == existing_namespaces[0].image.name
    assert old_instances[0].instances == existing_namespaces[0].containers

    migrate_to = [('kubernetes', '0002_auto_20250702_1052')]
    executor.migrate(migrate_to)  # Migrate forwards
    executor.loader.build_graph()  # Reload the graph
    new_apps = executor.loader.project_state(migrate_to).apps

    new_k8s = new_apps.get_model('kubernetes', 'KubernetesImage').objects.first()

    assert new_k8s.containers == existing_containers
    assert new_k8s.image.namespaces.all()[0].cluster == existing_namespaces[0].cluster
