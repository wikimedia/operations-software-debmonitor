DebMonitor - Debian packages tracker
------------------------------------

DebMonitor is a Django-based web application that allows to track Debian packages installed across a fleet of hosts,
along with their pending software/security updates.

It provides also a standalone command line script (CLI) that, when distributed in the target hosts, allows to
automatically update DebMonitor's database using APT and DPKG hooks.


Target configuration
^^^^^^^^^^^^^^^^^^^^

To automate the tracking of the packages in the target hosts, follow these steps:

* Deploy the standlone CLI script provided in ``utils/cli.py`` across the fleet, for example into
  ``/usr/local/bin/debmonitor``, and make it executable, optionally modifying the shebang to force a specific Python
  version. The script can also be downloaded directly from a DebMonitor server via its ``/client`` endpoint.
* Optionally add a configuration file in ``/etc/debmonitor.conf`` (or in a different one passing the
  ``--config /path/to/config`` CLI argument) to avoid to pass the common options to the CLI. See the example file in
  ``doc/examples/client.conf``.
* Add a configuration file in ``/etc/apt/apt.conf.d/`` with the following content, assuming that the ``server`` option
  was set in the configuration file.

  .. code-block:: none

    # Tell dpkg to use version 3 of the protocol for the Pre-Install-Pkgs hook (version 2 is also supported)
    Dpkg::Tools::options::/usr/local/bin/debmonitor::Version "3";
    # Set the dpkg hook to call DebMonitor for any change with the -g/--dpkg option to read the changes from stdin
    Dpkg::Pre-Install-Pkgs {"/usr/local/bin/debmonitor -g || true";};
    # Set the APT update hook to call DebMonitor with the -u/upgradable option to send only the pending upgrades
    APT::Update::Post-Invoke {"/usr/local/bin/debmonitor -u || true"};

* Set a daily or weekly crontab that executes DebMonitor to send the list of all installed and upgradable packages
  (do not set the ``-g`` or ``-u`` options). It is used as a reconciliation method if any of the hook would fail.
  It is also required to run DebMonitor in full mode at least once to track all the packages. Optionally set the
  ``--update`` option so that the script will automatically check for available updates and will overwrite itself with
  the latest version available on the DebMonitor server.

See all the available options of the CLI with the ``-h/--help`` option.

Database configuration
^^^^^^^^^^^^^^^^^^^^^^

debmonitor uses a custom Django database backend (debmonitor.mysql),
which requires the following settings to be added to the MySQL/Mariadb
configuration under [mysqld] along with a restart of the database server:

innodb_file_per_table = 1
innodb_file_format    = barracuda
innodb_large_prefix   = 1


The following steps are needed to create the database and the
debmonitor DB user:

CREATE DATABASE debmonitor;
CREATE USER debmonitor@localhost IDENTIFIED by 'SecretPassword';
GRANT ALL PRIVILEGES ON debmonitor.* TO debmonitor@localhost;
FLUSH PRIVILEGES;
