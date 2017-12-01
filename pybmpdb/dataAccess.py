import os
from pkg_resources import resource_filename

try:
    import pyodbc
except ImportError:
    pyodbc = None

import numpy as np
import pandas

from . import info

import wqio


__all__ = [
    'Database',
]


def _handle_ND_factors(df, qualcol='qual', rescol='res', dlcol='DL', quals=None, nd_correction=2):
    if quals is None:
        quals = ['U', 'UK', 'UA', 'UC', 'K']

    normal_ND = [df[qualcol].isin(quals), float(nd_correction)]
    weird_UJ = [(df[qualcol] == 'UJ') & (df[rescol] < df[dlcol]), df[dlcol] / df[rescol]]
    return wqio.utils.selector(1, normal_ND, weird_UJ)


def _handle_ND_qualifiers(df, qualcol='qual', rescol='res', dlcol='DL', quals=None):
    if quals is None:
        quals = ['U', 'UA', 'UI', 'UC', 'UK', 'K']

    is_ND = df[qualcol].isin(quals) | ((df[qualcol] == 'UJ') & (df[rescol] < df[dlcol]))
    return np.where(is_ND, 'ND', '=')


def _process_screening(df, screencol):
    yes = df[screencol].str.lower().isin(['inc', 'yes'])
    no = df[screencol].str.lower().isin(['exc', 'no'])
    return np.select([yes, no], ['yes', 'no'], 'invalid')


def _process_sampletype(df, sampletype):
    grab = [df[sampletype].str.lower().str.contains('grab'), 'grab']
    composite = [df[sampletype].str.lower().str.contains('composite'), 'composite']
    return wqio.utils.selector('unknown', grab, composite)


def _check_levelnames(levels):
    good_levels = [
        'category', 'site', 'bmp', 'parameter',
        'sampletype', 'epazone', 'state', 'paramgroup'
    ]
    msg = 'valid levels are {}'.format(good_levels)

    for lvl in levels:
        if lvl not in good_levels:
            raise ValueError(msg)


def db_connection(dbfile, driver=None):
    if driver is None:
        driver = r'{Microsoft Access Driver (*.mdb, *.accdb)}'

    connection_string = r'Driver={};DBQ={}'.format(driver, os.path.abspath(dbfile))
    try:
        cnn = pyodbc.connect(connection_string)
        return cnn
    except:
        msg = "Unable to connect to {} using {}"
        raise RuntimeError(msg.format(dbfile, driver))


def get_data(cmd, dbfile, driver=None):
    with db_connection(dbfile, driver=driver) as cnn:
        return pandas.read_sql(cmd, cnn)


