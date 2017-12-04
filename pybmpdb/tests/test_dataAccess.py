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

import numpy as np
import pandas

try:
    import pyodbc
except ImportError:
    pyodbc = None

from pybmpdb import dataAccess as da
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
        {'res': 5., 'DL': 5., 'qual': 'junk'},
    ])
    return df


@pytest.fixture
def db_quals():
    return ['U', 'UJ']


@pytest.fixture
def db_fromcsv():
    dbfile = get_data_file('bmpdata.csv')
    db = da.Database(dbfile, useTex=False)
    return db


@pytest.fixture
def db_fromaccess():
    dbfile = get_data_file('bmpdata.accdb')
    db = da.Database(dbfile, dbtable='bmp_data', useTex=False)
    return db


@pytest.fixture
def expected_parameters():
    parameters = [
        'Cadmium, Dissolved', 'Cadmium, Total',
        'Copper, Dissolved', 'Copper, Total',
        'Lead, Dissolved', 'Lead, Total',
        'Kjeldahl nitrogen (TKN)',
        'Kjeldahl nitrogen, Suspended',
        'Kjeldahl nitrogen, Dissolved',
        'Nitrogen, Nitrate (NO3) as N',
        'Nitrogen, Nitrite (NO2) + Nitrate (NO3) as N',
        'Phosphorus as P, Dissolved',
        'Phosphorus as P, Total',
        'Total suspended solids',
        'Escherichia coli',
    ]
    return parameters


@pytest.fixture
def expected_index_names():
    index_names = [
        'category', 'epazone', 'state', 'site', 'bmp', 'station', 'storm', 'sampletype',
        'watertype', 'paramgroup', 'units', 'parameter', 'fraction', 'initialscreen',
        'wqscreen', 'catscreen', 'balanced', 'bmptype', 'pdf_id', 'site_id', 'bmp_id',
        'sampledatetime'
    ]
    return index_names


def test__handle_ND_factors(df_for_quals):
    expected = np.array([2, 2, 2, 2, 2, 3, 2, 1, 1])
    result = da._handle_ND_factors(df_for_quals)
    nptest.assert_array_equal(result, expected)


def test__handle_ND_qualifiers(df_for_quals):
    result = da._handle_ND_qualifiers(df_for_quals)
    expected = np.array(['ND', 'ND', 'ND', 'ND', 'ND', 'ND', 'ND', '=', '='])
    nptest.assert_array_equal(result, expected)


def test__process_screening():
    df = pandas.DataFrame({
        'screen': ['Yes', 'INC', 'No', 'eXC', 'junk']
    })
    expected = np.array(['yes', 'yes', 'no', 'no', 'invalid'])
    result = da._process_screening(df, 'screen')
    nptest.assert_array_equal(result, expected)


def test__process_sampletype():
    df = pandas.DataFrame({
        'sampletype': ['SRL GraB asdf', 'SeL cOMPositE df', 'jeL LSDR as']
    })
    expected = np.array(['grab', 'composite', 'unknown'])
    result = da._process_sampletype(df, 'sampletype')
    nptest.assert_array_equal(result, expected)


def test__check_levelnames():
    da._check_levelnames(['epazone', 'category'])

    with pytest.raises(ValueError):
        da._check_levelnames(['site', 'junk'])


@pytest.mark.skipif('NO_ACCESS')
def test_db_connection():
    dbfile = get_data_file('bmpdata.accdb')
    try:
        cnn = da.db_connection(dbfile)
        assert isinstance(cnn, pyodbc.Connection)
        cnn.close()
    except:
        raise


@patch.object(da, 'db_connection')
@patch.object(pandas, 'read_sql', return_value=1)
def test_get_data(mock_sql, mock_cnn):
    da.get_data('select * from table', 'test.mdb')
    mock_sql.assert_called_once_with('select * from table', mock_cnn().__enter__())


