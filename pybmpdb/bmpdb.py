import os
from pkg_resources import resource_filename

try:
    import pyodbc
except ImportError:
    pyodbc = None

import numpy
import pandas
from engarde import checks

from . import info, utils

import wqio


__all__ = [
    'db_connection',
    'get_default_query',
    'get_data',
    'load_from_access',
    'load_from_csv',
    'prepare_data',
    'transform_parameters',
    'to_DataCollection'
]


def _handle_ND_factors(df, qualcol='qual', rescol='res', dlcol='DL', quals=None,
                       nd_correction=2):
    """ Determines the scaling factor to be applied to the water quality result
    based on the result qualifiers in the BMP Database.

    Parameters
    ----------
    df : pandas.DataFrame
    qualcol : str, optional (default = 'qual')
        The column in *df* that contain the qualifiers.
    rescol : str, optional (default = 'res')
        The column in *df* that contain the results.
    dlcol : str, optional (default = 'DL')
        The column in *df* that contain the detection limts.
    quals : list of str, optional.
        A list of qualifiers that signify that a result is non-detect. Falls
        back to ``['U', 'UK', 'UA', 'UC', 'K']`` when not provided.
    nd_correction : float, optional (default = 2.0)
        The factor by which non-detect results will be multiplied.

    Returns
    -------
    factors : numpy.array

    Notes
    -----
    The underlying assumption here is that the BMP Database reports non-detects
    at half of their detection limit. So we need to double the reported value
    to get the upper limit of the result for ROS/Kaplan-Meier imputation.

    Also note that there are some weird cases where UJ-flagged data should be
    given a different. This occurs when the reported result is greater than the
    reported DL. Lastly, UJ-flagged data where the result is less than the DL
    should be scaled by the ratio of the result to the DL, such that
    result * factor = DL.

    """

    quals = wqio.validate.at_least_empty_list(quals)
    if not quals:
        quals.extend(['U', 'UK', 'UA', 'UC', 'K'])

    normal_ND = [df[qualcol].isin(quals), float(nd_correction)]
    weird_UJ = [(df[qualcol] == 'UJ') & (df[rescol] < df[dlcol]), df[dlcol] / df[rescol]]
    return wqio.utils.selector(1, normal_ND, weird_UJ)


def _handle_ND_qualifiers(df, qualcol='qual', rescol='res', dlcol='DL', quals=None):
    """ Determines final qualifier to be applied to the water quality result
    based on the result qualifiers in the BMP Database. Non-detects get "ND",
    detected values get "=".

    Parameters
    ----------
    df : pandas.DataFrame
    qualcol : str, optional (default = 'qual')
        The column in *df* that contain the qualifiers.
    rescol : str, optional (default = 'res')
        The column in *df* that contain the results.
    dlcol : str, optional (default = 'DL')
        The column in *df* that contain the detection limts.
    quals : list of str, optional.
        A list of qualifiers that signify that a result is non-detect. Falls
        back to ``['U', 'UA', 'UI', 'UC', 'UK', 'K']`` when not provided.

    Returns
    -------
    qualifiers : numpy.array

    See also
    --------
    _handle_ND_factors

    Notes
    -----
    Same basic premise as _handle_ND_factors, but different qualifiers count
    as ND compared to what we used to determine the ND-scaling factors.

    """

    quals = wqio.validate.at_least_empty_list(quals)
    if not quals:
        quals.extend(['U', 'UA', 'UI', 'UC', 'UK', 'K'])

    is_ND = df[qualcol].isin(quals) | ((df[qualcol] == 'UJ') & (df[rescol] <= df[dlcol]))
    return numpy.where(is_ND, 'ND', '=')


def _process_screening(df, screencol):
    yes = df[screencol].str.lower().isin(['inc', 'yes'])
    no = df[screencol].str.lower().isin(['exc', 'no'])
    return wqio.utils.selector('invalid', [yes, 'yes'], [no, 'no'])


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
    """ Connect to an Access database with pyodbc

    Parameters
    dbfile : str
        Path to the Access database file
    driver : str, optional
        Database driver to be used by pyodbc. Defaults to
        "{Microsoft Access Driver (*.mdb, *.accdb)}"

    Returns
    -------
    connection

    """

    if driver is None:
        driver = r'{Microsoft Access Driver (*.mdb, *.accdb)}'

    connection_string = r'Driver={};DBQ={}'.format(driver, os.path.abspath(dbfile))
    try:
        cnn = pyodbc.connect(connection_string)
        return cnn
    except:
        msg = "Unable to connect to {} using {}"
        raise RuntimeError(msg.format(dbfile, driver))


def get_default_query():  # pragma: no cover
    """ Loads the default BMP Database query packaged with pybmpdb.
    """

    sqlfile = resource_filename('pybmpdb.data', 'default.sql')
    with open(sqlfile, 'r') as sql:
        sqlquery = sql.read()
    return sqlquery


def get_data(cmd, dbfile, driver=None):
    """ Fetch data from an Access database

    Parameters
    ----------
    cmd : str
        SQL (JET) query to run
    dbfile : str
        Path to the database file
    driver : str, optional
        Database driver for `pyodbc`

    Returns
    -------
    query_data : pandas.DataFrame

    """

    with db_connection(dbfile, driver=driver) as cnn:
        return pandas.read_sql(cmd, cnn)


