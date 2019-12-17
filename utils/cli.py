#!/usr/bin/env python
# ----------------------------------------------------------------------------
# DebMonitor CLI - Debian packages tracker CLI
# Copyright (C) 2017-2018  Riccardo Coccioli <rcoccioli@wikimedia.org>
#                          Wikimedia Foundation, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
"""
DebMonitor CLI - Debian packages tracker CLI.

Automatically collect the current status of all installed and upgradable packages and report it to a DebMonitor server.
It can report all installed and upgradable packages, just the upgradable ones, or the changes reported by a Dpkg hook.

This script was tested with Python 2.7, 3.4, 3.5, 3.6.

* Install the following Debian packages dependencies, choosing either the Python2 or the Python3 variant based on which
  version of Python will be used to run this script:

  * python-apt
  * python-requests

* Deploy this standalone CLI script across the fleet, for example into ``/usr/local/bin/debmonitor``, and make it
  executable, optionally modifying the shebang to force a specific Python version. The script can also be downloaded
  directly from a DebMonitor server via its ``/client`` endpoint.
* Optionally add a configuration file in ``/etc/debmonitor.conf`` (or in a different one passing the
  ``--config /path/to/config`` CLI argument) to avoid to pass the common options to the CLI. See the example file in
  ``doc/examples/client.conf``.
* Add a configuration file in ``/etc/apt/apt.conf.d/`` with the following content, assuming that the ``server`` option
  was set in the configuration file.

  .. code-block:: none

    # Tell dpkg to use version 3 of the protocol for the Pre-Install-Pkgs hook (version 2 is also supported)
    Dpkg::Tools::options::/usr/local/bin/debmonitor::Version "3";
    # Set the dpkg hook to call DebMonitor for any change with the -g/--dpkg option to read the changes from stdin
    Dpkg::Pre-Install-Pkgs {"/usr/local/bin/debmonitor -s ##DEMBONITOR_SERVER## -g || true";};
    # Set the APT update hook to call DebMonitor with the -u/upgradable option to send only the pending upgrades
    APT::Update::Post-Invoke {"/usr/local/bin/debmonitor -s ##DEMBONITOR_SERVER## -u || true"};

* Set a daily or weekly crontab that executes DebMonitor to send the list of all installed and upgradable packages
  (do not set the ``-g`` or ``-u`` options). It is used as a reconciliation method if any of the hook would fail.
  It is also required to run DebMonitor in full mode at least once to track all the packages. Optionally set the
  ``--update`` option so that the script will automatically check for available updates and will overwrite itself with
  the latest version available on the DebMonitor server.

"""
from __future__ import print_function

import argparse
import hashlib
import json
import logging
import os
import platform
import socket
import sys

from collections import namedtuple

try:
    from configparser import ConfigParser, Error as ConfigParserError
except ImportError:  # pragma: py3 no cover - Backward compatibility with Python 2.7
    # This except block is not actually covered by tests because the 3rd party test dependency module 'pytest-cov'
    # has as a dependency the 3rd party module 'configparser' that exposes on Python 2 the stdlib module 'ConfigParser'
    # as 'configparser', not allowing the tests to actually enter this block.
    from ConfigParser import SafeConfigParser as ConfigParser, Error as ConfigParserError

try:
    from json.decoder import JSONDecodeError
except ImportError:  # pragma: py3 no cover - Backward compatibility with Python 2.7
    JSONDecodeError = ValueError

import apt
import requests


# The client version is based on the server's major.minor version plus a dedicated client-specific incremental number.
__version__ = '0.2client1'

SUPPORTED_API_VERSIONS = ('v1',)
CLIENT_VERSION_HEADER = 'X-Debmonitor-Client-Version'
CLIENT_CHECKSUM_HEADER = 'X-Debmonitor-Client-Checksum'
OS_RELEASE_FILE = '/etc/os-release'
logger = logging.getLogger('debmonitor')
AptLineV2 = namedtuple('LineV2', ['name', 'version_from', 'direction', 'version_to', 'action'])
AptLineV3 = namedtuple('LineV3', ['name', 'version_from', 'arch_from', 'multiarch_from', 'direction', 'version_to',
                                  'arch_to', 'multiarch_to', 'action'])

logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


class AptInstalledFilter(apt.cache.Filter):
    """Filter class for python-apt to filter only installed packages."""

    def apply(self, pkg):
        """Filter only installed packages.

        :Parameters:
            according to parent `apply` method.

        Returns:
            bool: True if the package is installed, False otherwise.
        """
        if pkg.is_installed:
            return True

        return False


