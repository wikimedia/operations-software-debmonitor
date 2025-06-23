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
