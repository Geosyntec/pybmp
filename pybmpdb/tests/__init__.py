from pkg_resources import resource_filename

import pytest

import pybmpdb

def test(*args):
    options = [resource_filename('pybmpdb', 'tests')]
    options.extend(list(args))
    return pytest.main(options)