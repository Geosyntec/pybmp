import pytest
from wqio.tests import helpers
from unittest.mock import patch

from pybmpdb import info


@pytest.mark.parametrize(('value', 'expected', 'error'), [
    ('ug/L', {"name": "ug/L", "factor": 1}, None),
    ('mg/L', None, ValueError),
    ('MPN/100 mL', None, ValueError),
])
def test__find_by_name(value, expected, error):
    source = [
        {"name": "MPN/100 mL", "factor": 1},
        {"name": "MPN/100 mL", "factor": 1},
        {"name": "ug/L", "factor": 1},
    ]
    with helpers.raises(error):
        result = info._find_by_name(value, source)
        assert result == expected


@patch.object(info, 'units')
@patch.object(info, 'parameters')
@patch.object(info, '_find_by_name', return_value={'name': 'Lead', 'units': 'mg/L'})
def test_getUnitsFromParam(_find_by_name, parameters, units):
    assert info.getUnitsFromParam('Lead') == 'Lead'
    _find_by_name.assert_any_call('mg/L', units)
    _find_by_name.assert_any_call('Lead', parameters)


@patch.object(info, 'units')
@patch.object(info, '_find_by_name')
def test_getUnits(_find_by_name, units):
    _ = info.getUnits('mg/L')
    _find_by_name.assert_called_once_with('mg/L', units)


@patch.object(info, 'units')
@patch.object(info, '_find_by_name', return_value={'factor': 10})
@pytest.mark.parametrize(('value', 'expected'), [
    (None, 1),
    ('mg/L', 10)
])
def test_getNormalization(_find_by_name, units, value, expected):
    result = info.getNormalization(value)
    assert result == expected
    if value:
        _find_by_name.assert_called_once_with(value, units)


@patch.object(info, 'parameters')
@patch.object(info, 'getNormalization')
@patch.object(info, '_find_by_name', return_value={'units': 'mg/L'})
def test_getConversion(_find_by_name, getNormalization, parameters):
    result = info.getConversion('Lead')
    _find_by_name.assert_called_once_with('Lead', parameters)
    getNormalization.assert_called_once_with('mg/L')
