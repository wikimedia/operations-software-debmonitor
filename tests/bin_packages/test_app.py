from bin_packages.apps import BinPackagesConfig


def test_apps():
    assert BinPackagesConfig.name == 'bin_packages'
