import json
import sys

import pytest

from unittest.mock import MagicMock


CONFIG = """{
    "KEY": "VALUE",
    "USER_SEARCH": {
        "USER_FIELD": "uid",
        "SEARCH": "ou=people,dc=example,dc=com"
    },
    "GROUP_SEARCH": "dc=example,dc=com",
    "GLOBAL_OPTIONS": {
        "OPT_X_OPTION1": "VALUE1"
    },
    "REQUIRE_GROUP": __GROUP__,
    "USER_FLAGS_BY_GROUP": {
        "is_active": ["cn=staff,ou=groups,dc=example,dc=com", "cn=contractor,ou=groups,dc=example,dc=com"],
        "is_staff": ["cn=staff,ou=groups,dc=example,dc=com"],
        "is_superuser": "cn=admin,ou=groups,dc=example,dc=com",
        "is_empty": []
    }
}
"""


@pytest.mark.parametrize('group', (
    '[]',
    '"cn=staff,ou=groups,dc=example,dc=com"',
    '["cn=staff,ou=groups,dc=example,dc=com"]',
    '["cn=staff,ou=groups,dc=example,dc=com", "cn=contractor,ou=groups,dc=example,dc=com"]',
))
def test_get_settings(group):
    """Calling get_settings() should parse the LDAP config and return the LDAP settings."""
    # Inject mocked modules before importing to allow to run the test also without the LDAP dependencies that are
    # platform-specific.
    sys.modules['ldap'] = MagicMock()
    sys.modules['django_auth_ldap.config'] = MagicMock()
    from debmonitor.settings._ldap import get_settings

    config = json.loads(CONFIG.replace('__GROUP__', group))
    settings = get_settings(config)

    assert settings['AUTH_LDAP_KEY'] == 'VALUE'
    assert 'is_empty' not in settings['AUTH_LDAP_USER_FLAGS_BY_GROUP']
    assert 'AUTH_LDAP_GROUP_TYPE' in settings

    del sys.modules['ldap']
    del sys.modules['django_auth_ldap.config']
