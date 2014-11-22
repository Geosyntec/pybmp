import sys
import os
if sys.version_info.major == 3:
    from io import StringIO
else:
    from StringIO import StringIO

import nose
from nose.tools import *
import numpy as np
import numpy.testing as nptest
try:
    import pyodbc
except ImportError:
    pyodbc = None
import pandas

from pybmp.bmp import dataAccess as da
from pybmp.core import features

skip_db = pyodbc is None or os.name == 'posix'
datadir = os.path.join(sys.prefix, 'pybmp_data', 'testing')


def test__process_screening_yes():
    assert_equal('yes', da._process_screening('Yes'))
    assert_equal('yes', da._process_screening('INC'))


def test__process_screening_no():
    assert_equal('no', da._process_screening('No'))
    assert_equal('no', da._process_screening('eXC'))


@raises(ValueError)
def test__process_screening_raiese():
    assert_equal('yes', da._process_screening('JUNK'))


def test__process_sampletype_grab():
    assert_equal(da._process_sampletype('SRjeL GraB asdf'), 'grab')


def test__process_sampletype_composite():
    assert_equal(da._process_sampletype('SRjeL cOMPositE asdf'), 'composite')


def test__process_sampletype_unknown():
    assert_equal(da._process_sampletype('SRjeL LSDRsdfljkSdj asdf'), 'unknown')


class test__filter_index:
    def setup(self):
        self.row = ('BI', 'CA', 11)

    def test_scalars_single_true(self):
        assert_true(da._filter_index(self.row, [0], ['BI']))

    def test_scalars_single_false(self):
        assert_false(da._filter_index(self.row, [0], ['BS']))

    def test_scalars_multi_true(self):
        assert_true(da._filter_index(self.row, [0, 1], ['BI', 'CA']))

    def test_scalars_multi_false(self):
        assert_false(da._filter_index(self.row, [0, 1], ['BI','GA']))

    def test_lists_single_true(self):
        assert_true(da._filter_index(self.row, [0], [['BI', 'BS']]))

    def test_lists_single_false(self):
        assert_false(da._filter_index(self.row, [0], [['FS','BR']]))

    def test_lists_multi_true(self):
        assert_true(da._filter_index(self.row, [0, 1], [['BI'], ['CA']]))

    def test_lists_multi_false(self):
        assert_false(da._filter_index(self.row, [0, 1], [['BI'],['GA']]))


class test_defaultFilter:
    def setup(self):
        self.testcsv = StringIO(
            "A,B,X\n1,A,1\n2,A,1\n1,B,1\n2,B,1\n3,B,1\n"
            "4,B,1\n1,C,1\n2,C,1\n3,C,1\n4,C,1\n1,D,1\n"
            "2,D,1\n3,D,1\n4,D,1\n1,E,1\n2,E,1\n1,F,1\n"
            "2,F,1\n"
        )
        self.df = pandas.read_csv(self.testcsv, index_col=['A', 'B'])
        self.minElements = 3
        self.minGroups = 4
        self.known_A_filtered_length = 18
        self.known_A_include = True
        self.known_B_filtered_length = 12
        self.known_B_include = False

    def test_A_filter(self):
        a_data, a_include = da.defaultFilter(self.df, levelname='A',
                                         minElements=self.minElements,
                                         minGroups=self.minGroups)
        assert_equal(self.known_A_filtered_length, a_data.shape[0])
        assert_equal(self.known_A_include, a_include)

    def test_B_filter(self):
        b_data, b_include = da.defaultFilter(self.df, levelname='B',
                                         minElements=self.minElements,
                                         minGroups=self.minGroups)
        assert_equal(self.known_B_filtered_length, b_data.shape[0])
        assert_equal(self.known_B_include, b_include)


