import os
import itertools
from textwrap import dedent
from contextlib import contextmanager

try:
    import pyodbc
except ImportError:
    pyodbc = None

import numpy as np
import pandas
from pandas.io import sql

from . import info

import wqio
from wqio import utils


__all__ = [
    'Database',
    'Table',
    'Parameter'
]


def _fancy_factors(row, quals=None):
    if quals is None:
        quals = ['U', 'UK', 'UA', 'UC', 'K']
    if row['qual'] in quals:
        return 2.
    elif row['qual'] == 'UJ'and row['res'] < row['DL']:
        return row['DL'] / row['res']
    else:
        return 1.


def _fancy_quals(row, quals=None):
    if quals is None:
        quals = ['U', 'UA', 'UI', 'UC', 'UK', 'K']
    if (row['qual'] in quals) or (row['qual'] == 'UJ' and row['res'] <= row['DL']):
        return 'ND'
    else:
        return '='


def _process_screening(screen_val):
    if screen_val.lower().strip() in ['inc', 'yes']:
        return 'yes'
    elif screen_val.lower().strip() in ['exc', 'no']:
        return 'no'
    else:
        msg = 'invalid screening value ({0}) found'.format(screen_val)
        raise ValueError(msg)


def _process_sampletype(sampletype):
    if "grab" in sampletype.lower():
        return "grab"
    elif "composite" in sampletype.lower():
        return "composite"
    else:
        return "unknown"


def _check_station(station):
    if station.lower() in ['reference', 'subsurface']:
        raise NotImplementedError

    if station.lower() not in ['inflow', 'outflow']:
        raise ValueError('`station` must be "inflow" or "outflow"')

    return station.lower()


def _check_levelnames(levels):
    good_levels = [
        'category', 'site', 'bmp', 'parameter',
        'sampletype', 'epazone', 'state', 'paramgroup'
    ]
    msg = 'valid levels are {}'.format(good_levels)

    for lvl in levels:
        if lvl not in good_levels:
            raise ValueError(msg)


@contextmanager
def db_connection(dbfile, driver=None):
    if driver is None:
        driver = r'{Microsoft Access Driver (*.mdb, *.accdb)}'

    connection_string = r'Driver={};DBQ={}'.format(driver, os.path.abspath(dbfile))
    try:
        cnn = pyodbc.connect(connection_string)
        yield cnn
    except:
        msg = "Unable to connect to {} using {}"
        raise RuntimeError(msg.format(dbfile, driver))

    cnn.close()


