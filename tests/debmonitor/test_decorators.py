import pytest

from debmonitor import decorators


VALID_PARAMETERS = (
    (),
    [],
    ('GET',),
    ['GET'],
    ('GET', 'HEAD'),
    ['GET', 'HEAD'],
)
INVALID_PARAMETERS = (
    None,
    'invalid',
    5,
    {},
)


def test_verify_clients():
    """The decorator should set the custom function property to True."""
    @decorators.verify_clients
    def view(request):
        pass

    assert view.debmonitor_verify_clients


@pytest.mark.parametrize('arg', VALID_PARAMETERS)
def test_verify_clients_params_ok(arg):
    """For all valid parameters, the decorator should set the custom function property to the parameter's value."""
    @decorators.verify_clients(arg)
    def view(request):
        pass

    assert view.debmonitor_verify_clients_methods == arg


@pytest.mark.parametrize('arg', INVALID_PARAMETERS)
def test_verify_clients_params_ko(arg):
    """For all invalid parameters, the decorator should raise RuntimeError."""
    try:  # Manual approach as pytest.raises doesn't catch this
        @decorators.verify_clients(arg)
        def view(request):
            pass
    except RuntimeError as e:
        assert 'Decorator verify_clients parameter must be a list or tuple' in str(e)
    else:
        raise AssertionError('The verify_clients decorator should have raised RuntimeError')
