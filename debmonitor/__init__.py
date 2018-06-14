import ast
import hashlib
import os

from django.conf import settings as django_settings
from django.db.models import Aggregate, Manager


class SelectManager(Manager):
    """Custom manager to transparently select related items."""

    def __init__(self, *args, **kwargs):
        """Override parent constructor to set the related fields to always select."""
        self._select_related = kwargs.pop('_select_related', [])

        super().__init__(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        """Override parent method to apply the select_related() based on self._select_related."""
        queryset = super().get_queryset(*args, **kwargs)
        return queryset.select_related(*self._select_related)


class DistinctGroupConcat(Aggregate):
    """Implement a simple DISTINCT GROUP_CONCAT aggregation for MySQL and SQLite."""

    template = "GROUP_CONCAT(DISTINCT %(expressions)s ORDER BY %(expressions)s SEPARATOR ', ')"

    def as_sqlite(self, compiler, connection):
        """Override the SQLite version that has a different syntax and requires a workaround."""
        return self.as_sql(compiler, connection, template="replace(group_concat(distinct %(expressions)s), ',', ', ')")


def get_client():
    """Load the DebMonitor client CLI body and return its content, version and checksum."""
    path = os.path.join(django_settings.BASE_DIR, 'utils', 'cli.py')
    with open(path, 'r') as f:
        body = f.read()

    checksum = hashlib.sha256(body.encode('utf-8')).hexdigest()
    version = ''
    tree = ast.parse(body)
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == '__version__':
                version = ast.literal_eval(node.value)
                break

    return version, checksum, body
