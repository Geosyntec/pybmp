import sys
import os
from pkg_resources import resource_filename

from six import StringIO
import nose
from nose.tools import *
import numpy as np
import numpy.testing as nptest

import pandas
import pandas.util.testing as pdtest

try:
    import pyodbc
except ImportError:
    pyodbc = None

from pybmp import dataAccess as da
from wqio.core import features

skip_db = pyodbc is None or os.name == 'posix'

@nottest
def get_data_file(filename):
    return resource_filename("wqio.data", filename)


def test__process_screening_yes():
    assert_equal('yes', da._process_screening('Yes'))
    assert_equal('yes', da._process_screening('INC'))


def test__process_screening_no():
    assert_equal('no', da._process_screening('No'))
    assert_equal('no', da._process_screening('eXC'))


@raises(ValueError)
def test__process_screening_raiese():
    da._process_screening('JUNK')


def test__process_sampletype_grab():
    assert_equal(da._process_sampletype('SRjeL GraB asdf'), 'grab')


def test__process_sampletype_composite():
    assert_equal(da._process_sampletype('SRjeL cOMPositE asdf'), 'composite')


def test__process_sampletype_unknown():
    assert_equal(da._process_sampletype('SRjeL LSDRsdfljkSdj asdf'), 'unknown')


class test__check_station(object):
    def test_noraise_inflow(self):
        da._check_station('inflow')

    def test_noraise_outflow(self):
        da._check_station('outflow')

    @raises(NotImplementedError)
    def test_notimpl_ref(self):
        da._check_station('reference')

    @raises(NotImplementedError)
    def test_notimpl_ref(self):
        da._check_station('subsurface')

    @raises(ValueError)
    def test_normal_raise(self):
        da._check_station('junk')


class test__check_levelnames(object):
    def test_good(self):
        da._check_levelnames(['epazone', 'category'])

    @raises(ValueError)
    def test_bad(self):
        da._check_station(['site', 'junk'])


class test__fancy_factors(object):
    def setup(self):
        self.default_quals = ['U', 'UK', 'UA', 'UC', 'K']

    def test_2(self):
        for dq in self.default_quals:
            assert_equal(da._fancy_factors(dict(qual=dq)), 2.)

    def test_uj_small(self):
        row = {'res': 5., 'DL': 15., 'qual': 'UJ'}
        assert_equal(da._fancy_factors(row), 3.)

    def test_uj_big(self):
        row = {'res': 10., 'DL': 5., 'qual': 'UJ'}
        assert_equal(da._fancy_factors(row), 1.)

    def test_other(self):
        row = {'res': 5., 'DL': 5., 'qual': 'junk'}
        assert_equal(da._fancy_factors(row), 1.)


class test__fancy_quals(object):
    def setup(self):
        self.default_quals =  quals = ['U', 'UA', 'UI', 'UC', 'UK', 'K']

    def test_ND(self):
        for dq in self.default_quals:
            assert_equal(da._fancy_quals(dict(qual=dq)), 'ND')

    def test_uj_LT(self):
        row = {'res': 5., 'DL': 15., 'qual': 'UJ'}
        assert_equal(da._fancy_quals(row), 'ND')

    def test_uj_EQ(self):
        row = {'res': 5., 'DL': 5., 'qual': 'UJ'}
        assert_equal(da._fancy_quals(row), 'ND')

    def test_uj_GT(self):
        row = {'res': 15., 'DL': 5., 'qual': 'UJ'}
        assert_equal(da._fancy_quals(row), '=')

    def test_other(self):
        row = {'res': 5., 'DL': 5., 'qual': 'junk'}
        assert_equal(da._fancy_quals(row), '=')