class _base_database():
    @nottest
    def mainsetup(self):
        self.known_dbfile = os.path.join(datadir, 'testdata.accdb')
        self.known_csvfile = os.path.join(datadir, 'testdata.csv')
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

    @nptest.dec.skipif(skip_db)
    def test_driver(self):
        assert_true(hasattr(self.db, 'driver'))
        assert_equal(self.db.driver, self.known_driver)

    @nptest.dec.skipif(skip_db)
    def test_usingdb(self):
        assert_true(hasattr(self.db, 'usingdb'))
        assert_equal(self.db.usingdb, self.known_usingdb)

    @nptest.dec.skipif(skip_db)
    def test_file(self):
        assert_true(hasattr(self.db, 'file'))
        assert_equal(self.db.file, self.known_file)

    @nptest.dec.skipif(skip_db)
    def test_data_exists(self):
        assert_true(hasattr(self.db, 'data'))
        assert_true(isinstance(self.db.data, pandas.DataFrame))
        assert_tuple_equal(self.db.data.shape, self.known_datashape)

    @nptest.dec.skipif(skip_db)
    def test_data_index(self):
        assert_true(isinstance(self.db.data.index, pandas.MultiIndex))
        assert_equal(self.db.data.index.names, self.known_index_names)

    @nptest.dec.skipif(skip_db)
    def test_data_positive(self):
        assert_true(self.db.data['res'].min() > 0)

    @nptest.dec.skipif(skip_db)
    def test_selectData_exists(self):
        assert_true(hasattr(self.db, 'selectData'))
        data = self.db.selectData(paramgroup=self.known_group)

    @nptest.dec.skipif(skip_db)
    def test_selectData_form(self):
        data = self.db.selectData(paramgroup=self.known_group)
        assert_true(isinstance(data, pandas.DataFrame))
        assert_true(data.index.names, self.known_index_names)
       # assert_list_equal(self.db.data.columns.names, self.known_col_names)
        nptest.assert_array_equal(data.index.get_level_values('paramgroup').unique(),
                          np.array([self.known_group]))

    @raises(ValueError)
    @nptest.dec.skipif(skip_db)
    def test_selectData_raise(self):
        self.db.selectData(junk=False)

    @nptest.dec.skipif(skip_db)
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

    @nptest.dec.skipif(skip_db)
    def test_selectData_list_args(self):
        parameters = [
            u'Copper, Total',
            u'Copper, Dissolved',
        ]
        data = self.db.selectData(parameter=parameters)
        assert_true(isinstance(data, pandas.DataFrame))
        nptest.assert_array_equal(data.index.get_level_values('parameter').unique(),
                          np.array(parameters))

    @nptest.dec.skipif(skip_db)
    def test_selectData_table(self):
        parameters = [
            u'Copper, Total',
            u'Copper, Dissolved',
        ]
        table = self.db.selectData(astable=True, parameter=parameters)
        assert_true(isinstance(table, da.Table))
        nptest.assert_array_equal(table.data.index.get_level_values('parameter').unique(),
                          np.array(parameters))


class test_DatabaseFromDB(_base_database):
    @nptest.dec.skipif(skip_db)
    def setup(self):
        self.mainsetup()
        self.known_driver = r'{Microsoft Access Driver (*.mdb, *.accdb)}'
        self.known_bmpcatsrc = 'bmpcats'
        self.known_usingdb = True
        self.known_file = self.known_dbfile
        self.known_catScreen = False
        self.db = da.Database(self.known_dbfile)
        self.error = pyodbc.ProgrammingError

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
    @raises(pyodbc.ProgrammingError)
    def test_connect_BadQuery(self):
        cmd = "JUNKJUNKJUNK"
        self.db.connect(cmd=cmd)

    @nptest.dec.skipif(skip_db)
    def test_file(self):
        assert_true(hasattr(self.db, 'file'))
        assert_equal(self.db.file, self.known_dbfile)

    @nptest.dec.skipif(True)
    def test_convertTableToCSV(self):
        assert_true(hasattr(self.db, 'convertTableToCSV'))
        outputfile = os.path.join(datadir, 'testoutput.csv')
        self.db.convertTableToCSV('bmpcats', filepath=outputfile)


class test_DatabaseFromCSV(_base_database):
    def setup(self):
        self.mainsetup()
        self.known_driver = None
        self.known_usingdb = False
        self.known_file = self.known_csvfile
        self.known_bmpcatsrc = os.path.join(datadir, 'testbmpcats.csv')
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
        outputfile = os.path.join(datadir, 'testoutput.csv')
        self.db.convertTableToCSV('bmpcats', filepath=outputfile)

    def test_file(self):
        assert_true(hasattr(self.db, 'file'))
        assert_equal(self.db.file, self.known_csvfile)


class _base_table:
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
        self.known_csvfile = os.path.join(datadir, 'testdata.csv')
        self.known_bmpcatsrc = os.path.join(datadir, 'testbmpcats.csv')
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

    def test_getDatasets_withFilter(self):
        assert_true(hasattr(self.table, 'getDatasets'))
        ds_filtered = self.table.getDatasets('category', filterfxn=da.defaultFilter)
        ds_nofilter = self.table.getDatasets('category')
        influent_diff = 5
        effluent_diff = 10
        for dsf, dsn in zip(ds_filtered, ds_nofilter):
            assert_true(dsn.influent.data.shape[0] >= dsf.influent.data.shape[0])
            assert_true(dsn.effluent.data.shape[0] >= dsf.effluent.data.shape[0])
            influent_diff += dsn.influent.data.shape[0] - dsf.influent.data.shape[0]
            effluent_diff += dsn.effluent.data.shape[0] - dsf.effluent.data.shape[0]

        assert_equal(influent_diff, self.known_influent_diff)
        assert_equal(effluent_diff, self.known_effluent_diff)

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


class test_table_metals(_base_table):
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


class _base_parameter:
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


class test_param(_base_parameter):
    def setup(self):
        self.mainsetup()
        self.usecomma = False
        self.parameter = da.Parameter(self.known_name)
        self.known_paramunits = r'Total Copper (\si[per-mode=symbol]{\micro\gram\per\liter})'


class test_param_usecomma(_base_parameter):
    def setup(self):
        self.mainsetup()
        self.usecomma = True
        self.parameter = da.Parameter(self.known_name)
        self.known_paramunits = r'Total Copper, \si[per-mode=symbol]{\micro\gram\per\liter}'