def get_packages(upgradable_only=False):
    """Return the list of installed and upgradable packages, or only the upgradable ones.

    Arguments:
        upgradable_only (bool, optional): whether to return only the upgradable packages.

    Returns:
        dict: a dictionary of lists with the installed and upgradable packages.
    """
    packages = {'installed': [], 'upgradable': [], 'uninstalled': []}
    cache = apt.cache.FilteredCache()
    cache.set_filter(AptInstalledFilter())
    logger.info('Found %d installed binary packages', len(cache))

    cache.upgrade(dist_upgrade=True)
    upgrades = cache.get_changes()
    logger.info('Found %d upgradable binary packages (including new dependencies)', len(upgrades))

    if not upgradable_only:
        for pkg in cache:
            package = {'name': pkg.name, 'version': pkg.installed.version, 'source': pkg.installed.source_name}
            packages['installed'].append(package)
            logger.debug('Collected installed: %s', package)

    for pkg in upgrades:
        if not pkg.is_installed:
            continue

        upgrade = {'name': pkg.name, 'version_from': pkg.installed.version, 'version_to': pkg.candidate.version,
                   'source': pkg.candidate.source_name}
        packages['upgradable'].append(upgrade)
        logger.debug('Collected upgrade: %s', upgrade)

    return packages


def parse_dpkg_hook(input_lines):
    """Parse packages changes as reported by the Dpkg::Pre-Install-Pkgs hook.

    Arguments:
        input_lines (list): list of strings with the Dpkg::Pre-Install-Pkgs hook output.

    Returns:
        dict: a dictionary of lists with the installed and uninstalled packages.

    Raises:
        RuntimeError: if the version of the Dpkg::Pre-Install-Pkgs hook protocol is not supported or unable to
            determine its version.

    """
    hook_version_line = input_lines.pop(0).strip()

    if not hook_version_line.startswith('VERSION '):
        raise RuntimeError('Expected VERSION line to be the first one, got: {ver}'.format(ver=hook_version_line))

    hook_version = int(hook_version_line[-1])
    if hook_version not in (2, 3):
        raise RuntimeError('Unsupported version {ver}'.format(ver=hook_version))

    try:
        upgrades = input_lines[input_lines.index('\n') + 1:]
    except ValueError:
        raise RuntimeError('Unable to find the empty line separator in input')

    if not upgrades:
        return {}

    packages = {'installed': [], 'upgradable': [], 'uninstalled': []}
    cache = apt.cache.Cache()
    for update_line in upgrades:
        group, package = parse_apt_line(update_line, cache, version=hook_version)
        if group is not None:
            packages[group].append(package)

    logger.info('Got %d updates from dpkg hook version %d', len(packages['installed']) + len(packages['uninstalled']),
                hook_version)

    return packages


