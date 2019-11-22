from images.apps import ImagesConfig


def test_apps():
    assert ImagesConfig.name == 'images'
