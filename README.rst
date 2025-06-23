DebMonitor - Debian packages tracker
------------------------------------

DebMonitor is a Django-based web application that allows to track Debian packages installed across a fleet of hosts,
along with their pending software/security updates.

It provides also a standalone command line script (CLI) that, when distributed in the target hosts, allows to
automatically update DebMonitor's database using APT and DPKG hooks.


Target configuration
^^^^^^^^^^^^^^^^^^^^

To automate the tracking of the packages in the target hosts, follow these steps:

* Deploy the Debmonitor client installing the ``debmonitor-client`` Debian package.
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
  It is also required to run DebMonitor in full mode at least once to track all the packages.

See all the available options of the CLI with the ``-h/--help`` option.

Database configuration
^^^^^^^^^^^^^^^^^^^^^^

debmonitor uses a custom Django database backend (``debmonitor.mysql``), which requires the following settings to be
added to the MySQL/Mariadb configuration under the ``[mysqld]`` section along with a restart of the database server:

.. code-block:: ini

  innodb_file_per_table = 1
  innodb_file_format    = barracuda
  innodb_large_prefix   = 1


The following steps are needed to create the database and the debmonitor DB user:

.. code-block:: sql

  CREATE DATABASE debmonitor;
  CREATE USER debmonitor@localhost IDENTIFIED by 'SecretPassword';
  GRANT ALL PRIVILEGES ON debmonitor.* TO debmonitor@localhost;
  FLUSH PRIVILEGES;

Proxy hosts
^^^^^^^^^^^

By default data submissions for host package data is validated against
the CN of the submitting host. There might be situations where that
cannot be applied, e.g. if you have a central orchestration setup
which also updates the Debmonitor data. You can whitelist hosts for
arbitrary host data submissions/deletions using the ``PROXY_HOSTS``
config setting, it accepts a list of FQDNs.

If container images are also being tracked, support for enabling
submissions from e.g. the container build host can be configured using
the similar ``PROXY_IMAGES`` setting.


CAS authentication
^^^^^^^^^^^^^^^^^^

debmonitor supports optional authentication via Apereo CAS. The IDP
login URL needs to be configured via a configuration option in the
``CAS`` block of the the config.json config file:

.. code-block:: ini

  "CAS": {
     "CAS_SERVER_URL": "https://idp.wikimedia.org/idp"
   }

If access for debmonitor is to be restricted to a subset of users
managed by Apereo CAS it needs to be restricted within the CAS service
definition by means of an ``accessStrategy`` setting.

CAS support is implemented via django-cas-ng.

By default CAS protocol version 2 is used (as the default in
django-cas-ng), you can set the protocol version using the CAS_VERSION
option (possible values ``1``, ``2``, ``3`` or ``CAS_2_SAML_1.0``).

By default users are created in the database after successful CAS
authentication, this can be disabled by setting ``CAS_CREATE_USER`` to
``FALSE``.