class test_DatabaseStaticMethods(object):
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
        assert_raises(
            ValueError,
            da.Database._apply_res_factors,
            df, 'res', 'qual',
        )

        assert_raises(
            ValueError,
            da.Database._apply_res_factors,
            df, 'res', 'qual', factor=2
        )

        assert_raises(
            ValueError,
            da.Database._apply_res_factors,
            df, 'res', 'qual', factor=2, userfxn=2,
        )

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
    @nottest
    def mainsetup(self):
        self.known_dbfile = get_data_file('testdata.accdb')
        self.known_csvfile = get_data_file('testdata.csv')
        self.known_top_col_level = ['Inflow', 'Outflow']
        self.known_bottom_col_level = ['DL', 'res', 'qual']
        self.known_col_names = ['station', 'quantity']
        self.known_datashape = (3094, 3)

        self.known_index_names = [
            'category', 'epazone', 'state', 'site', 'bmp', 'station', 'storm',
            'sampletype', 'watertype', 'paramgroup', 'units', 'parameter',
            'wqscreen', 'catscreen',  'balanced', 'PDFID', 'WQID'
        ]
        self.known_bmpcats = ['BR', 'BS', 'MD']
        self.known_group = 'Metals'

    #@nptest.dec.skipif(skip_db)
    def test_driver(self):
        assert_true(hasattr(self.db, 'driver'))
        assert_equal(self.db.driver, self.known_driver)

    #@nptest.dec.skipif(skip_db)
    def test_usingdb(self):
        assert_true(hasattr(self.db, 'usingdb'))
        assert_equal(self.db.usingdb, self.known_usingdb)

    #@nptest.dec.skipif(skip_db)
    def test_file(self):
        assert_true(hasattr(self.db, 'file'))
        assert_equal(self.db.file, self.known_file)

    #@nptest.dec.skipif(skip_db)
    def test_data_exists(self):
        assert_true(hasattr(self.db, 'data'))
        assert_true(isinstance(self.db.data, pandas.DataFrame))
        assert_tuple_equal(self.db.data.shape, self.known_datashape)

    #@nptest.dec.skipif(skip_db)
    def test_data_index(self):
        assert_true(isinstance(self.db.data.index, pandas.MultiIndex))
        assert_equal(self.db.data.index.names, self.known_index_names)

    #@nptest.dec.skipif(skip_db)
    def test_data_positive(self):
        assert_true(self.db.data['res'].min() > 0)

    #@nptest.dec.skipif(skip_db)
    def test_selectData_exists(self):
        assert_true(hasattr(self.db, 'selectData'))
        data = self.db.selectData(paramgroup=self.known_group)

    #@nptest.dec.skipif(skip_db)
    def test_selectData_form(self):
        data = self.db.selectData(paramgroup=self.known_group)
        assert_true(isinstance(data, pandas.DataFrame))
        assert_true(data.index.names, self.known_index_names)
       # assert_list_equal(self.db.data.columns.names, self.known_col_names)
        nptest.assert_array_equal(data.index.get_level_values('paramgroup').unique(),
                          np.array([self.known_group]))

    def test_sqlquery_setter(self):
        assert_true(hasattr(self.db, 'sqlquery'))
        new_query = 'test'
        self.db.sqlquery = new_query
        assert_equal(self.db.sqlquery, new_query)

    def test__data_fromdb(self):
        assert_true(hasattr(self.db, '_data_fromdb'))
        assert_true(isinstance(self.db._data_fromdb, pandas.DataFrame))

    def test__data_cleaned(self):
        assert_true(hasattr(self.db, '_data_cleaned'))
        assert_true(isinstance(self.db._data_cleaned, pandas.DataFrame))

    def test_dbtable(self):
        assert_true(hasattr(self.db, 'dbtable'))
        assert_equal(self.db.dbtable, None)
        self.db.dbtable = 'test'
        assert_equal(self.db.dbtable, 'test')

    @raises(ValueError)
    #@nptest.dec.skipif(skip_db)
    def test_selectData_raise(self):
        self.db.selectData(junk=False)

    #@nptest.dec.skipif(skip_db)
    def test_selectData_single_args(self):
        parameter = 'Copper, Total'
        siteid = '21st and Iris Rain Garden'
        bmpid = 'UDFCD Rain Garden'
        data = self.db.selectData(parameter=parameter, site=siteid, bmp=bmpid)
        assert_true(isinstance(data, pandas.DataFrame))
        assert_equal(data.index.get_level_values('parameter').unique()[0],
                     parameter)
        assert_equal(data.index.get_level_values('site').unique()[0],
                     siteid)
        assert_equal(data.index.get_level_values('bmp').unique()[0],
                     bmpid)

        assert_tuple_equal(data.index.get_level_values('parameter').unique().shape, (1,))
        assert_tuple_equal(data.index.get_level_values('site').unique().shape, (1,))
        assert_tuple_equal(data.index.get_level_values('bmp').unique().shape, (1,))

    #@nptest.dec.skipif(skip_db)
    def test_selectData_list_args(self):
        parameters = [
            u'Copper, Total',
            u'Copper, Dissolved',
        ]
        data = self.db.selectData(parameter=parameters)
        assert_true(isinstance(data, pandas.DataFrame))
        nptest.assert_array_equal(data.index.get_level_values('parameter').unique(),
                          np.array(parameters))

    #@nptest.dec.skipif(skip_db)
    def test_selectData_table(self):
        parameters = [
            u'Copper, Total',
            u'Copper, Dissolved',
        ]
        table = self.db.selectData(astable=True, parameter=parameters)
        assert_true(isinstance(table, da.Table))
        nptest.assert_array_equal(table.data.index.get_level_values('parameter').unique(),
                          np.array(parameters))


