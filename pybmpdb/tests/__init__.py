from pkg_resources import resource_filename

import pybmpdb


def test(*args):
    try:
        import pytest
    except ImportError:
        raise ImportError("pytest required run tests")

    options = [resource_filename('pybmpdb', 'tests')]
    options.extend(list(args))
    return pytest.main(options)
