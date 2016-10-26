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

SKIP_DB = True # pyodbc is None or os.name == 'posix'


def get_data_file(filename):
    return resource_filename("wqio.tests._data", filename)


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


class Test__fancy_factors(object):
    def setup(self):
        self.default_quals = ['U', 'UK', 'UA', 'UC', 'K']

    def test_2(self):
        for dq in self.default_quals:
            assert da._fancy_factors(dict(qual=dq)) == 2.

    def test_uj_small(self):
        row = {'res': 5., 'DL': 15., 'qual': 'UJ'}
        assert da._fancy_factors(row) == 3.

    def test_uj_big(self):
        row = {'res': 10., 'DL': 5., 'qual': 'UJ'}
        assert da._fancy_factors(row) == 1.

    def test_other(self):
        row = {'res': 5., 'DL': 5., 'qual': 'junk'}
        assert da._fancy_factors(row) == 1.


class Test__fancy_quals(object):
    def setup(self):
        self.default_quals =  quals = ['U', 'UA', 'UI', 'UC', 'UK', 'K']

    def test_ND(self):
        for dq in self.default_quals:
            assert da._fancy_quals(dict(qual=dq)), 'ND'

    def test_uj_LT(self):
        row = {'res': 5., 'DL': 15., 'qual': 'UJ'}
        assert da._fancy_quals(row) == 'ND'

    def test_uj_EQ(self):
        row = {'res': 5., 'DL': 5., 'qual': 'UJ'}
        assert da._fancy_quals(row) == 'ND'

    def test_uj_GT(self):
        row = {'res': 15., 'DL': 5., 'qual': 'UJ'}
        assert da._fancy_quals(row) == '='

    def test_other(self):
        row = {'res': 5., 'DL': 5., 'qual': 'junk'}
        assert da._fancy_quals(row) == '='


class Test_DatabaseStaticMethods(object):
    def setup(self):
        self.quals = ['U', 'UJ']
        np.random.seed(0)

    def test__strip_quals(self):
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

    def test__apply_res_factors_baseline(self):
        df_raw = pandas.DataFrame({
            'res':  [  1,   2,   3,    4,    5,    6,    7,    8],
            'qual': ['U', 'U', 'U', None, 'AB', None, 'UJ', 'UJ']
        })

        df_final = pandas.DataFrame({
            'res':  [  2,   4,   6,    4,    5,    6,   14,   16],
            'qual': ['U', 'U', 'U', None, 'AB', None, 'UJ', 'UJ']
        })

        da.Database._apply_res_factors(df_raw, 'res', 'qual',
                                       quallist=self.quals, factor=2)
        pdtest.assert_frame_equal(df_raw, df_final)

    def test__apply_res_factors_fancy(self):
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

    def test__apply_res_factors_errors(self):
        df = pandas.DataFrame([1, 2, 3])
        with pytest.raises(ValueError):
            da.Database._apply_res_factors(df, 'res', 'qual')

        with pytest.raises(ValueError):
            da.Database._apply_res_factors(df, 'res', 'qual', factor=2)

        with pytest.raises(ValueError):
            da.Database._apply_res_factors(df, 'res', 'qual', factor=2, userfxn=2)

    def test__standardize_quals(self):
        df_raw = pandas.DataFrame({
            'res':  [  2,   4,   6,    4,    5,    6,   14,   16],
            'qual': ['U', 'U', 'U', None, None, None, 'UJ', 'UJ']
        })

        df_final = pandas.DataFrame({
            'res':  [   2,    4,    6,   4,   5,   6,   14,   16],
            'qual': ['ND', 'ND', 'ND', '=', '=', '=', 'ND', 'ND']
        })
        da.Database._standardize_quals(df_raw, 'qual', self.quals)
        pdtest.assert_frame_equal(df_raw, df_final)


