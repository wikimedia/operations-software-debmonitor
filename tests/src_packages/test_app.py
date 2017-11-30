from src_packages.apps import SrcPackagesConfig


def test_apps():
    assert SrcPackagesConfig.name == 'src_packages'