def parse_apt_line(update_line, cache, version=3):
    """Parse a single package line as reported by the Dpkg::Pre-Install-Pkgs hook version 3 or 2.

    - Protocol version 2 examples
      - Installation
        package-name - < 1.0.0-1 /var/cache/apt/archives/package-name_1.0.0-1_all.deb
        package-name - < 1.0.0-1 **CONFIGURE**

      - Re-installation
        package-name 1.0.0-1 = 1.0.0-1 /var/cache/apt/archives/package-name_1.0.0-1_all.deb
        package-name 1.0.0-1 = 1.0.0-1 **CONFIGURE**

      - Upgrade
        package-name 1.0.0-1 < 1.0.0-2 /var/cache/apt/archives/package-name_1.0.0-2_all.deb
        package-name 1.0.0-1 < 1.0.0-2 **CONFIGURE**

      - Downgrade
        package-name 1.0.0-2 > 1.0.0-1 /var/cache/apt/archives/package_name_.1.0.0-1_all.deb
        package-name 1.0.0-2 > 1.0.0-1 **CONFIGURE**

      - Removal
        package-name 1.0.0-1 > - **REMOVE**

    - Protocol version 3 examples
      - Installation
        package-name - - none < 1.0.0-1 all none /var/cache/apt/archives/package-name_1.0.0-1_all.deb
        package-name - - none < 1.0.0-1 all none **CONFIGURE**

      - Re-installation
        package-name 1.0.0-1 all none = 1.0.0-1 all none /var/cache/apt/archives/package-name_1.0.0-1_all.deb
        package-name 1.0.0-1 all none = 1.0.0-1 all none **CONFIGURE**

      - Upgrade
        package-name 1.0.0-1 all none < 1.0.0-2 all none /var/cache/apt/archives/package-name_1.0.0-2_all.deb
        package-name 1.0.0-1 all none < 1.0.0-2 all none **CONFIGURE**

      - Downgrade
        package-name 1.0.0-2 all none > 1.0.0-1 all none /var/cache/apt/archives/package_name_.1.0.0-1_all.deb
        package-name 1.0.0-2 all none > 1.0.0-1 all none **CONFIGURE**

      - Removal
        package-name 1.0.0-2 all none > - - none **REMOVE**

    Arguments:
        update_line (str): one line of the Dpkg::Pre-Install-Pkgs hook output.
        cache (apt.cache.Cache): a `apt.cache.Cache` instance to gather additional metadata of the modified packages.
        version (int, optional): the Dpkg::Pre-Install-Pkgs hook protocol version. Supported versions are: 2, 3.

    Returns:
        tuple: a tuple (str, dict) with the name of the group the package belongs to and the dictionary with the
            package metadata. The group is one of 'installed', 'uninstalled'.

    Raises:
        RuntimeError: if the version of the Dpkg::Pre-Install-Pkgs hook protocol is not supported.

    """
    if version == 3:
        line = AptLineV3(*update_line.strip().split(' ', 9))
    elif version == 2:
        line = AptLineV2(*update_line.strip().split(' ', 5))
    else:
        raise RuntimeError('Unsupported version {ver}'.format(ver=version))

    if line.action in ('**CONFIGURE**'):  # Skip those lines, package already tracked
        return None, None

    cache_item = cache[line.name]
    if line.direction == '<':  # Upgrade
        group = 'installed'
        package = {'name': line.name, 'version': line.version_to, 'source': cache_item.candidate.source_name}

        if line.version_from == '-':
            action = 'installed'
        else:
            action = 'upgraded'
        logger.debug('Collected %s package: %s', action, package)

    elif line.direction == '>':  # Downgrade/removal
        if line.version_to == '-':  # Removal
            group = 'uninstalled'
            package = {'name': line.name, 'version': line.version_from, 'source': cache_item.installed.source_name}
            logger.debug('Collected removed package: %s', package)
        else:  # Downgrade
            group = 'installed'
            package = {'name': line.name, 'version': line.version_to, 'source': cache_item.candidate.source_name}
            logger.debug('Collected downgraded package: %s', package)

    else:  # No change (=)
        group = None
        package = None

    return group, package


def self_update(base_url, cert, verify):
    """Check if the DebMonitor server has a different version of this script and automatically self-overwrite it.

    Arguments:
        base_url (str): the base URL of the DebMonitor server.
        cert (str, tuple, None): a client certificate as required by the requests library.
        verify (bool, str): to be passed to requests calls for server side certificate validation. Either a boolean or
            a string with the path to a CA bundle.

    Raises:
        requests.exceptions.RequestException: on error to check the version and get the new script.
        EnvironmentError: if unable to overwrite itself.
        RuntimeError: if no remote version is found or there is a checksum mismatch or a wrong HTTP status code.
    """
    client_url = '{base_url}/client'.format(base_url=base_url)
    response = requests.head(client_url, cert=cert, verify=verify)
    if response.status_code != requests.status_codes.codes.ok:
        raise RuntimeError('Unable to check remote script version, got HTTP {retcode}, expected 200 OK.'.format(
            retcode=response.status_code))

    version = response.headers.get(CLIENT_VERSION_HEADER)
    if version is None:
        raise RuntimeError('No header {header} value found, unable to check remote version of the script.'.format(
            header=CLIENT_VERSION_HEADER))

    if version == __version__:
        logger.debug('The current script version is the correct one, no update needed.')
        return

    logger.info('Found new remote version %s, current version is %s. Updating.', version, __version__)
    response = requests.get(client_url, cert=cert, verify=verify)
    if response.status_code != requests.status_codes.codes.ok:
        raise RuntimeError('Unable to download remote script, got HTTP {retcode}, expected 200 OK.'.format(
            retcode=response.status_code))

    checksum = hashlib.sha256(response.content).hexdigest()
    if response.headers.get(CLIENT_CHECKSUM_HEADER) != checksum:
        raise RuntimeError('The checksum of the script do not match the HTTP header: {checksum} != {header}'.format(
            checksum=checksum, header=response.headers.get(CLIENT_CHECKSUM_HEADER)))

    with open(os.path.realpath(__file__), mode='w') as script_file:
        script_file.write(response.text)

    logger.info('Successfully self-updated DebMonitor CLI to version %s', version)