class _base_database_Mixin(object):
    def mainsetup(self):
        self.known_dbfile = get_data_file('testdata.accdb')
        self.known_csvfile = get_data_file('testdata.csv')
        self.known_top_col_level = ['Inflow', 'Outflow']
        self.known_bottom_col_level = ['DL', 'res', 'qual']
        self.known_col_names = ['station', 'quantity']
        self.known_datashape = (3094, 2)

        self.known_index_names = [
            'category', 'epazone', 'state', 'site', 'bmp', 'station',
            'storm', 'sampletype', 'watertype', 'paramgroup', 'units',
            'parameter', 'wqscreen', 'catscreen',  'balanced', 'PDFID',
            'WQID', 'sampledatetime'
        ]
        self.known_bmpcats = ['BR', 'BS', 'MD']
        self.known_group = 'Metals'

    def test_driver(self):
        assert self.db.driver == self.known_driver

    def test_usingdb(self):
        assert self.db.usingdb == self.known_usingdb

    def test_file(self):
        assert self.db.file == self.known_file

    def test_data_exists(self):
        assert isinstance(self.db.data, pandas.DataFrame)
        assert self.db.data.shape == self.known_datashape

    def test_data_index(self):
        assert isinstance(self.db.data.index, pandas.MultiIndex)
        assert self.db.data.index.names == self.known_index_names

    def test_data_positive(self):
        assert self.db.data['res'].min() > 0

    def test_selectData_exists(self):
        data = self.db.selectData(paramgroup=self.known_group)

    def test_selectData_form(self):
        data = self.db.selectData(paramgroup=self.known_group)
        assert isinstance(data, pandas.DataFrame)
        assert data.index.names, self.known_index_names
        nptest.assert_array_equal(data.index.get_level_values('paramgroup').unique(),
                                  np.array([self.known_group]))

    def test_sqlquery_setter(self):
        new_query = 'test'
        self.db.sqlquery = new_query
        assert self.db.sqlquery == new_query

    def test__data_fromdb(self):
        assert isinstance(self.db._data_fromdb, pandas.DataFrame)

    def test__data_cleaned(self):
        assert isinstance(self.db._data_cleaned, pandas.DataFrame)

    def test_dbtable(self):
        assert self.db.dbtable == None
        self.db.dbtable = 'test'
        assert self.db.dbtable == 'test'

    def test_selectData_raise(self):
        with pytest.raises(ValueError):
            self.db.selectData(junk=False)

    def test_selectData_single_args(self):
        parameter = 'Copper, Total'
        siteid = '21st and Iris Rain Garden'
        bmpid = 'UDFCD Rain Garden'
        data = self.db.selectData(parameter=parameter, site=siteid, bmp=bmpid)
        assert isinstance(data, pandas.DataFrame)
        assert data.index.get_level_values('parameter').unique()[0] == parameter
        assert data.index.get_level_values('site').unique()[0] == siteid
        assert data.index.get_level_values('bmp').unique()[0] == bmpid

        assert data.index.get_level_values('parameter').unique().shape == (1,)
        assert data.index.get_level_values('site').unique().shape == (1,)
        assert data.index.get_level_values('bmp').unique().shape == (1,)

    def test_selectData_list_args(self):
        parameters = [
            u'Copper, Total',
            u'Copper, Dissolved',
        ]
        data = self.db.selectData(parameter=parameters)
        assert isinstance(data, pandas.DataFrame)
        nptest.assert_array_equal(data.index.get_level_values('parameter').unique(),
                                  np.array(parameters))

    def test_selectData_table(self):
        parameters = [
            u'Copper, Total',
            u'Copper, Dissolved',
        ]
        table = self.db.selectData(astable=True, parameter=parameters)
        assert isinstance(table, da.Table)
        nptest.assert_array_equal(table.data.index.get_level_values('parameter').unique(),
                                  np.array(parameters))


@pytest.mark.skipif(SKIP_DB, reason='No viable DB')
class Test_DatabaseFromDB(_base_database_Mixin):
    def setup(self):
        self.mainsetup()
        self.known_driver = r'{Microsoft Access Driver (*.mdb, *.accdb)}'
        self.known_bmpcatsrc = 'bmpcats'
        self.known_usingdb = True
        self.known_file = self.known_dbfile
        self.known_catScreen = False
        self.db = da.Database(self.known_dbfile)

    def test_connect(self):
        if self.db.usingdb:
            with self.db.connect() as cnn:
                assert isinstance(cnn, pyodbc.Connection)

    def test_connect_GoodQuery(self):
        cmd = "select 5 as N"
        try:
            cnn = self.db.connect(cmd=cmd)
        finally:
            cnn.close()

    def test_connect_BadQuery(self):
        cmd = "JUNKJUNKJUNK"
        with pytest.raises(pyodbc.ProgrammingError):
            self.db.connect(cmd=cmd)

    def test_file(self):
        assert self.db.file == self.known_dbfile

    @pytest.mark.skipif(True, reason='not implmented')
    def test_convertTableToCSV(self):
        outputfile = get_data_file('testoutput.csv')
        self.db.convertTableToCSV('bmpcats', filepath=outputfile)


