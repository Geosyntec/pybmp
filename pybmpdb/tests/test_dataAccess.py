import sys
import os
from io import StringIO
from pkg_resources import resource_filename

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
        'category', 'epazone', 'state', 'site', 'bmp', 'station', 'storm',
        'sampletype', 'watertype', 'paramgroup', 'units', 'parameter',
        'fraction', 'initialscreen', 'wqscreen', 'catscreen', 'balanced',
        'PDFID', 'WQID', 'bmptype', 'sampledatetime'
    ]
    return index_names


@pytest.mark.skipif('NO_ACCESS')
def test_db_connection():
    dbfile = get_data_file('bmpdata.accdb')
    try:
        cnn = da.db_connection(dbfile)
        assert isinstance(cnn, pyodbc.Connection)
        cnn.close()
    except:
        raise


@pytest.mark.parametrize(('value', 'expected'), [
    ('Yes', 'yes'),
    ('INC', 'yes'),
    ('No', 'no'),
    ('eXC', 'no'),
    ('junk', None)
])
def test__process_screening(value, expected):
    if expected is None:
        with pytest.raises(ValueError):
            da._process_screening(value)
    else:
        assert da._process_screening(value) == expected


@pytest.mark.parametrize(('value', 'expected'), [
    ('SRjeL GraB asdf', 'grab'),
    ('SRjeL cOMPositE asdf', 'composite'),
    ('SRjeL LSDRsdfljkSdj asdf', 'unknown'),
])
def test__process_sampletype_grab(value, expected):
    assert da._process_sampletype(value) == expected


@pytest.mark.parametrize(('value', 'error'), [
    ('inFLow', None),
    ('OutflOW', None),
    ('rEFErence', NotImplementedError),
    ('subsURFace', NotImplementedError),
    ('junk', ValueError)
])
def test__check_station(value, error):
    if error is not None:
        with pytest.raises(error):
            da._check_station(value)
    else:
        assert da._check_station(value) == value.lower()


def test__check_levelnames():
    da._check_levelnames(['epazone', 'category'])

    with pytest.raises(ValueError):
        da._check_levelnames(['site', 'junk'])


@pytest.mark.parametrize(('row', 'expected'), [
    ({'qual': 'U'}, 2),
    ({'qual': 'UK'}, 2),
    ({'qual': 'UA'}, 2),
    ({'qual': 'UC'}, 2),
    ({'qual': 'K'}, 2),
    ({'res': 5., 'DL': 15., 'qual': 'UJ'}, 3),
    ({'res': 5., 'DL': 10., 'qual': 'UJ'}, 2),
    ({'res': 10., 'DL': 5., 'qual': 'UJ'}, 1),
    ({'res': 5., 'DL': 5., 'qual': 'junk'}, 1),
])
def test__fancy_factors(row, expected):
    result = da._fancy_factors(row)
    assert result == expected


@pytest.mark.parametrize(('row', 'expected'), [
    ({'qual': 'U'}, 'ND'),
    ({'qual': 'UK'}, 'ND'),
    ({'qual': 'UA'}, 'ND'),
    ({'qual': 'UC'}, 'ND'),
    ({'qual': 'K'}, 'ND'),
    ({'res': 5., 'DL': 15., 'qual': 'UJ'}, 'ND'),
    ({'res': 5., 'DL': 10., 'qual': 'UJ'}, 'ND'),
    ({'res': 5., 'DL': 5., 'qual': 'UJ'}, 'ND'),
    ({'res': 10., 'DL': 5., 'qual': 'UJ'}, '='),
    ({'res': 5., 'DL': 5., 'qual': 'junk'}, '='),

])
def test__fancy_quals(row, expected):
    result = da._fancy_quals(row)
    assert result == expected


def test_Database_strip_quals(db_quals):
    df_raw = pandas.DataFrame({
        'res':  [  1,    2,     3,    4,    5,    6,     7,    8],
        'qual': ['U', 'U ', ' U ', None, None, None, ' UJ', 'UJ']
    })

    df_final = pandas.DataFrame({
        'res':  [  1,   2,   3,    4,    5,    6,    7,    8],
        'qual': ['U', 'U', 'U', None, None, None, 'UJ', 'UJ']
    })
    da.Database._strip_quals(df_raw, 'qual')
    pdtest.assert_frame_equal(df_raw, df_final)


def test_Database_apply_res_factors_baseline(db_quals):
    df_raw = pandas.DataFrame({
        'res':  [  1,   2,   3,    4,    5,    6,    7,    8],
        'qual': ['U', 'U', 'U', None, 'AB', None, 'UJ', 'UJ']
    })

    df_final = pandas.DataFrame({
        'res':  [  2,   4,   6,    4,    5,    6,   14,   16],
        'qual': ['U', 'U', 'U', None, 'AB', None, 'UJ', 'UJ']
    })

    da.Database._apply_res_factors(df_raw, 'res', 'qual',
                                   quallist=db_quals, factor=2)
    pdtest.assert_frame_equal(df_raw, df_final)