def load_from_access(dbfile, sqlquery=None, dbtable=None):
    """ Load BMP performance data from the Access database

    Parameters
    ----------
    dbfile : str
        Path to the Access database.
    sqlquery : str, optional
        SQL (JET) query to run.

    Returns
    -------
    bmpdata : pandas.DataFrame

    """

    driver = r'{Microsoft Access Driver (*.mdb, *.accdb)}'
    if not sqlquery:
        if dbtable:
            sqlquery = "select * from {}".format(dbtable)
        else:
            dbtable = 'bWQ BMP FlatFile BMP Indiv Anal_Rev 10-2014'
            sqlquery = get_default_query().format(dbtable)

    return get_data(sqlquery, dbfile, driver=driver)


def load_from_csv(csvfile):
    return pandas.read_csv(csvfile, parse_dates=['sampledate'], encoding='utf-8')


def prepare_data(raw_df):
    _row_headers = [
        'category', 'epazone', 'state', 'site', 'bmp',
        'station', 'storm', 'sampletype', 'watertype',
        'paramgroup', 'units', 'parameter', 'fraction',
        'initialscreen', 'wqscreen', 'catscreen', 'balanced',
        'bmptype', 'pdf_id', 'ws_id', 'site_id', 'bmp_id',
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

    expected_rows = raw_df.loc[:, 'wq_value'].groupby(lambda x: x > 0).count().loc[True]

    biofilters = {
        'Biofilter - Grass Swale': 'Grass Swale',
        'Biofilter - Grass Strip': 'Grass Strip',
    }

    drop_columns = ['ms', '_parameter']
    prepped = (
        raw_df
            .fillna({'wq_qual': '='})
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
            .assign(units=lambda df: df['units'].map(lambda u: info.getUnits(u, attr='unicode')))
            .assign(_parameter=lambda df: df['parameter'].str.lower().str.strip())
            .assign(fraction=lambda df: numpy.where(df['_parameter'].str.lower().str.contains('dissolved'), 'dissolved', 'total'))
            .replace({'category': biofilters})
            .pipe(wqio.utils.normalize_units, units_norm, target_units, paramcol='_parameter',
                  rescol='res', unitcol='units', napolicy='raise')
            .drop(drop_columns, axis=1)
            .query("res > 0")
            .pipe(checks.none_missing, columns=_row_headers)
            .groupby(by=_row_headers)
            .agg({'res': 'mean', 'qual': 'min', 'sampledatetime': 'min'})
            .set_index('sampledatetime', append=True)
            .pipe(checks.unique_index)
    )
    return prepped


def transform_parameters(df, existingparams, newparam, newunits, resfxn, qualfxn,
                         indexMods=None, paramlevel='parameter'):
    """ Apply an arbitrary transformation to a parameter in the data

    Parameters
    ----------
    df : pandas.DataFrame
    existingparams : list of strings
        List of the existing parameters that will be used to compute
        the new values
    newparam : string
        Name of the new parameter to be generated
    newunits : string
        Units of the newly computed values
    resfxn : callable
        Function (or lambda) that will determine the result of
        ``newparam`` based on the values of ``existingparams``.
        Function must assume to be operating on a row of
        ``self.data`` with the elements of ``existingparams`` stored
        as columns.
    qualfxn : function
        Same as ``resfxn``, but for determining the final qualifier
        of the ``newparam`` results.
    indexMods : dict, optional (keys = index level names)
        Dictionary of index level name whose values are the new
        values of those levels where ``parameter == newparam``.

    Returns
    -------
    transformed : pandas.DataFrame

    """

    index_name_cache = df.index.names
    existingparams = wqio.validate.at_least_empty_list(existingparams)

    transformed = (
        df.query("{} in @existingparams".format(paramlevel))
          .pipe(utils.refresh_index)
          .unstack(level=paramlevel)
          .pipe(wqio.utils.assign_multilevel_column, qualfxn, 'qual', newparam)
          .pipe(wqio.utils.assign_multilevel_column, resfxn, 'res', newparam)
          .xs(newparam, level=paramlevel, axis='columns', drop_level=False)
          .stack(level=paramlevel)
    )

    indexMods = wqio.validate.at_least_empty_dict(indexMods, units=newunits)
    # add the units into indexMod, apply all changes
    indexMods['units'] = newunits
    for levelname, value in indexMods.items():
        transformed = wqio.utils.redefine_index_level(transformed, levelname, value,
                                                      criteria=None, dropold=True)

    # return the *full* dataset (preserving original params)
    result = pandas.concat([
        df.reset_index(),
        transformed.reset_index()
    ], sort=False).set_index(index_name_cache)
    return result


def to_DataCollection(df, **kwargs):  # pragma: no cover
    othergroups = kwargs.pop('othergroups', ['category', 'units'])
    pairgroups = kwargs.pop('pairgroups', ['category', 'units', 'bmp_id', 'site_id', 'storm'])
    dc = (
        df.reset_index()
          .pipe(wqio.DataCollection, rescol='res', qualcol='qual', ndval=['ND'],
                stationcol='station', paramcol='parameter', othergroups=othergroups,
                pairgroups=pairgroups, **kwargs)
    )
    return dc