class Test_DatabaseFromCSV(_base_database_Mixin):
    usingdb = False
    def setup(self):
        self.mainsetup()
        self.known_driver = None
        self.known_usingdb = False
        self.known_file = self.known_csvfile
        self.known_bmpcatsrc = get_data_file('testbmpcats.csv')
        self.known_excludeGrabs = False
        self.known_catScreen = True
        self.db = da.Database(self.known_csvfile)

    def test_connect_CSVError(self):
        with pytest.raises(ValueError):
            cmd = "select 5 as N"
            cnn = self.db.connect(cmd=cmd)

    def test_convertTableToCSV(self):
        with pytest.raises(NotImplementedError):
            outputfile = get_data_file('testoutput.csv')
            self.db.convertTableToCSV('bmpcats', filepath=outputfile)

    def test_file(self):
        assert self.db.file == self.known_csvfile


class _base_tableMixin(object):
    def mainsetup(self):
        self.known_data_columns = pandas.MultiIndex.from_tuples([
            (u'Inflow', u'res'),
            (u'Inflow', u'qual'),
            (u'Inflow', u'DL'),
            (u'Outflow', u'res'),
            (u'Outflow', u'qual'),
            (u'Outflow', u'DL')
        ])
        self.known_data_columns_pairs = pandas.MultiIndex.from_tuples([
            (u'Inflow', u'res'),
            (u'Inflow', u'qual'),
            (u'Inflow', u'DL'),
            (u'Outflow', u'res'),
            (u'Outflow', u'qual'),
            (u'Outflow', u'DL'),
            ('diff', ''),
            ('logdiff', '')
        ])
        self.known_csvfile = get_data_file('testdata.csv')
        self.known_bmpcatsrc = get_data_file('testbmpcats.csv')
        self.known_index_names = [
            'category', 'epazone', 'state', 'site','bmp', 'station',
            'storm', 'sampletype', 'watertype', 'paramgroup', 'units',
            'parameter', 'wqscreen', 'catscreen', 'balanced', 'PDFID',
            'WQID', 'sampledatetime',
        ]
        self.known_getData_row_index_names = [
            'epazone', 'state', 'site', 'bmp', 'storm',
            'sampletype', 'paramgroup', 'units', 'wqscreen', 'catscreen'
        ]
        self.known_loc_subkeys_category = ['location', 'definition', 'name']
        self.known_loc_subkeys_siteid = ['location', 'definition', 'name']
        self.known_ds_subkeys_category = ['category', 'parameter']
        self.known_ds_subkeys_siteid = ['category', 'site', 'parameter']

    def test_name(self):
        assert self.table.name == self.known_name

    def test_data(self):
        assert isinstance(self.table.data, pandas.DataFrame)

    def test_data_row_index(self):
        assert isinstance(self.table.data.index, pandas.MultiIndex)
        assert self.table.data.index.names == self.known_index_names

    def test_parameters(self):
        for p in self.table.parameters:
            assert p.name in self.known_parameters
            assert isinstance(p, wqio.Parameter)

    def test_parameter_lookup(self):
        assert isinstance(self.table.parameter_lookup, dict)
        assert sorted(list(self.table.parameter_lookup.keys())) == sorted(self.known_parameters)

    def test_index(self):
        assert len(self.table.index.keys()) == len(self.known_index_names)
        for key in self.table.index.keys():
            assert key in self.known_index_names

    def test_index_values(self):
        bmpcats = self.table.index_values('category')
        assert sorted(bmpcats) == sorted(self.known_bmp_cats)

    def test_index_vals_raises(self):
        with pytest.raises(KeyError):
            self.table.index_values('JUNK')

    def test_getData_NonPaired_Exists(self):
        with pytest.raises(NotImplementedError):
            data = self.table.getData(self.known_parameters[0],
                                      self.known_bmp_cats[0],
                                      paired=False)
            assert isinstance(data, pandas.DataFrame)

    def test_getData_NonPaired_Form(self):
        with pytest.raises(NotImplementedError):
            data = self.table.getData(self.known_parameters[0],
                                      self.known_bmp_cats[0],
                                      paired=False)
            assert data.columns.tolist() == self.known_data_columns.tolist()
            assert data.index.names == self.known_getData_row_index_names

    def test_getData_Paired_Exists(self):
        with pytest.raises(NotImplementedError):
            data = self.table.getData(self.known_parameters[0],
                                      self.known_bmp_cats[0],
                                      paired=True)
            assert isinstance(data, pandas.DataFrame)

    def test_getData_Paired_Form(self):
        with pytest.raises(NotImplementedError):
            data = self.table.getData(self.known_parameters[0],
                                      self.known_bmp_cats[0],
                                      paired=True)
            assert data.columns.tolist() == self.known_data_columns_pairs.tolist()
            assert data.index.names == self.known_getData_row_index_names

    def test_getData_ParameterError(self):
        with pytest.raises(NotImplementedError):
            data = self.table.getData('JUNK',
                                      self.known_bmp_cats[0],
                                      paired=False)

    def test_getData_BMPCatError(self):
        with pytest.raises(NotImplementedError):
            data = self.table.getData(self.known_parameters[0],
                                      'JUNK',
                                      paired=True)

    def test_transformParameters(self):
        old_params = [self.known_parameters[-1]]
        new_param = 'log_' + self.known_parameters[-1]
        self.table.transformParameters(
            old_params, new_param,
            lambda x, old_p: 1000*x[('res', old_p)],
            lambda x, old_p: x[('qual', old_p)],
            '1000*mg/L'
        )
        assert '1000*mg/L' in self.table.data.index.get_level_values('units')
        assert new_param in self.table.parameter_lookup.keys()
        assert new_param in self.table.data.index.get_level_values('parameter')

    def test_unionParamsWithPreference(self):
        components = self.known_parameters[-2:]
        combined = 'New Combination'
        self.table.unionParamsWithPreference(components, combined, 'mg/L')
        assert combined in self.table.parameter_lookup.keys()
        assert combined in self.table.data.index.get_level_values('parameter')

    def test_getLocations_exists(self):
        locations = self.table.getLocations('inflow')
        assert isinstance(locations, list)
        for loc in locations:
            assert isinstance(loc['definition']['parameter'], wqio.Parameter)
            assert isinstance(loc['location'], wqio.Location)

    def test_getLocations_form_category(self):
        locations = self.table.getLocations('inflow', 'category')
        for locdict in locations:
            for key in list(locdict.keys()):
                assert key in self.known_loc_subkeys_category

    def test_getLocations_form_siteid(self):
        locations = self.table.getLocations('inflow', 'category', 'site')
        for locdict in locations:
            for key in list(locdict.keys()):
                assert key in self.known_loc_subkeys_siteid

    def test_getLocations_form_raises_badIndex(self):
        with pytest.raises(ValueError):
            locations = self.table.getLocations('inflow', 'storm')

    def test_getLocations_form_raises_badStation(self):
        with pytest.raises(ValueError):
            locations = self.table.getLocations('JUNK')

    def test_getDatasets_exists(self):
        datasets = self.table.getDatasets()
        assert isinstance(datasets, list)
        for ds in datasets:
            assert isinstance(ds, wqio.Dataset)

    def test_getDatasets_form_default(self):
        datasets = self.table.getDatasets()
        for ds in datasets:
            assert sorted(['parameter']) == sorted(list(ds.definition.keys()))
            assert isinstance(ds.definition['parameter'], wqio.Parameter)

    def test_getDatasets_form_category(self):
        datasets = self.table.getDatasets('category')
        for ds in datasets:
            assert sorted(self.known_ds_subkeys_category) == sorted(list(ds.definition.keys()))

    def test_getDatasets_form_siteid_and_category(self):
        datasets = self.table.getDatasets('category', 'site')
        for ds in datasets:
            assert sorted(self.known_ds_subkeys_siteid) == sorted(list(ds.definition.keys()))

    def test_getDatasets_form_raises(self):
        with pytest.raises(ValueError):
            datasets = self.table.getDatasets('storm')

    def test_redefineIndexLevel_DropOldTrue(self):
        levelname = 'epazone'
        newzone = 9999
        oldzone = 2

        criteria = lambda row: row[1] == oldzone

        self.table.redefineIndexLevel(levelname, newzone, criteria, dropold=True)
        assert newzone in self.table.data.index.get_level_values(levelname)
        assert oldzone not in self.table.data.index.get_level_values(levelname)

    def test_redefineIndexLevel_DropOldFalse(self):
        levelname = 'epazone'
        newzone = 9999
        oldzone = 2

        criteria = lambda row: row[1] == oldzone

        self.table.redefineIndexLevel(levelname, newzone, criteria, dropold=False)
        assert newzone in self.table.data.index.get_level_values(levelname)
        assert oldzone in self.table.data.index.get_level_values(levelname)

    def test_redefineBMPCategory_DropOldTrue(self):
        newcat = 'Test New Category'
        oldcat = self.known_bmp_cats[-1]

        bmpcat_index = self.table.index['category']
        criteria = lambda row: row[bmpcat_index] == oldcat

        self.table.redefineBMPCategory(newcat, criteria, dropold=True)
        assert newcat in self.table.data.index.get_level_values('category')
        assert oldcat not in self.table.data.index.get_level_values('category')

    def test_redefineBMPCategory_DropOldFalse(self):
        newcat = 'Test New Category'
        oldcat = self.known_bmp_cats[-1]

        bmpcat_index = self.table.index['category']
        criteria = lambda row: row[bmpcat_index] == oldcat

        self.table.redefineBMPCategory(newcat, criteria, dropold=False)
        assert newcat in self.table.data.index.get_level_values('category')
        assert oldcat in self.table.data.index.get_level_values('category')

    def test_to_DataCollection(self):
        dc = self.table.to_DataCollection()
        assert isinstance(dc, wqio.DataCollection)

    def test__check_for_parameters(self):
        assert self.table._check_for_parameters(self.known_parameters)
        assert self.table._check_for_parameters(self.known_parameters[0])
        assert not (self.table._check_for_parameters(['junk', 'garbage']))