class Database(object):
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

    """
    def __init__(self, filename=None, dbtable=None, sqlquery=None,
                 catanalysis=False, useTex=True, ndscaler=None):

        self.file = filename or wqio.download('bmpdata')
        self.usingdb = os.path.splitext(self.file)[1] in ['.accdb', '.mdb']
        self.catanalysis = catanalysis
        self.useTex = useTex
        self.ndscaler = ndscaler or _handle_ND_factors

        # property initialization
        self.__data_raw = None
        self.__data_cleaned = None
        self.__data_final = None
        self._data = None

        if self.usingdb:
            self._sqlquery = sqlquery
            if dbtable is None:
                dbtable = 'bWQ BMP FlatFile BMP Indiv Anal_Rev 10-2014'
            self._dbtable = dbtable
            self.driver = r'{Microsoft Access Driver (*.mdb, *.accdb)}'
        else:
            self._sqlquery = None
            self._dbtable = None
            self.driver = None

        self._row_headers = [
            'category', 'epazone', 'state', 'site', 'bmp',
            'station', 'storm', 'sampletype', 'watertype',
            'paramgroup', 'units', 'parameter', 'fraction',
            'initialscreen', 'wqscreen', 'catscreen', 'balanced',
            'bmptype', 'pdf_id', 'site_id', 'bmp_id',
        ]

        self.agg_rules = {
            'res': 'mean',
            'qual': 'min',
            'sampledatetime': 'min'
        }

    @property
    def dbtable(self):
        return self._dbtable
    @dbtable.setter
    def dbtable(self, value):
        self._dbtable = value

    @property
    def sqlquery(self):
        if self._sqlquery is None:
            sqlfile = resource_filename('pybmpdb.data', 'default.sql')
            with open(sqlfile, 'r') as sql:
                self._sqlquery = sql.read().format(self.dbtable)
        return self._sqlquery
    @sqlquery.setter
    def sqlquery(self, value):
        self._sqlquery = value

    @property
    def _data_raw(self):
        if self.__data_raw is None:
            if self.usingdb:
                # SQL query text, execution, data retrieval
                df = get_data(self.sqlquery, self.file, driver=self.driver)
            else:
                df = pandas.read_csv(self.file, parse_dates=['sampledate'], encoding='utf-8')

        return df.fillna({'wq_qual': '='})

    @property
    def _data_cleaned(self):
        if self.__data_cleaned is None:
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

            biofilters = {
                'Biofilter - Grass Swale': 'Grass Swale',
                'Biofilter - Grass Strip': 'Grass Strip',
            }

            drop_columns = ['ms', '_parameter']
            self.__data_cleaned = (
                self._data_raw
                    .rename(columns=rename_columns)
                    .dropna(subset=['res'])
                    .assign(qual=lambda df: df['qual'].str.strip())
                    .assign(res=lambda df: df['res'] * _handle_ND_factors(df))
                    .assign(qual=lambda df: _handle_ND_qualifiers(df))
                    .assign(initialscreen=lambda df: _process_screening(df, 'initialscreen'))
                    .assign(wqscreen=lambda df: _process_screening(df, 'wqscreen'))
                    .assign(catscreen=lambda df: _process_screening(df, 'catscreen'))
                    .assign(station=lambda df: df['station'].str.lower())
                    .assign(sampletype=lambda df: _process_sampletype(df, 'sampletype'))
                    .assign(sampledatetime=lambda df: df.apply(wqio.utils.makeTimestamp, axis=1))
                    .assign(units=lambda df: df['units'].map(
                        lambda u: info.getUnits(u, attr='unicode')
                    ))
                    .assign(_parameter=lambda df: df['parameter'].str.lower().str.strip())
                    .assign(fraction=lambda df: df['fraction'].str.lower().str.strip())
                    .replace({'category': biofilters})
                    .pipe(wqio.utils.normalize_units, units_norm, target_units, paramcol='_parameter',
                          rescol='res', unitcol='units', napolicy='raise')
                    .drop(drop_columns, axis=1)
                    .query("res > 0")
            )

        return self.__data_cleaned

    @property
    def _data_final(self):
        if self.__data_final is None:
            self.__data_final = (
                self._data_cleaned
                    .groupby(by=self._row_headers)
                    .agg(self.agg_rules)
                    .set_index('sampledatetime', append=True)
            )
        return self.__data_final

    @property
    def data(self):
        if self._data is None:
            self._data = self._data_final
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

    def connect(self):
        if self.usingdb:
            return db_connection(self.file)
        else:
            raise ValueError("can't connect to {}".format(self.file))

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

        if self.useTex:
            parameters = [
                wqio.Parameter(
                    name=info.getParam(row['parameter'], attr='tex'),
                    units=info.getUnits(row['units'], attr='tex')
                ) for row in params_df.to_dict(orient='records')
            ]
        else:
            parameters = [
                wqio.Parameter(name=row['parameter'], units=row['units'])
                for row in params_df.to_dict(orient='records')
            ]

        return parameters

    def _check_for_parameters(self, parameter_names):
        if np.isscalar(parameter_names):
            parameter_names = [parameter_names]
        return np.all([p in self.params for p in parameter_names])

    def dbtable_to_csv(self, tablename, filepath=None):
        '''
        Converts all relevant tables in the DB to CSV files
        '''
        if not self.usingdb:
            raise NotImplementedError('`Database` source is not an Access Database')
        if filepath is None:
            filepath = 'bmpdb.csv'

        df = get_data(self.sqlquery, self.file, driver=self.driver)
        df.to_csv(filepath, index=False, encoding='utf-8')

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
            'epazone', 'state', 'station'
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

    def redefineBMPCategory(self, category, criteria, dropold=True):
        """ Redefine a selection of BMPs into another or new category

        Parameters
        ----------
        category : string
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

        self.data = wqio.utils.redefine_index_level(
            self.data, 'category', category,
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
        ...     lambda x, junk: wqio.utils.pH2concentration(x[('res', 'pH')]),
        ...     lambda x, junk: x[('qual', 'pH')], 'mg/L'
        ... )

        """

        index_name_cache = self.data.index.names
        existingparams = wqio.validate.at_least_empty_list(existingparams)

        params_exist = self._check_for_parameters(existingparams)
        if not params_exist:
            raise ValueError("Parameter %s is not in this dataset" % param)
        
        selection = (
            self.data
                .query("parameter in @existingparams")
                .reset_index()
                .set_index(index_name_cache)
                .unstack(level='parameter')
                .pipe(wqio.utils.assign_multilevel_column,
                      lambda df: qualfxn(df, existingparams),
                      'qual', newparam)
                .pipe(wqio.utils.assign_multilevel_column,
                      lambda df: resfxn(df, existingparams),
                      'res', newparam)
                .xs(newparam, level='parameter', axis='columns', drop_level=False)
                .stack(level='parameter')
        )

        indexMods = wqio.validate.at_least_empty_dict(indexMods, units=newunits)
        # add the units into indexMod, apply all changes
        indexMods['units'] = newunits
        for levelname, value in indexMods.items():
            selection = wqio.utils.redefine_index_level(
                selection,
                levelname,
                value,
                criteria=None,
                dropold=True
            )

        if newunits.lower() not in [u['name'].lower() for u in info.units]:
            info.units = info.addUnit(name=newunits)

        if newparam.lower() not in [p['name'].lower() for p in info.parameters]:
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
        def returnFiniteQual(df, existingparams):

            return np.where(
                ~df[('qual', existingparams[0])].isnull(), 
                df[('qual', existingparams[0])],
                df[('qual', existingparams[1])],
            )

        # function to return the right column of results
        def returnFiniteRes(df, existingparams):

            return np.where(
                ~df[('res', existingparams[0])].isnull(), 
                df[('res', existingparams[0])],
                df[('res', existingparams[1])],
            )

        self.transformParameters(existingparams, newparam, returnFiniteRes, returnFiniteQual, newunits)

    def to_DataCollection(self, selection_dict=None, **kwargs):
        selection_dict = wqio.validate.at_least_empty_dict(selection_dict)
        othergroups = kwargs.pop('othergroups', ['category', 'units'])
        pairgroups = kwargs.pop('pairgroups', ['category', 'units', 'bmp_id', 'site_id', 'storm'])
        return (
            self.select(**selection_dict)
                .reset_index()
                .pipe(
                    wqio.DataCollection,
                    rescol='res',
                    qualcol='qual',
                    ndval=['ND'],
                    stationcol='station',
                    paramcol='parameter',
                    othergroups=othergroups,
                    pairgroups=pairgroups,
                    **kwargs)
        )