class Database(object):
    def __init__(self, filename, dbtable=None, sqlquery=None,
                 catanalysis=False, useTex=True):
        """Top-level entry point for International BMP Database analysis

        Parameters
        ----------
        filename : string
            CSV file or MS Access database containing the data.
        dbtable : optional string (defaults to the bundled data')
            Table in the MS Access database storing the data for
            analysis. Only used if `usingdb` is True.
        catanalysis : optional bool (default = False)
            Toggles the filtering for data that have been approved for
            BMP Category-level analysis

        Attributes
        ----------
        dbfile : string
            Full path to the database file.
        driver : string
            ODBC-compliant Microsoft Access driver string.
        category_type : string
            See Input section.
        usingdb : bool
            See Input section.
        excluded_parameters : list of string or None
            See `parametersToExclude` in Input section.
        data : pandas DataFrame
            DataFrame of all of the data found in the DB or CSV file.

        Methods
        -------
        connect
        redefineBMPCategory
        convertTablesToCSV
        getAllData
        getGroupData

        """

        self.file = filename
        self.usingdb = os.path.splitext(self.file)[1] in ['.accdb', '.mdb']
        self.catanalysis = catanalysis
        self.useTex = useTex

        # property initialization
        self.__from_source = None
        self.__data_cleaned = None
        self._data = None
        if self.usingdb:
            self._sqlquery = sqlquery
            self._dbtable = dbtable
            self.driver = r'{Microsoft Access Driver (*.mdb, *.accdb)}'
        else:
            self._sqlquery = None
            self._dbtable = None
            self.driver = None

    @property
    def dbtable(self):
        return self._dbtable
    @dbtable.setter
    def dbtable(self, value):
        self._dbtable = value

    @property
    def sqlquery(self):
        if self.dbtable is not None:
            self._sqlquery = "select * from [{}]".format(self.dbtable)
        elif self._sqlquery is None:
            self._sqlquery = dedent("""
                select
                    [src].[Analysis_Category] as [category],
                    [src].[BMP Cat Code] as [bmpcat],
                    [src].[TBMPT 2009] as [bmptype],
                    [src].[EPA Rain Zone] as [epazone],
                    [src].[State] as [state],
                    [src].[Country] as [country],
                    [src].[SITENAME] as [site],
                    [src].[BMPName] as [bmp],
                    [src].[PDF ID] as [PDFID],
                    [src].[WQID],
                    [src].[MSNAME] as [monitoringstation],
                    [src].[Storm #] as [storm],
                    [src].[SAMPLEDATE] as [sampledate],
                    [src].[SAMPLETIME] as [sampletime],
                    [src].[Group] as [paramgroup],
                    [src].[Analysis Sample Fraction] as [fraction],
                    [src].[WQX Parameter] as [raw_parameter],
                    [src].[Common Name] as [parameter],
                    [src].[WQ UNITS] as [wq_units],
                    [src].[QUAL] as [wq_qual],
                    [src].[WQ Analysis Value] as [wq_value],
                    [src].[DL] as [DL],
                    [src].[Monitoring Station Type] as [station],
                    [src].[SGTCodeDescp] as [watertype],
                    [src].[STCODEDescp] as [sampletype],
                    [src].[Use in BMP WQ Analysis] as [wqscreen],
                    [src].[Use in BMP Category Analysis] as [catscreen],
                    [src].[Infl_Effl_Balance] as [balanced]
                from [{}] as [src]
                where [src].[Common Name] is not null
                order by
                    [src].[TBMPT 2009],
                    [src].[CATEGORY],
                    [src].[SITENAME],
                    [src].[BMPName],
                    [src].[Storm #],
                    [src].[SAMPLEDATE],
                    [src].[Common Name],
                    [src].[WQX Parameter],
                    [src].[Analysis Sample Fraction],
                    [src].[Monitoring Station Type];
                """.format(self.dbtable)
            )
        return self._sqlquery
    @sqlquery.setter
    def sqlquery(self, value):
        self._sqlquery = value

    @property
    def _source_data(self):
        if self.__from_source is None:
            if self.usingdb:
                # SQL query text, execution, data retrieval
                with db_connection(self.file, self.driver) as cnn:
                    self.__from_source = sql.read_sql(self.sqlquery, cnn)
            else:
                self.__from_source = pandas.read_csv(self.file, encoding='utf-8')

        return self.__from_source

    @property
    def _data_cleaned(self):
        if self.__data_cleaned is None:
            self.__data_cleaned = self._cleanup_data()
        return self.__data_cleaned

    @property
    def data(self):
        if self._data is None:
            self._data = self._group_data()
        return self._data
    @data.setter
    def data(self, df):
        self._data = df

    @property
    def index(self):
        return {name: level for level, name in enumerate(self.data.index.names)}

    @property
    def bmp_categories(self):
        return self.index_values('category')

    @property
    def params(self):
        return self.index_values('parameter')

    @property
    def parameters(self):
        self._parameters = self._get_parameters(asobj=True)
        return self._parameters

    @property
    def parameter_lookup(self):
        return {p.name: p for p in self.parameters}

    def index_values(self, levelname):
        """ Fetch unique values of a level of the index of ``data``

        Parameters
        ----------
        levelname : string

        Returns
        -------
        values : np.array

        """
        return self.data.index.get_level_values(levelname).unique().tolist()

    @staticmethod
    def _strip_quals(df, qualcol):
        df[qualcol] = df[qualcol].str.strip()
        return df

    @staticmethod
    def _apply_res_factors(df, rescol, qualcol, userfxn=None, quallist=None, factor=None):

        if factor is not None and userfxn is None:
            if quallist is None:
                raise ValueError("must provide `quallist` if useing `factor`")

            factors = df[qualcol].apply(lambda x: factor if x in quallist else 1)

        elif factor is None and userfxn is not None:
            factors = df.apply(userfxn, axis=1)

        else:
            raise ValueError("must provide exactly 1 of `factor` or `userfxn`")

        df[rescol] *= factors

        return df

    @staticmethod
    def _standardize_quals(df, qualcol, ndquals=None, userfxn=None):
        if ndquals is not None and userfxn is None:
            df[qualcol] = df.apply(
                lambda x: 'ND' if x.qual in ndquals else '=',
                axis=1
            )
        elif ndquals is None and userfxn is not None:
            df[qualcol] = df.apply(userfxn, axis=1)

        else:
            raise ValueError("must provide exactly 1 of `ndquals` or `userfxn`")

        return df

    def _get_parameters(self, asobj=True):
        """
        Looks at the dataframe `tabledata` (from `getTableData`) and returns a list
        of Parameter objects for each unique parameter-unit combination.

        Ideally, there should only be one unit for each parameter.

        Input:
            usingdb (bool, default False) : toggles reading from the database or a
                local csv file
            csvfile (string, default 'bmp/bmpcats.csv') : path and filename to the
                datafile

        Returns
        -------
        parameters (list of Parameter objects)

        """

        # groups the data by parameter, tex, and units
        parameter_unit_levels = ['parameter', 'units']
        params_df = self.data.reset_index()[parameter_unit_levels].drop_duplicates()

        if params_df.shape[0] > params_df['parameter'].unique().shape[0]:
            raise ValueError('dataframe does not have consistent units')

        # initalize the results list
        parameters = []
        for row in params_df.to_dict(orient='records'):
            basic_param = row['parameter']
            basic_unit = row['units']
            if self.useTex:
                p = wqio.Parameter(
                    name=info.getParam(basic_param, attr='tex'),
                    units=info.getUnits(basic_unit, attr='tex')
                )
            else:
                p = wqio.Parameter(name=basic_param, units=basic_unit)

            parameters.append(p)

        return parameters

    def _check_for_parameters(self, parameter_names):
        if np.isscalar(parameter_names):
            parameter_names = [parameter_names]
        return np.all([p in self.params for p in parameter_names])

    def _cleanup_data(self):

        row_headers = [
            'category', 'epazone', 'state', 'site', 'bmp',
            'station', 'storm', 'sampletype', 'watertype',
            'paramgroup', 'units', 'parameter', 'fraction', 'wqscreen',
            'catscreen', 'balanced', 'PDFID', 'WQID'
        ]

        units_norm = {
            u['unicode']: info.getNormalization(u['name'])
            for u in info.units
        }

        target_units = {
            p['name'].lower(): info.getUnitsFromParam(p['name'], attr='unicode')
            for p in info.parameters
        }

        # rename columns:
        rename_columns = {
            'wq_qual': 'qual',
            'wq_value': 'res',
            'wq_units': 'units',
            'raw_parameter': 'general_parameter',
            'category': 'category'
        }
        drop_columns = ['monitoringstation', '_parameter']
        data = (
            self._source_data
                .rename(columns=rename_columns)
                .dropna(subset=['res'])
                .pipe(self._strip_quals, qualcol='qual')
                .pipe(self._apply_res_factors, rescol='res', qualcol='qual', userfxn=_fancy_factors)
                .pipe(self._standardize_quals, qualcol='qual', userfxn=_fancy_quals)
                .assign(wqscreen=lambda df: df['wqscreen'].apply(_process_screening))
                .assign(catscreen=lambda df: df['catscreen'].apply(_process_screening))
                .assign(station=lambda df: df['station'].str.lower())
                .assign(sampletype=lambda df: df['sampletype'].apply(_process_sampletype))
                .assign(sampledatetime=lambda df: df.apply(utils.makeTimestamp, axis=1))
                .assign(units=lambda df: df['units'].map(lambda u: info.getUnits(u, attr='unicode')))
                .assign(_parameter=lambda df: df['parameter'].str.lower().str.strip())
                .assign(fraction=lambda df: df['fraction'].str.lower().str.strip())
                .pipe(utils.normalize_units, units_norm, target_units, paramcol='_parameter', rescol='res', unitcol='units', napolicy='raise')
                .drop(drop_columns, axis=1)
                .query("res > 0")
        )

        return data

    def _group_data(self):
        # columns to be the index
        row_headers = [
            'category', 'epazone', 'state', 'site', 'bmp',
            'station', 'storm', 'sampletype', 'watertype',
            'paramgroup', 'units', 'parameter', 'wqscreen',
            'catscreen', 'balanced', 'PDFID', 'WQID'
        ]

        # group the data based on the index
        agg_rules = {'res': 'mean', 'qual': 'min', 'sampledatetime': 'min'}

        agged = (
            self._data_cleaned
                .groupby(by=row_headers)
                .agg(agg_rules)
                .set_index('sampledatetime', append=True)
        )

        return agged

    def connect(self, cmd=None, commit=False):
        '''
        Connects to the database using pyodbc. Executes a command if provided.

        Parameters
        ----------
        cmd : optional string or None (default)
            SQL statement that will be executed (see Notes).

        commit : optional bool (default = False)
            Toggles if the changes to the database executed with `cmd`
            should be save. Be carefule. You could delete everything

        Returns
        -------
        cnn : pyodbc connection object

        Notes
        ------
         - It's recommended to not use the `cmd` argument to retrieve data.
           In fact, it's impossible. If you need to execute a custom
           selection query it's recommended to use the function to create
           the connection object and the pass that to
           pandas.io.sql.read_frame (see Examples).
         - This function is primarily used internally to select large
           amounts of data when instantiating the `Database` object.
           It's probably best to use pandas selection methods on the
           `data` attribute to isolated specific records for a
           particular analysis.

        Examples
        -------
        >>> from pandas.io import sql
        >>> import bmp
        >>> db = bmp.dataAccess.Database()
        >>> myCmd = "SELECT * FROM myTable"
        >>> with db.connect() as cnn:
           ...: data = sql.read_frame(myCmd, cnn)
        >>> print(data.head())

        '''

        if os.path.splitext(self.file)[1] not in ['.accdb', '.mdb']:
            raise ValueError('Datasource is not an MS Access database')

        # connection string
        connection_string = r'Driver=%s;DBQ=%s' % (self.driver, self.file)

        # make the connection and cursor
        cnn = pyodbc.connect(connection_string)

        # execute commands if provided
        if cmd is not None:
            cur = cnn.cursor()

            try:
                cur.execute(cmd)

                # commit if requested
                if commit:
                    cnn.commit()

            # raise whatever exception we encoutered
            except:
                raise
            # be sure to close the cursor
            finally:
                cur.close()

        return cnn

    def dbtable_to_csv(self, tablename, filepath=None):
        '''
        Converts all relevant tables in the DB to CSV files
        '''
        if not self.usingdb:
            raise NotImplementedError('`Database` source is not an Access Database')
        if filepath is None:
            filepath = 'bmp/data/{0}.csv'
        cmd = "select * from [{0}]".format(tablename)
        with db_connection(self.file, self.driver) as cnn:
            sql.read_frame(cmd, cnn).to_csv(filepath, index=False, encoding='utf-8')

    def select(self, **kwargs):
        """Select data from the database.

        Parameters
        ----------
        Optional kwargs:
            You can additioanlly pass keyword arguments that define
            selection criteria on the data. Values can be either strings
            (single values) or lists of strings (multiple values).
            Valid Keys are:
                'category', 'site', 'bmp', 'storm', 'paramgroup',
                'units', 'parameter', 'sampletype', 'epazone', 'state',
                'wqscreen', and 'catscreen'

        Returns
        -------
        pandas.DataFrame or bmp.Table per `astable`

        Examples
        --------
        >>> db = bmp.Database(my_database_path)
        >>> table = db.select(
        ... category=['Wetland Basin', 'Bioretention'],
        ... paramgroup='Nutrients'
        ... )

        """
        good_keys = [
            'category', 'site', 'bmp', 'storm', 'sampledatetime',
            'paramgroup', 'units', 'parameter', 'sampletype',
            'epazone', 'state',
        ]

        index_levels = self.data.index.names

        data = self.data.reset_index()
        for key, val in kwargs.items():
            if key not in good_keys:
                raise ValueError("filtering by %s not supported" % key)

            if np.isscalar(val):
                val = [val]

            data = data.loc[data[key].isin(val), :]

        return data.set_index(index_levels)

    def redefineIndexLevel(self, levelname, value, criteria, dropold=True):
        """ Redefine a selection of BMPs into another or new category

        Parameters
        ----------
        levelname : string
            The name of the index level that needs to be modified.
            (see `Database.index`)
        value : string or int
            The replacement value for the index level.
        critera : callable
            This should return True/False in a manner consitent with the
            `.select()` method of a pandas dataframe. See that docstring
            for more info.
        dropold : bool, optional (default is True)
            Toggles the replacement (True) or addition (False) of the
            data of the redefined BMPs into the the `data` dataframe.

        Returns
        -------
        None (operates in-place)

        Notes
        -----
        The standard dataframe present in `Database.data` has the
        following indicies:

        | Level | Name                                       |
        |-------|--------------------------------------------|
        | 0     | category (determined by ``category_type``) |
        | 1     | epazone                                    |
        | 2     | state                                      |
        | 3     | site                                       |
        | 4     | bmp                                        |
        | 5     | storm                                      |
        | 6     | sampletype                                 |
        | 7     | paramgroup                                 |
        | 8     | units                                      |
        | 9     | parameter                                  |

        So if you were creating a selection based on a set of Site IDs,
        your lambda expression would look like this:

        >>> criteria = lambda row: row[1] in my_site_id_list

        Example
        -------
        >>> # import and create `Database` object
        >>> import bmp
        >>> db = bmp.dataAccess.Database()
        >>> # move tree box planters into their own EPA Zone
        >>> bmpcats = [-1098775618, 95902823, 1053525776, 1495211473]
        >>> criteria = lambda row: row[3] in TB_bmps
        >>> db.redefineIndexLevel('epazone', 9999, criteria, dropold=True)
        >>> # prove to ourselves that it worked
        >>> print(db.data.index.get_level_values('epazone').unique())

        """

        self.data = utils.redefine_index_level(
            self.data, levelname, value,
            criteria=criteria, dropold=dropold
        )

    def redefineBMPCategory(self, bmpname, criteria, dropold=True):
        """ Redefine a selection of BMPs into another or new category

        Parameters
        ----------
        bmpname : string
            The longer-form name/description of the BMP category that
            will be created.
        critera : callable
            This should return True/False in a manner consitent with the
            `.select()` method of a pandas dataframe. See that docstring
            for more info.
        dropold : bool, optional (default is True)
            Toggles the replacement (True) or addition (False) of the
            data of the redefined BMPs into the the `data` dataframe.

        Returns
        -------
        None (operates in-place)

        Notes
        -----
        The standard dataframe present in `Database.data` has the
        following indicies:

        | Level | Name                                       |
        |-------|--------------------------------------------|
        | 0     | category (determined by ``category_type``) |
        | 1     | epazone                                    |
        | 2     | state                                      |
        | 3     | site                                       |
        | 4     | bmp                                        |
        | 5     | storm                                      |
        | 6     | sampletype                                 |
        | 7     | paramgroup                                 |
        | 8     | units                                      |
        | 9     | parameter                                  |

        So if you were creating a selection based on a set of Site IDs,
        your lambda expression would look like this:

        >>> criteria = lambda row: row[1] in my_site_id_list

        Examples
        --------
        >>> # import and create `Database` object
        >>> import bmp
        >>> db = bmp.dataAccess.Database()
        >>> # replace tree box planters original BMP category (MD)
        >>> # with "TreeBox"
        >>> TB_bmps = [-1098775618, 95902823, 1053525776, 1495211473]
        >>> criteria = lambda row: row[3] in TB_bmps
        >>> db.redefineBMPCategory('TB', 'Tree box planter', criteria)
        >>> # show that it worked
        >>> print(db.data.index.get_level_values('category').unique())
        """

        self.data = utils.redefine_index_level(
            self.data, 'category', bmpname,
            criteria=criteria, dropold=dropold
        )

    def transformParameters(self, existingparams, newparam, resfxn, qualfxn,
                            newunits, indexMods=None):
        """ Apply an arbitrary transformation to a parameter in the data

        Parameters
        ----------
        existingparams : list of strings
            List of the existing parameters that will be used to compute
            the new values
        newparam : string
            Name of the new parameter to be generated
        resfxn : callable
            Function (or lambda) that will determine the result of
            ``newparam`` based on the values of ``existingparams``.
            Function must assume to be operating on a row of
            ``self.data`` with the elements of ``existingparams`` stored
            as columns.
        qualfxn : function
            Same as ``resfxn``, but for determining the final qualifier
            of the ``newparam`` results.
        newunits : string
            Units of the newly computed values
        indexMods : dict, optional (keys = index level names)
            Dictionary of index level name whose values are the new
            values of those levels where ``parameter == newparam``.

        Returns
        -------
        None (operates in-place)

        Example
        -------
        >>> csvpath = 'bmp/data/data_pybmpdb.csv'
        >>> db = bmp.dataAccess.Database(file=csvpath)
        >>> db.transformParameters(['pH'], 'protons',
        ...     lambda x, junk: utils.pH2concentration(x[('res', 'pH')]),
        ...     lambda x, junk: x[('qual', 'pH')], 'mg/L'
        ... )

        """

        index_name_cache = self.data.index.names

        if np.isscalar(existingparams):
            existingparams = [existingparams]

        params_exist = self._check_for_parameters(existingparams)
        if not params_exist:
            raise ValueError("Parameter %s is not in this dataset" % param)


        pindex = self.index['parameter']
        selection = self.data.query("parameter in {}".format(existingparams))

        # put the station into the row index and pivot the param into columns
        selection = selection.unstack(level='parameter')

        # compute the right values
        selection[('qual', newparam)] = selection.apply(qualfxn, axis=1,
                                                  args=existingparams)
        selection[('res', newparam)] = selection.apply(resfxn, axis=1,
                                                 args=existingparams)

        # keep only the combined data
        selection = selection.select(lambda col: col[1] == newparam, axis=1)

        # station goes back in into columns, parameters into rows
        #selection = selection.unstack(level='station')
        selection = selection.stack(level='parameter')

        # get the column indices in the right order
        #selection.columns = selection.columns.swaplevel('quantity', 'station')

        # check on indexMods
        if indexMods is None:
            indexMods = {}

        # check indexMods type
        if indexMods is not None:
            if not isinstance(indexMods, dict):
                raise ValueError('indexMods must be a dictionary')

            # add the units into indexMod, apply all changes
            indexMods['units'] = newunits
            for levelname, value in indexMods.items():
                selection = utils.redefine_index_level(
                    selection,
                    levelname,
                    value,
                    criteria=None,
                    dropold=True
                )

        if newunits not in [u['name'] for u in info.units]:
            info.units = info.addUnit(name=newunits)

        if newparam not in [p['name'] for p in info.parameters]:
            info.parameters = info.addParameter(name=newparam, units=newunits)

        # return the *full* dataset (preserving original params)
        self.data = pandas.concat([
            self.data.reset_index(),
            selection.reset_index()
        ]).set_index(index_name_cache)

    def unionParamsWithPreference(self, existingparams, newparam, newunits):
        """
        Looks as instances of two different analytes, picks the best one, and
        the appends a new row with the preferred result under a new parameter
        name. The best example of this is taking NO3+NO2 and NO3 data, and
        "unioning" them to get NOx data -- NO3+NO2 is the best to use, but if
        it's not available, fall back to NO3 since NO2 is typically small.

        Parameters
        ----------
        existingparams : list of string
            List of the parameters you wish to merge (currently limited
            to 2)

        newparam : string
            Name of the new parameter you're creating (e.g., NOx in the
            example above)

        newunits : string
            Units of the new value

        Returns:
            None - (operates in-place)

        Examples
        -------
        >>> db = bmp.dataAccess.Database(file='bmp/data/data_pybmpdb.csv')
        >>> table = bmp.dataAccess.Table('Nutrients', db)
        >>> nitro_components = [
            'Nitrogen, Nitrite (NO2) + Nitrate (NO3) as N',
            'Nitrogen, Nitrate (NO3) as N'
        ]
        >>> nitro_combined = 'Nitrogen, NOx as N'
        >>> table.unionParamsWithPreference(nitro_components, nitro_combined, 'mg/L')

        """

        if len(existingparams) != 2:
            raise NotImplementedError('existingparams must be a sequence of length = 2')

        # function to return the right column of qualifiers
        def returnFiniteQual(row, preferred, secondary):
            if isinstance(row[('qual', preferred)], str):
                return row[('qual', preferred)]
            else:
                return row[('qual', secondary)]

        # function to return the right column of results
        def returnFiniteRes(row,  preferred, secondary):
            if np.isfinite(row[('res', preferred)]):
                return row[('res', preferred)]
            else:
                return row[('res', secondary)]

        self.transformParameters(existingparams, newparam, returnFiniteRes, returnFiniteQual, newunits)

    def to_DataCollection(self, selection_dict, **kwargs):
        df = self.select(**selection_dict)
        return wqio.DataCollection(self.data, **kwargs)