class Test_table_metals(_base_tableMixin):
    def setup(self):
        self.mainsetup()
        self.known_bmp_cats = [
            'Biofilter - Grass Swale',
            'Biofilter - Grass Strip',
            'Bioretention',
            'Detention Basin'
        ]
        self.known_name = 'Metals'
        self.known_parameters = [
            'Cadmium, Dissolved', 'Cadmium, Total',
            'Copper, Total', 'Copper, Dissolved',
        ]
        self.db = da.Database(self.known_csvfile)
        self.known_parametername = self.known_parameters[0]
        self.known_bmpcat_code = self.known_bmp_cats[1]
        self.table = self.db.selectData(
            paramgroup=self.known_name,
            astable=True,
            name=self.known_name
        )
        self.known_influent_diff = 6
        self.known_effluent_diff = 16


class _base_parameterMixin(object):
    def mainsetup(self):
        self.known_name = 'Copper, Total'
        self.known_tex = 'Total Copper'
        self.known_std_units = 'ug/L'
        self.known_units = r'\si[per-mode=symbol]{\micro\gram\per\liter}'

    def test_name(self):
        assert self.parameter.name == self.known_name

    def test_tex(self):
        assert self.parameter.tex == self.known_tex

    def test_units(self):
        assert self.parameter.units == self.known_units

    def test_std_units(self):
        assert self.parameter.std_units == self.known_std_units

    def test_paramunit(self):
        result = self.parameter.paramunit(usetex=True, usecomma=self.usecomma)
        assert result == self.known_paramunits


class Test_param(_base_parameterMixin):
    def setup(self):
        self.mainsetup()
        self.usecomma = False
        self.parameter = da.Parameter(self.known_name)
        self.known_paramunits = r'Total Copper (\si[per-mode=symbol]{\micro\gram\per\liter})'


class Test_param_usecomma(_base_parameterMixin):
    def setup(self):
        self.mainsetup()
        self.usecomma = True
        self.parameter = da.Parameter(self.known_name)
        self.known_paramunits = r'Total Copper, \si[per-mode=symbol]{\micro\gram\per\liter}'