def get_distro_name():
    """Return the Linux distribution name, uppercase first character."""
    os = 'unknown'
    try:
        with open(OS_RELEASE_FILE, mode='r') as os_file:
            for line in os_file.readlines():
                if line.startswith('ID='):
                    osname = line.split('=', 1)[1].strip()
                    os = osname[0].upper() + osname[1:]
                    break
    except (IOError, IndexError):
        pass  # Explicitely ignored exception, os is already set to unknown.

    return os


def parse_args(argv):
    """Parse command line arguments.

    Arguments:
        argv (list): list of strings with the CLI parameters to parse.

    Returns:
        argparse.Namespace: the parsed CLI parameters.

    Raises:
        SystemExit: if there are missing required parameters or an invalid combination of parameters is used.

    """
    conf_parser = argparse.ArgumentParser(add_help=False)
    conf_parser.add_argument(
        '--config', default='/etc/debmonitor.conf',
        help=('Configuration file for the DebMonitor CLI script to provide default values without having to pass them '
              'as CLI arguments. If not present, rely only on CLI arguments. CLI argument always override '
              'configuration file values. [default: /etc/debmonitor.conf]'))

    # Parse the configuration file only for now
    args, remaining_argv = conf_parser.parse_known_args(argv)

    # Read the configuration file, if any. ConfigParser doesn't fail if the file do not exists or is not readable.
    config = ConfigParser()
    try:
        config.read(args.config)
    except ConfigParserError as e:
        conf_parser.error('Unable to parse configuration file {name}: {msg}'.format(name=args.config, msg=e))

    def json_file_type(path):
        """Open a file and parse its content as JSON."""
        fp = argparse.FileType()(path)
        try:
            return json.load(fp)
        except JSONDecodeError as e:
            raise argparse.ArgumentTypeError("Failed to load JSON file '{path}': {e}".format(path=path, e=e))

    # Add remaining CLI options
    parser = argparse.ArgumentParser(
        prog='debmonitor-client', description='DebMonitor CLI - Debian packages tracker CLI', epilog=__doc__,
        parents=[conf_parser], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-s', '--server', help='DebMonitor server DNS name, required unless -n/--dry-run is set.')
    parser.add_argument('-p', '--port', default=443, type=int,
                        help='Port in which the DebMonitor server is listening. [default: 443]')
    parser.add_argument('-i', '--image-name',
                        help='Instead of submitting host entries, record the package state of a container image'
                             'This parameter specifies the image name and enables the image mode')
    parser.add_argument('-f', '--image-file', type=json_file_type,
                        help='Load the container package data to submit from a pre-dumped JSON file.')
    parser.add_argument('-c', '--cert',
                        help=('Path to the client SSL certificate to use for sending the update. If it does not '
                              'contain also the private key, -k/--key must be specified too.'))
    parser.add_argument('-k', '--key',
                        help=('Path to the client SSH private key to use for sending the update. If not specified, '
                              'the private key is expected to be found in the certificate defined by -c/--cert.'))
    parser.add_argument('--ca',
                        help=('Path to a CA bundle to use to verify the DebMonitor server certificate. Mandatory when '
                              '--update is set.'))
    parser.add_argument('-a', '--api', help='Version of the API to use. [default: v1]', default='v1',
                        choices=SUPPORTED_API_VERSIONS)
    parser.add_argument('-u', '--upgradable', action='store_true',
                        help='Send only the list of upgradable packages. Can be used as a hook for apt-get update.')
    parser.add_argument('-g', '--dpkg-hook', action='store_true',
                        help=('Parse modified packages from stdin according to DPKG hook Dpkg::Pre-Install-Pkgs '
                              'format for version 3 and 2.'))
    parser.add_argument('-n', '--dry-run', action='store_true',
                        help='Do not send the report to a DebMonitor server, rather print the package data to stdout '
                             'in JSON format. This can be useful to generate container information in a build '
                             'environment which does not have direct access to a DebMonitor server.')
    parser.add_argument('--update', action='store_true',
                        help=('Self-update DebMonitor CLI script if there is a new version available on the '
                              'DebMonitor server. The script will execute with the current version.'))
    parser.add_argument('-d', '--debug', action="store_true", help='Set logging level to DEBUG')
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    # Initialize the default values with those from the configuration file.
    parser.set_defaults(config=args.config, **config.defaults())
    args = parser.parse_args(remaining_argv)

    if not args.server and not args.dry_run:
        parser.error('argument -s/--server is required unless -n/--dry-run is set')

    if args.key is not None and args.cert is None:
        parser.error('argument -c/--cert is required when -k/--key is set')

    if args.upgradable and args.dpkg_hook:
        parser.error('argument -u/--upgradable and -g/--dpkg-hook are mutually exclusive')

    if args.update and args.ca is None:
        parser.error('argument --ca is required when --update is set')

    args.verify = True
    if args.ca is not None:
        args.verify = args.ca

    return args


def generate_payload(args, input_lines=None):
    """Collect the list of packages and generate the payload to send to the DebMonitor server.

    There are three ways of submitting package data:
    1. From a host submitting to a debmonitor server (default if no option is passed otherwise.
    2. From a running container image to a debmonitor server (enabled via --image_name option (but can also be used
       to only dump the state by also adding the --dry-run option.
    3. Submitting pregenerated package data in JSON format (enabled via --image_file).

    Arguments:
        args (argparse.Namespace): the parsed CLI parameters.
        input_lines (list, optional): the lines passed to stdin via the dpkg_hook.

    Returns:
        dict: the payload dictionary.

    """
    if args.image_file:
        return args.image_file

    if args.dpkg_hook:
        update_type = 'dpkg_hook'
    elif args.upgradable:
        update_type = 'upgradable'
    else:
        update_type = 'full'

    if args.dpkg_hook:
        packages = parse_dpkg_hook(input_lines)
    else:
        packages = get_packages(upgradable_only=args.upgradable)

    payload = {
        'api_version': args.api,
        'os': get_distro_name(),
        'installed': packages['installed'],
        'uninstalled': packages['uninstalled'],
        'upgradable': packages['upgradable'],
        'update_type': update_type,
    }

    if args.image_name:
        payload['image_name'] = args.image_name
    else:
        payload['hostname'] = socket.getfqdn()
        payload['running_kernel'] = {
            'release': platform.release(),
            'version': platform.version(),
        }

    return payload


def run(args, input_lines=None):
    """Collect the list of packages and send the update to the DebMonitor server.

    Arguments:
        args (argparse.Namespace): the parsed CLI parameters.
        input_lines (list, optional): the lines passed to stdin via the dpkg_hook.

    Raises:
        RuntimeError, requests.exceptions.RequestException: on error.

    """
    base_url = 'https://{server}:{port}'.format(server=args.server, port=args.port)

    payload = generate_payload(args, input_lines)
    if args.dry_run:
        print(json.dumps(payload, sort_keys=True, indent=4))
        return

    if args.image_file is not None:
        url = '{base_url}/images/{name}/update'.format(base_url=base_url, name=payload['image_name'])
    elif args.image_name is not None:
        url = '{base_url}/images/{name}/update'.format(base_url=base_url, name=args.image_name)
    else:
        url = '{base_url}/hosts/{host}/update'.format(base_url=base_url, host=payload['hostname'])

    cert = None
    if args.key is not None:
        cert = (args.cert, args.key)
    elif args.cert is not None:
        cert = args.cert

    response = requests.post(url, cert=cert, json=payload, verify=args.verify)
    if response.status_code != requests.status_codes.codes.created:
        raise RuntimeError('Failed to send the update to the DebMonitor server: {status} {body}'.format(
            status=response.status_code, body=response.text))
    logger.info('Successfully sent the %s update to the DebMonitor server', payload['update_type'])

    if args.update:
        try:
            self_update(base_url, cert, args.verify)
        except Exception as e:
            logger.error('Unable to self-update this script: %s', e)


def main(args, input_lines=None):
    """Run the DebMonitor CLI.

    Arguments:
        args (argparse.Namespace): the parsed CLI parameters.
        input_lines (list, optional): input lines from stdin when the -g/--dpkg-hook option is set.

    Returns:
        int: the exit code of the operation. Zero on success, a positive integer on failure.
    """
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    logging.basicConfig(level=level)

    try:
        run(args, input_lines=input_lines)
        exit_code = 0
    except Exception as e:
        exit_code = 1
        message = 'Failed to execute DebMonitor CLI: '
        if args.debug:
            logger.exception(message)
        else:
            logger.error(message + str(e))

    return exit_code


if __name__ == '__main__':  # pragma: no cover
    args = parse_args(sys.argv[1:])
    input_lines = None
    if args.dpkg_hook:
        input_lines = sys.stdin.readlines()

    sys.exit(main(args, input_lines=input_lines))
