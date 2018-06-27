#!/usr/bin/env python
"""Package configuration."""
from setuptools import find_packages, setup


with open('README.rst', 'r') as readme:
    long_description = readme.read()

# Required dependencies
install_requires = [
    'Django>=2.0,<2.1.0a0',
    'django-stronghold==0.3.0',
    'django-csp==3.4',
]

# Extra dependencies
extras_require = {
    'with-mysql': [  # With MySQL support
        'mysqlclient==1.3.12',
    ],
    'with-ldap': [  # With LDAP support
        'django-auth-ldap==1.6.1',
    ],
    'tests': [  # Test dependencies
        'flake8>=3.5.0',
        'pytest>=3.5.0',
        'pytest-cov>=2.5.1',
        'pytest-django>=3.1.2',
        'requests-mock>=1.3.0',
    ],
}
extras_require['with-all'] = extras_require['with-mysql'] + extras_require['with-ldap']

setup_requires = [
    'pytest-runner>=4.2',
    'setuptools_scm>=1.17.0',
]

setup(
    author='Riccardo Coccioli',
    author_email='rcoccioli@wikimedia.org',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.0',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
    ],
    description='Debian packages tracker',
    extras_require=extras_require,
    install_requires=install_requires,
    keywords=['debmonitor', 'apt', 'deb'],
    license='GPLv3+',
    long_description=long_description,
    name='debmonitor',
    packages=find_packages(exclude=['*.tests', '*.tests.*', 'tests.*']),
    platforms=['GNU/Linux', 'MacOSX'],
    setup_requires=setup_requires,
    url='https://github.com/wikimedia/debmonitor',
    use_scm_version=True,
    zip_safe=False,
)