@patch.object(da, 'get_default_query', return_value='select * from [{}]')
@patch.object(da, 'get_data')
@pytest.mark.parametrize(('sql', 'table', 'expected_sql'), [
    (None, None, 'select * from [bWQ BMP FlatFile BMP Indiv Anal_Rev 10-2014]'),
    ('select * from bmp_data', None, 'select * from bmp_data'),
    (None, 'bmp_data', 'select * from bmp_data'),
    ('select * from bmp_data', 'another_table', 'select * from bmp_data'),
])
def test_load_from_access(get_data, get_dq, sql, table, expected_sql):
    dbfile = 'test.mdb'
    _ = da.load_from_access(dbfile, sqlquery=sql, dbtable=table)
    get_data.assert_called_once_with(
        expected_sql,
        dbfile,
        driver=r'{Microsoft Access Driver (*.mdb, *.accdb)}'
    )


@patch.object(pandas, 'read_csv')
def test_load_from_csv(read_csv):
    da.load_from_csv('bmp.csv')
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
    result = da.transform_parameters(
        df, old_params, new_param, 'ug/L',
        lambda x: 1000 * x['res'].sum(axis=1),
        lambda x: x[('qual', 'B')],
        paramlevel='param'
    )
    pdtest.assert_frame_equal(result, expected)


@patch.object(zipfile.ZipFile, 'extractall')
@patch.object(request, 'urlretrieve')
@patch.object(os.path, 'splitext')
@patch.object(os, 'makedirs')
@patch.object(wqio, 'download')
def test_Database_no_file(mockdl, mockos, mockpath, mockreq, mockzip):
    db = da.Database()
    mockdl.assert_called_once_with('bmpdata')


@pytest.mark.parametrize(('db', 'expected_driver'), [
    (db_fromcsv(), None), pytest.mark.skipif('NO_ACCESS')(
        (db_fromaccess(), r'{Microsoft Access Driver (*.mdb, *.accdb)}')
    ),
])
def test_Database_driver(db, expected_driver):
    assert db.driver == expected_driver


@pytest.mark.parametrize(('db', 'expected'), [
    (db_fromcsv(), False),
    pytest.mark.skipif('NO_ACCESS')((db_fromaccess(), True)),
])
def test_Database_usingdb(db, expected):
    assert db.usingdb == expected


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_file(db):
    assert hasattr(db, 'file')


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_data_attr(db, expected_index_names):
    expected_datashape = (16273, 2)
    assert isinstance(db.data, pandas.DataFrame)
    assert db.data.shape == expected_datashape
    assert isinstance(db.data.index, pandas.MultiIndex)
    assert db.data.index.names == expected_index_names
    assert db.data['res'].min() > 0


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_sqlquery_setter(db):
    new_query = 'test'
    db.sqlquery = new_query
    assert db.sqlquery == new_query


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database__data_raw(db):
    assert isinstance(db._data_raw, pandas.DataFrame)


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database__data_cleaned(db):
    assert isinstance(db._data_cleaned, pandas.DataFrame)