def test_Database_apply_res_factors_fancy(db_quals):
    df_raw = pandas.DataFrame({
        'res':  [ 1.,  2.,  3.,   4.,   5.,   6.,   7.,   8.],
        'DL':   [ 1.,  2.,  3.,   4.,   5.,   6.,  10.,   8.],
        'qual': ['U', 'U', 'U', None, 'AB', None, 'UJ', 'UJ']
    })

    df_final = pandas.DataFrame({
        'res':  [ 2.,  4.,  6.,   4.,   5.,   6.,  10.,   8.],
        'DL':   [ 1.,  2.,  3.,   4.,   5.,   6.,  10.,   8.],
        'qual': ['U', 'U', 'U', None, 'AB', None, 'UJ', 'UJ']
    })

    def fancy_factors(row):
        if row.qual == 'U':
            return 2
        elif row.qual == 'UJ'and row.res < row.DL:
            return row.DL / row.res
        else:
            return 1

    da.Database._apply_res_factors(df_raw, 'res', 'qual',
                                   userfxn=fancy_factors)
    pdtest.assert_frame_equal(df_raw, df_final)


def test_Database_apply_res_factors_errors(db_quals):
    df = pandas.DataFrame([1, 2, 3])
    with pytest.raises(ValueError):
        da.Database._apply_res_factors(df, 'res', 'qual')

    with pytest.raises(ValueError):
        da.Database._apply_res_factors(df, 'res', 'qual', factor=2)

    with pytest.raises(ValueError):
        da.Database._apply_res_factors(df, 'res', 'qual', factor=2, userfxn=2)


def test_Database_standardize_quals(db_quals):
    df_raw = pandas.DataFrame({
        'res':  [  2,   4,   6,    4,    5,    6,   14,   16],
        'qual': ['U', 'U', 'U', None, None, None, 'UJ', 'UJ']
    })

    df_final = pandas.DataFrame({
        'res':  [   2,    4,    6,   4,   5,   6,   14,   16],
        'qual': ['ND', 'ND', 'ND', '=', '=', '=', 'ND', 'ND']
    })
    da.Database._standardize_quals(df_raw, 'qual', db_quals)
    pdtest.assert_frame_equal(df_raw, df_final)


@pytest.mark.parametrize(('db', 'expected_driver'), [
    (db_fromcsv(), None),
     pytest.mark.skipif('NO_ACCESS')(
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
def test_Database_select_form(db):
    data = db.select(paramgroup='Metals')
    assert isinstance(data, pandas.DataFrame)
    assert data.index.names == db.data.index.names
    nptest.assert_array_equal(
        data.index.get_level_values('paramgroup').unique(),
        np.array(['Metals'])
    )


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
def test_Database_select_raise(db):
    with pytest.raises(ValueError):
        db.select(junk=False)


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_select_single_args(db):
    parameter = 'Copper, Total'
    siteid = '21st and Iris Rain Garden'
    bmpid = 'UDFCD Rain Garden'
    fraction = 'total'
    data = db.select(parameter=parameter, site=siteid, bmp=bmpid)
    assert isinstance(data, pandas.DataFrame)
    assert data.index.get_level_values('parameter').unique()[0] == parameter
    assert data.index.get_level_values('site').unique()[0] == siteid
    assert data.index.get_level_values('bmp').unique()[0] == bmpid

    assert data.index.get_level_values('parameter').unique().shape == (1,)
    assert data.index.get_level_values('site').unique().shape == (1,)
    assert data.index.get_level_values('bmp').unique().shape == (1,)


@pytest.mark.parametrize('db', [
    db_fromcsv(),
    pytest.mark.skipif('NO_ACCESS')(db_fromaccess()),
])
def test_Database_select_list_args(db):
    parameters = ['Copper, Total', 'Lead, Total']
    data = db.select(parameter=parameters)
    assert isinstance(data, pandas.DataFrame)
    nptest.assert_array_equal(data.index.get_level_values('parameter').unique(),
                              np.array(parameters))


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


def test_Database_transformParameters(db_fromcsv):
    old_params = ['Total suspended solids']
    new_param = 'log_' + 'Total suspended solids'
    db_fromcsv.transformParameters(
        old_params, new_param,
        lambda x, old_p: 1000*x[('res', old_p)],
        lambda x, old_p: x[('qual', old_p)],
        '1000*mg/L'
    )
    assert '1000*mg/L' in db_fromcsv.data.index.get_level_values('units')
    assert new_param in db_fromcsv.parameter_lookup.keys()
    assert new_param in db_fromcsv.data.index.get_level_values('parameter')


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
def test_Database_redefineIndexLevel(db_fromcsv, dropold):
    levelname = 'epazone'
    newzone = 9999
    oldzone = 7

    criteria = lambda row: row[1] == oldzone

    db_fromcsv.redefineIndexLevel(levelname, newzone, criteria, dropold=dropold)
    assert newzone in db_fromcsv.data.index.get_level_values(levelname)
    if dropold:
        assert oldzone not in db_fromcsv.data.index.get_level_values(levelname)
    else:
        assert oldzone in db_fromcsv.data.index.get_level_values(levelname)


@pytest.mark.parametrize('dropold', [True, False])
def test_Database_redefineBMPCategory(db_fromcsv, dropold):
    newcat = 'Test New Category'
    oldcat = 'Bioretention'

    bmpcat_index = db_fromcsv.index['category']
    criteria = lambda row: row[bmpcat_index] == oldcat

    db_fromcsv.redefineBMPCategory(newcat, criteria, dropold=dropold)
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
    outputfile = get_data_file('testoutput.csv')
    if should_raise:
        with pytest.raises(NotImplementedError):
            db.dbtable_to_csv('bmpcats', filepath=outputfile)
    else:
        db.dbtable_to_csv('bmpcats', filepath=outputfile)
