import sys
import os
from io import StringIO
from pkg_resources import resource_filename
import tempfile
import zipfile
from urllib import request

from unittest.mock import patch
import pytest
import numpy.testing as nptest
import pandas.util.testing as pdtest

import numpy
import pandas

try:
    import pyodbc
except ImportError:
    pyodbc = None

from pybmpdb import bmpdb
import wqio


def get_data_file(filename):
    return resource_filename("pybmpdb.tests._data", filename)


_no_access_file = not os.path.exists(get_data_file('bmpdata.accdb'))
NO_ACCESS = (pyodbc is None) or (os.name == 'posix') or _no_access_file


@pytest.fixture
def df_for_quals():
    df = pandas.DataFrame([
        {'res': 1, 'DL': 2, 'qual': 'U'},
        {'res': 1, 'DL': 2, 'qual': 'UK'},
        {'res': 1, 'DL': 2, 'qual': 'UA'},
        {'res': 1, 'DL': 2, 'qual': 'UC'},
        {'res': 1, 'DL': 2, 'qual': 'K'},
        {'res': 5., 'DL': 15., 'qual': 'UJ'},
        {'res': 5., 'DL': 10., 'qual': 'UJ'},
        {'res': 10., 'DL': 5., 'qual': 'UJ'},
        {'res': 10., 'DL': 10., 'qual': 'UJ'},
        {'res': 5., 'DL': 5., 'qual': 'junk'},
    ])
    return df


def test__handle_ND_factors(df_for_quals):
    expected = numpy.array([2, 2, 2, 2, 2, 3, 2, 1, 1, 1])
    result = bmpdb._handle_ND_factors(df_for_quals)
    nptest.assert_array_equal(result, expected)


def test__handle_ND_qualifiers(df_for_quals):
    result = bmpdb._handle_ND_qualifiers(df_for_quals)
    expected = numpy.array(['ND', 'ND', 'ND', 'ND', 'ND', 'ND', 'ND', '=', 'ND', '='])
    nptest.assert_array_equal(result, expected)


def test__process_screening():
    df = pandas.DataFrame({
        'screen': ['Yes', 'INC', 'No', 'eXC', 'junk']
    })
    expected = numpy.array(['yes', 'yes', 'no', 'no', 'invalid'])
    result = bmpdb._process_screening(df, 'screen')
    nptest.assert_array_equal(result, expected)


def test__process_sampletype():
    df = pandas.DataFrame({
        'sampletype': ['SRL GraB asdf', 'SeL cOMPositE df', 'jeL LSDR as']
    })
    expected = numpy.array(['grab', 'composite', 'unknown'])
    result = bmpdb._process_sampletype(df, 'sampletype')
    nptest.assert_array_equal(result, expected)


def test__check_levelnames():
    bmpdb._check_levelnames(['epazone', 'category'])

    with pytest.raises(ValueError):
        bmpdb._check_levelnames(['site', 'junk'])


@pytest.mark.skipif('NO_ACCESS')
def test_db_connection():
    dbfile = get_data_file('bmpdata.accdb')
    try:
        cnn = bmpdb.db_connection(dbfile)
        assert isinstance(cnn, pyodbc.Connection)
        cnn.close()
    except:
        raise


@patch.object(bmpdb, 'db_connection')
@patch.object(pandas, 'read_sql', return_value=1)
def test_get_data(mock_sql, mock_cnn):
    bmpdb.get_data('select * from table', 'test.mdb')
    mock_sql.assert_called_once_with('select * from table', mock_cnn().__enter__())


@patch.object(bmpdb, 'get_default_query', return_value='select * from [{}]')
@patch.object(bmpdb, 'get_data')
@pytest.mark.parametrize(('sql', 'table', 'expected_sql'), [
    (None, None, 'select * from [bWQ BMP FlatFile BMP Indiv Anal_Rev 10-2014]'),
    ('select * from bmp_data', None, 'select * from bmp_data'),
    (None, 'bmp_data', 'select * from bmp_data'),
    ('select * from bmp_data', 'another_table', 'select * from bmp_data'),
])
def test_load_from_access(get_data, get_dq, sql, table, expected_sql):
    dbfile = 'test.mdb'
    _ = bmpdb.load_from_access(dbfile, sqlquery=sql, dbtable=table)
    get_data.assert_called_once_with(
        expected_sql,
        dbfile,
        driver=r'{Microsoft Access Driver (*.mdb, *.accdb)}'
    )


@patch.object(pandas, 'read_csv')
def test_load_from_csv(read_csv):
    bmpdb.load_from_csv('bmp.csv')
    read_csv.assert_called_once_with('bmp.csv', parse_dates=['sampledate'], encoding='utf-8')


@pytest.mark.skipif(True, reason='test not ready')
def test_prepare_data():
    pass


def test_transform_parameters():
    index_cols = ['storm', 'param', 'units']
    df = pandas.DataFrame({
        'storm': [1, 1, 2, 2, 3, 3],
        'param': list('ABABAB'),
        'units': ['mg/L'] * 6,
        'res': [1, 2, 3, 4, 5, 6],
        'qual': ['<', '='] * 3,
    }).set_index(index_cols)

    expected = pandas.DataFrame({
        'storm': [1, 1, 2, 2, 3, 3, 1, 2, 3],
        'param': list('ABABABCCC'),
        'units': (['mg/L'] * 6) + (['ug/L'] * 3),
        'res': [1, 2, 3, 4, 5, 6, 3000, 7000, 11000],
        'qual': (['<', '='] * 3) + (['='] * 3),
    }).set_index(index_cols)

    old_params = ['A', 'B']
    new_param = 'C'
    result = bmpdb.transform_parameters(
        df, old_params, new_param, 'ug/L',
        lambda x: 1000 * x['res'].sum(axis=1),
        lambda x: x[('qual', 'B')],
        paramlevel='param'
    )
    pdtest.assert_frame_equal(result, expected)