class test_DatabaseFromDB(_base_database_Mixin):
    @nptest.dec.skipif(skip_db)
    def setup(self):
        self.mainsetup()
        self.known_driver = r'{Microsoft Access Driver (*.mdb, *.accdb)}'
        self.known_bmpcatsrc = 'bmpcats'
        self.known_usingdb = True
        self.known_file = self.known_dbfile
        self.known_catScreen = False
        self.db = da.Database(self.known_dbfile)

    @nptest.dec.skipif(skip_db)
    def test_connect(self):
        assert_true(hasattr(self.db, 'connect'))
        if self.db.usingdb:
            with self.db.connect() as cnn:
                assert_true(isinstance(cnn, pyodbc.Connection))

    @nptest.dec.skipif(skip_db)
    def test_connect_GoodQuery(self):
        cmd = "select 5 as N"
        try:
            cnn = self.db.connect(cmd=cmd)
        finally:
            cnn.close()

    @nptest.dec.skipif(skip_db)
    def test_connect_BadQuery(self):
        cmd = "JUNKJUNKJUNK"
        assert_raises(self.db.connect(cmd=cmd), pyodbc.ProgrammingError)

    @nptest.dec.skipif(skip_db)
    def test_file(self):
        assert_true(hasattr(self.db, 'file'))
        assert_equal(self.db.file, self.known_dbfile)

    @nptest.dec.skipif(True)
    def test_convertTableToCSV(self):
        assert_true(hasattr(self.db, 'convertTableToCSV'))
        outputfile = get_data_file('testoutput.csv')
        self.db.convertTableToCSV('bmpcats', filepath=outputfile)


class test_DatabaseFromCSV(_base_database_Mixin):
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

    @raises(ValueError)
    def test_connect_CSVError(self):
        cmd = "select 5 as N"
        cnn = self.db.connect(cmd=cmd)

    @raises(NotImplementedError)
    def test_convertTableToCSV(self):
        assert_true(hasattr(self.db, 'convertTableToCSV'))
        outputfile = get_data_file('testoutput.csv')
        self.db.convertTableToCSV('bmpcats', filepath=outputfile)

    def test_file(self):
        assert_true(hasattr(self.db, 'file'))
        assert_equal(self.db.file, self.known_csvfile)