@pytest.mark.parametrize(('db', 'expected'), [
    (db_fromcsv(), None),
    pytest.mark.skipif('NO_ACCESS')((db_fromaccess(), 'bmp_data')),
])
def test_Database_dbtable(db, expected):
    assert db.dbtable == expected
    db.dbtable = 'test'
    assert db.dbtable == 'test'


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
@pytest.mark.parametrize('options', [
    pytest.mark.xfail(raises=ValueError)(dict(junk=False)),
    dict(paramgroup='Metals'),
    dict(parameter='Copper, Total', site='21st and Iris Rain Garden', bmp='UDFCD Rain Garden'),
    dict(parameter=['Copper, Total', 'Lead, Total']),
])
def test_Database_select(db, options):
    data = db.select(**options)
    assert isinstance(data, pandas.DataFrame)
    assert data.index.names == db.data.index.names
    for level, values in options.items():
        nptest.assert_array_equal(
            data.index.get_level_values(level).unique(),
            np.array(values)
        )


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_params(db, expected_parameters):
    for p in db.params:
        assert p in expected_parameters


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_parameters(db):
    for p in db.parameters:
        assert p.name in db.params
        assert isinstance(p, wqio.Parameter)


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_parameter_lookup(db):
    assert isinstance(db.parameter_lookup, dict)
    assert sorted(list(db.parameter_lookup.keys())) == sorted(db.params)


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_index(db, expected_index_names):
    assert len(db.index.keys()) == len(expected_index_names)
    for key in db.index.keys():
        assert key in expected_index_names


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_index_values(db):
    expected_categories = [
        'Grass Swale',
        'Bioretention',
        'Detention Basin',
        'Porous Pavement',
        'Retention Pond',
        'Wetland Basin'
    ]
    bmpcats = db.index_values('category')
    assert sorted(bmpcats) == sorted(expected_categories)


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_index_vals_raises(db):
    with pytest.raises(KeyError):
        db.index_values('JUNK')


@pytest.mark.xfail
def test_Database_transformParameters(db_fromcsv):
    old_params = ['Total suspended solids']
    new_param = 'log_Total suspended solids'
    db_fromcsv.transformParameters(
        old_params, new_param,
        lambda x, old_p: 1000 * x[('res', old_p)],
        lambda x, old_p: x[('qual', old_p)],
        '1000*mg/L'
    )
    assert '1000*mg/L' in db_fromcsv.data.index.get_level_values('units')
    assert new_param in db_fromcsv.parameter_lookup.keys()
    assert new_param in db_fromcsv.data.index.get_level_values('parameter')


@pytest.mark.xfail
def test_Database_unionParamsWithPreference(db_fromcsv):
    components = [
        'Nitrogen, Nitrate (NO3) as N',
        'Nitrogen, Nitrite (NO2) + Nitrate (NO3) as N',
    ]
    combined = 'NOx'
    db_fromcsv.unionParamsWithPreference(components, combined, 'mg/L')
    assert combined in db_fromcsv.parameter_lookup.keys()
    assert combined in db_fromcsv.data.index.get_level_values('parameter')


@pytest.mark.parametrize('dropold', [True, False])
def test_Database_redefineBMPCategory(db_fromcsv, dropold):
    newcat = 'Test New Category'
    oldcat = 'Bioretention'

    bmpcat_index = db_fromcsv.index['category']
    db_fromcsv.redefineBMPCategory(newcat, lambda row: row[bmpcat_index] == oldcat,
                                   dropold=dropold)
    assert newcat in db_fromcsv.data.index.get_level_values('category')
    if dropold:
        assert oldcat not in db_fromcsv.data.index.get_level_values('category')
    else:
        assert oldcat in db_fromcsv.data.index.get_level_values('category')


def test_Database_to_DataCollection(db_fromcsv):
    dc = db_fromcsv.to_DataCollection(dict(state='GA'))
    assert isinstance(dc, wqio.DataCollection)


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database__check_for_parameters(db, expected_parameters):
    assert db._check_for_parameters(expected_parameters)
    assert db._check_for_parameters(expected_parameters[0])
    assert not (db._check_for_parameters(['junk', 'garbage']))


@pytest.mark.skipif('True')
@pytest.mark.parametrize(('db', 'should_raise'), [
    (db_fromcsv(), True),
    pytest.mark.skipif('NO_ACCESS')((db_fromaccess(), False)),
])
def test_Database_dbtable_to_csv(db, should_raise):
    with tempfile.TemporaryDirectory() as tempdir:
        outputfile = os.path.join(tempdir, 'testoutput.csv')
        if should_raise:
            with pytest.raises(NotImplementedError):
                db.dbtable_to_csv('bmpcats', filepath=outputfile)
        else:
            db.dbtable_to_csv('bmpcats', filepath=outputfile)
