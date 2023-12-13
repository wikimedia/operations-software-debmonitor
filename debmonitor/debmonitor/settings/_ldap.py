import ldap

from django_auth_ldap.config import LDAPGroupQuery, LDAPSearch, GroupOfNamesType


def get_settings(config):
    """Generate the LDAP settings based on the configuration.

    Arguments:
        dict: the LDAP-specific configuration.

    Returns:
        dict: where the keys are the attributes to set with the value.

    """
    settings = {}

    for key, value in config.items():
        settings.update(_parse_config_item(key, value))

    return settings


def _parse_config_item(key, value):
    """Generate the settings related to a specific configuration item.

    Arguments:
        key (str): the configuration name.
        value (mixed): the configuration value to parse.

    Returns:
        dict: with the additional settings to create based on the config.

    """
    if key == 'GROUP_SEARCH':
        return {'AUTH_LDAP_GROUP_SEARCH': LDAPSearch(value, ldap.SCOPE_SUBTREE, '(objectClass=groupOfNames)'),
                'AUTH_LDAP_GROUP_TYPE': GroupOfNamesType()}

    if key == 'USER_SEARCH':
        return {'AUTH_LDAP_USER_SEARCH': LDAPSearch(
            value['SEARCH'],
            ldap.SCOPE_ONELEVEL,
            '({user_field}=%(user)s)'.format(user_field=value['USER_FIELD']))}

    if key == 'GLOBAL_OPTIONS':  # Options for ldap.set_option(). Keys are ldap.OPT_* constants.
        return {'AUTH_LDAP_GLOBAL_OPTIONS': {
            getattr(ldap, opt_name): opt_value for opt_name, opt_value in value.items()}}

    if key == 'USER_FLAGS_BY_GROUP':
        flag_settings = value.copy()
        for flag, groups in value.items():
            if isinstance(groups, str):
                continue

            parsed_groups = _get_ldap_group_query(groups)
            if parsed_groups is None:
                del flag_settings[flag]
            else:
                flag_settings[flag] = parsed_groups

        return {'AUTH_LDAP_USER_FLAGS_BY_GROUP': flag_settings}

    if key == 'REQUIRE_GROUP':
        if isinstance(value, str):
            require_settings = value
        else:
            require_settings = _get_ldap_group_query(value)

        if require_settings is not None:
            return {'AUTH_LDAP_REQUIRE_GROUP': require_settings}
        else:
            return {}

    return {'AUTH_LDAP_' + key: value}


def _get_ldap_group_query(groups):
    """From a list of LDAP simple searches create an LDAPGroupQuery with the items in OR.

    Arguments:
        groups (list): the list of simple LDAP searches to OR.

    Returns:
        django_auth_ldap.config.LDAPGroupQuery: the search object

    """
    if not groups:
        return None

    if len(groups) == 1:
        return groups[0]

    group_query = LDAPGroupQuery(groups[0])
    for group in groups[1:]:
        group_query |= LDAPGroupQuery(group)

    return group_query