class _base_tableMixin(object):
    @nottest
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
            'category', 'epazone', 'state', 'site','bmp', 'station', 'storm',
            'sampletype', 'watertype', 'paramgroup', 'units', 'parameter',
            'wqscreen', 'catscreen', 'balanced', 'PDFID', 'WQID'
        ]
        self.known_getData_row_index_names = [
            'epazone', 'state', 'site', 'bmp', 'storm',
            'sampletype', 'paramgroup', 'units', 'wqscreen', 'catscreen'
        ]
        self.known_loc_subkeys_category = ['location', 'definition', 'name']
        self.known_loc_subkeys_siteid = ['location', 'definition', 'name']
        self.known_ds_subkeys_category = ['category', 'parameter']
        self.known_ds_subkeys_siteid = ['category', 'site', 'parameter']
        pass

    def test_name(self):
        assert_true(hasattr(self.table, 'name'))
        assert_equal(self.table.name, self.known_name)

    def test_data(self):
        assert_true(hasattr(self.table, 'data'))
        assert_true(isinstance(self.table.data, pandas.DataFrame))

    def test_data_row_index(self):
        assert_true(hasattr(self.table, 'data'))
        assert_true(isinstance(self.table.data.index, pandas.MultiIndex))
        assert_list_equal(self.table.data.index.names, self.known_index_names)

    def test_parameters(self):
        assert_true(hasattr(self.table, 'parameters'))
        for p in self.table.parameters:
            assert_true(p.name in self.known_parameters)
            assert_true(isinstance(p, features.Parameter))

    def test_parameter_lookup(self):
        assert_true(hasattr(self.table, 'parameter_lookup'))
        assert_true(isinstance(self.table.parameter_lookup, dict))
        assert_list_equal(sorted(list(self.table.parameter_lookup.keys())), sorted(self.known_parameters))

    def test_index(self):
        assert_true(hasattr(self.table, 'index'))
        assert_equal(len(self.table.index.keys()), len(self.known_index_names))
        for key in self.table.index.keys():
            assert_true(key in self.known_index_names)

    def test_index_values(self):
        assert_true(hasattr(self.table, 'index_values'))
        bmpcats = self.table.index_values('category')
        assert_equal(len(bmpcats), len(self.known_bmp_cats))
        assert_list_equal(sorted(bmpcats), sorted(self.known_bmp_cats))
        #for c in bmpcats:
        #    assert_true(c in self.known_bmp_cats)

    @raises
    def test_index_vals_raises(self):
        assert_true(hasattr(self.table, 'index_values'))
        self.table.index_values('JUNK')

    @raises(NotImplementedError)
    def test_getData_NonPaired_Exists(self):
        assert_true(hasattr(self.table, 'getData'))
        data = self.table.getData(self.known_parameters[0],
                                  self.known_bmp_cats[0],
                                  paired=False)
        assert_true(isinstance(data, pandas.DataFrame))

    @raises(NotImplementedError)
    def test_getData_NonPaired_Form(self):
        data = self.table.getData(self.known_parameters[0],
                                  self.known_bmp_cats[0],
                                  paired=False)
        assert_list_equal(data.columns.tolist(), self.known_data_columns.tolist())
        assert_list_equal(data.index.names, self.known_getData_row_index_names)

    @raises(NotImplementedError)
    def test_getData_Paired_Exists(self):
        assert_true(hasattr(self.table, 'getData'))
        data = self.table.getData(self.known_parameters[0],
                                  self.known_bmp_cats[0],
                                  paired=True)
        assert_true(isinstance(data, pandas.DataFrame))

    @raises(NotImplementedError)
    def test_getData_Paired_Form(self):
        data = self.table.getData(self.known_parameters[0],
                                  self.known_bmp_cats[0],
                                  paired=True)
        assert_list_equal(data.columns.tolist(), self.known_data_columns_pairs.tolist())
        assert_list_equal(data.index.names, self.known_getData_row_index_names)

    @raises(NotImplementedError)
    def test_getData_ParameterError(self):
        data = self.table.getData('JUNK',
                                  self.known_bmp_cats[0],
                                  paired=False)

    @raises(NotImplementedError)
    def test_getData_BMPCatError(self):
        data = self.table.getData(self.known_parameters[0],
                                  'JUNK',
                                  paired=True)

    def test_transformParameters(self):
        assert_true(hasattr(self.table, 'transformParameters'))
        old_params = [self.known_parameters[-1]]
        new_param = 'log_' + self.known_parameters[-1]
        self.table.transformParameters(
            old_params, new_param,
            lambda x, old_p: 1000*x[('res', old_p)],
            lambda x, old_p: x[('qual', old_p)],
            '1000*mg/L'
        )
        assert_true('1000*mg/L' in self.table.data.index.get_level_values('units'))
        assert_true(new_param in self.table.parameter_lookup.keys())
        assert_true(new_param in self.table.data.index.get_level_values('parameter'))

    def test_unionParamsWithPreference(self):
        assert_true(hasattr(self.table, 'unionParamsWithPreference'))
        components = self.known_parameters[-2:]
        combined = 'New Combination'
        self.table.unionParamsWithPreference(components, combined, 'mg/L')
        assert_true(combined in self.table.parameter_lookup.keys())
        assert_true(combined in self.table.data.index.get_level_values('parameter'))

    def test_getLocations_exists(self):
        assert_true(hasattr(self.table, 'getLocations'))
        locations = self.table.getLocations('inflow')
        assert_true(isinstance(locations, list))
        for loc in locations:
            assert_true(isinstance(loc['definition']['parameter'], features.Parameter))
            assert_true(isinstance(loc['location'], features.Location))

    def test_getLocations_form_category(self):
        assert_true(hasattr(self.table, 'getLocations'))
        locations = self.table.getLocations('inflow', 'category')
        for locdict in locations:
            for key in list(locdict.keys()):
                assert_true(key in self.known_loc_subkeys_category)

    def test_getLocations_form_siteid(self):
        assert_true(hasattr(self.table, 'getLocations'))
        locations = self.table.getLocations('inflow', 'category', 'site')
        for locdict in locations:
            for key in list(locdict.keys()):
                assert_true(key in self.known_loc_subkeys_siteid)

    @raises(ValueError)
    def test_getLocations_form_raises_badIndex(self):
        assert_true(hasattr(self.table, 'getLocations'))
        locations = self.table.getLocations('inflow', 'storm')

    @raises(ValueError)
    def test_getLocations_form_raises_badStation(self):
        assert_true(hasattr(self.table, 'getLocations'))
        locations = self.table.getLocations('JUNK')

    def test_getDatasets_exists(self):
        assert_true(hasattr(self.table, 'getDatasets'))
        datasets = self.table.getDatasets()
        assert_true(isinstance(datasets, list))
        for ds in datasets:
            assert_true(isinstance(ds, features.Dataset))

    def test_getDatasets_form_default(self):
        assert_true(hasattr(self.table, 'getDatasets'))
        datasets = self.table.getDatasets()
        for ds in datasets:
            assert_list_equal(sorted(['parameter']), sorted(list(ds.definition.keys())))
            assert_true(isinstance(ds.definition['parameter'], features.Parameter))

    def test_getDatasets_form_category(self):
        assert_true(hasattr(self.table, 'getDatasets'))
        datasets = self.table.getDatasets('category')
        for ds in datasets:
            assert_list_equal(sorted(self.known_ds_subkeys_category), sorted(list(ds.definition.keys())))

    def test_getDatasets_form_siteid_and_category(self):
        assert_true(hasattr(self.table, 'getDatasets'))
        datasets = self.table.getDatasets('category', 'site')
        for ds in datasets:
            assert_list_equal(sorted(self.known_ds_subkeys_siteid), sorted(list(ds.definition.keys())))

    @raises(ValueError)
    def test_getDatasets_form_raises(self):
        assert_true(hasattr(self.table, 'getDatasets'))
        datasets = self.table.getDatasets('storm')

    def test_redefineIndexLevel_DropOldTrue(self):
        levelname = 'epazone'
        newzone = 9999
        oldzone = 2

        assert_true(hasattr(self.table, 'redefineIndexLevel'))
        criteria = lambda row: row[1] == oldzone

        self.table.redefineIndexLevel(levelname, newzone, criteria, dropold=True)
        assert_true(newzone in self.table.data.index.get_level_values(levelname))
        assert_true(oldzone not in self.table.data.index.get_level_values(levelname))

    def test_redefineIndexLevel_DropOldFalse(self):
        levelname = 'epazone'
        newzone = 9999
        oldzone = 2

        assert_true(hasattr(self.table, 'redefineIndexLevel'))
        criteria = lambda row: row[1] == oldzone

        self.table.redefineIndexLevel(levelname, newzone, criteria, dropold=False)
        assert_true(newzone in self.table.data.index.get_level_values(levelname))
        assert_true(oldzone in self.table.data.index.get_level_values(levelname))

    def test_redefineBMPCategory_DropOldTrue(self):
        newcat = 'Test New Category'
        oldcat = self.known_bmp_cats[-1]

        bmpcat_index = self.table.index['category']
        assert_true(hasattr(self.table, 'redefineBMPCategory'))
        criteria = lambda row: row[bmpcat_index] == oldcat

        self.table.redefineBMPCategory(newcat, criteria, dropold=True)
        assert_true(newcat in self.table.data.index.get_level_values('category'))
        assert_true(oldcat not in self.table.data.index.get_level_values('category'))

    def test_redefineBMPCategory_DropOldFalse(self):
        newcat = 'Test New Category'
        oldcat = self.known_bmp_cats[-1]

        bmpcat_index = self.table.index['category']
        assert_true(hasattr(self.table, 'redefineBMPCategory'))
        criteria = lambda row: row[bmpcat_index] == oldcat

        self.table.redefineBMPCategory(newcat, criteria, dropold=False)
        assert_true(newcat in self.table.data.index.get_level_values('category'))
        assert_true(oldcat in self.table.data.index.get_level_values('category'))

    def test_to_DataCollection(self):
        assert_true(hasattr(self.table, 'to_DataCollection'))
        dc = self.table.to_DataCollection()
        assert_true(isinstance(dc, features.DataCollection))

    def test__check_for_parameters(self):
        assert_true(hasattr(self.table, '_check_for_parameters'))
        assert_true(self.table._check_for_parameters(self.known_parameters))
        assert_true(self.table._check_for_parameters(self.known_parameters[0]))
        assert_false(self.table._check_for_parameters(['junk', 'garbage']))


