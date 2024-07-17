from django.db.backends.mysql import base, schema


class DatabaseSchemaEditor(schema.DatabaseSchemaEditor):
    """Override the default MySQL database schema editor to add ROW_FORMAT=dynamic."""
    sql_create_table = "CREATE TABLE %(table)s (%(definition)s) ROW_FORMAT=DYNAMIC"


class DatabaseWrapper(base.DatabaseWrapper):
    """Override the default MySQL database wrapper to use the custom schema editor class."""
    SchemaEditorClass = DatabaseSchemaEditor