class test_table_metals(_base_tableMixin):
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
    @nottest
    def mainsetup(self):
        self.known_name = 'Copper, Total'
        self.known_tex = 'Total Copper'
        self.known_std_units = 'ug/L'
        self.known_units = r'\si[per-mode=symbol]{\micro\gram\per\liter}'

    def test_name(self):
        assert_true(hasattr(self.parameter, 'name'))
        assert_equal(self.parameter.name, self.known_name)

    def test_tex(self):
        assert_true(hasattr(self.parameter, 'tex'))
        assert_equal(self.parameter.tex, self.known_tex)

    def test_units(self):
        assert_true(hasattr(self.parameter, 'units'))
        assert_equal(self.parameter.units, self.known_units)

    def test_std_units(self):
        assert_true(hasattr(self.parameter, 'std_units'))
        assert_equal(self.parameter.std_units, self.known_std_units)

    def test_paramunit(self):
        assert_true(hasattr(self.parameter, 'paramunit'))
        assert_equal(self.parameter.paramunit(usetex=True, usecomma=self.usecomma),
                     self.known_paramunits)


class test_param(_base_parameterMixin):
    def setup(self):
        self.mainsetup()
        self.usecomma = False
        self.parameter = da.Parameter(self.known_name)
        self.known_paramunits = r'Total Copper (\si[per-mode=symbol]{\micro\gram\per\liter})'


class test_param_usecomma(_base_parameterMixin):
    def setup(self):
        self.mainsetup()
        self.usecomma = True
        self.parameter = da.Parameter(self.known_name)
        self.known_paramunits = r'Total Copper, \si[per-mode=symbol]{\micro\gram\per\liter}'
