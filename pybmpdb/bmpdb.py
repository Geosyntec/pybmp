import os
import logging
from pkg_resources import resource_filename
from functools import partial
from pathlib import Path

try:
    import pyodbc
except ImportError:
    pyodbc = None

import numpy
import pandas
from engarde import checks

from . import info, utils

import wqio


__all__ = ["load_data", "transform_parameters", "paired_qual"]


_logger = logging.getLogger(__name__)


@wqio.utils.log_df_shape(_logger)
def _handle_ND_factors(
    df, qualcol="qual", rescol="res", dlcol="DL", quals=None, nd_correction=2
):
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
        quals.extend(["U", "UK", "UA", "UC", "K"])

    normal_ND = [df[qualcol].isin(quals), float(nd_correction)]
    weird_UJ = [
        (df[qualcol] == "UJ") & (df[rescol] < df[dlcol]),
        df[dlcol] / df[rescol],
    ]
    return wqio.utils.selector(1, normal_ND, weird_UJ)


@wqio.utils.log_df_shape(_logger)
def _handle_ND_qualifiers(df, qualcol="qual", rescol="res", dlcol="DL", quals=None):
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
        quals.extend(["U", "UA", "UI", "UC", "UK", "K"])

    is_ND = df[qualcol].isin(quals) | (
        (df[qualcol] == "UJ") & (df[rescol] <= df[dlcol])
    )
    return numpy.where(is_ND, "ND", "=")


@wqio.utils.log_df_shape(_logger)
def _process_screening(df, screencol):
    yes = df[screencol].str.lower().isin(["inc", "yes", "y"])
    no = df[screencol].str.lower().isin(["exc", "no", "n"])
    return wqio.utils.selector("invalid", [yes, "yes"], [no, "no"])


@wqio.utils.log_df_shape(_logger)
def _process_sampletype(df, sampletype):
    grab = [df[sampletype].str.lower().str.contains("grab"), "grab"]
    composite = [
        df[sampletype].str.lower().str.contains("emc")
        | df[sampletype].str.lower().str.contains("comp"),
        "composite",
    ]
    return wqio.utils.selector("unknown", grab, composite)


def _check_levelnames(levels):
    good_levels = [
        "category",
        "site",
        "bmp",
        "parameter",
        "sampletype",
        "epazone",
        "state",
        "paramgroup",
    ]
    msg = "valid levels are {}".format(good_levels)

    for lvl in levels:
        if lvl not in good_levels:
            raise ValueError(msg)


@wqio.utils.log_df_shape(_logger)
def transform_parameters(
    df,
    existingparams,
    newparam,
    newunits,
    resfxn,
    qualfxn,
    indexMods=None,
    paramlevel="parameter",
):
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
        .pipe(wqio.utils.assign_multilevel_column, qualfxn, "qual", newparam)
        .pipe(wqio.utils.assign_multilevel_column, resfxn, "res", newparam)
        .xs(newparam, level=paramlevel, axis="columns", drop_level=False)
        .stack(level=paramlevel)
    )

    indexMods = wqio.validate.at_least_empty_dict(indexMods, units=newunits)
    # add the units into indexMod, apply all changes
    indexMods["units"] = newunits
    for levelname, value in indexMods.items():
        transformed = wqio.utils.redefine_index_level(
            transformed, levelname, value, criteria=None, dropold=True
        )

    # return the *full* dataset (preserving original params)
    result = pandas.concat(
        [df.reset_index(), transformed.reset_index()], sort=False
    ).set_index(index_name_cache)
    return result


@wqio.utils.log_df_shape(_logger)
def paired_qual(df, qualin="qual_inflow", qualout="qual_outflow"):
    ND_neither = [(df[qualin] == "=") & (df[qualout] == "="), "Pair"]
    ND_in = [(df[qualin] == "ND") & (df[qualout] == "="), "Influent ND"]
    ND_out = [(df[qualin] == "=") & (df[qualout] == "ND"), "Effluent ND"]
    ND_both = [(df[qualin] == "ND") & (df[qualout] == "ND"), "Both ND"]
    return wqio.utils.selector("=", ND_neither, ND_in, ND_out, ND_both)


@wqio.utils.log_df_shape(_logger)
def _pick_non_null(df, maincol, preferred, secondary):
    return df[(maincol, preferred)].combine_first(df[(maincol, secondary)])


@wqio.utils.log_df_shape(_logger)
def _pick_best_station(df):
    def best_col(df, mainstation, backupstation, valcol):
        for sta in [mainstation, backupstation]:
            if (sta, valcol) not in df.columns:
                df = wqio.utils.assign_multilevel_column(df, numpy.nan, sta, valcol)

        return df[(mainstation, valcol)].combine_first(df[(backupstation, valcol)])

    orig_index = df.index.names
    data = (
        df.pipe(utils.refresh_index)
        .unstack(level="station")
        .pipe(wqio.utils.swap_column_levels, 0, 1)
        .pipe(
            wqio.utils.assign_multilevel_column,
            lambda df: best_col(df, "outflow", "subsurface", "res"),
            "final_outflow",
            "res",
        )
        .pipe(
            wqio.utils.assign_multilevel_column,
            lambda df: best_col(df, "outflow", "subsurface", "qual"),
            "final_outflow",
            "qual",
        )
        .pipe(
            wqio.utils.assign_multilevel_column,
            lambda df: best_col(df, "inflow", "reference outflow", "res"),
            "final_inflow",
            "res",
        )
        .pipe(
            wqio.utils.assign_multilevel_column,
            lambda df: best_col(df, "inflow", "reference outflow", "qual"),
            "final_inflow",
            "qual",
        )
        .loc[:, lambda df: df.columns.map(lambda c: "final_" in c[0])]
        .rename(columns=lambda col: col.replace("final_", ""))
        .stack(level="station")
    )

    return data


@wqio.utils.log_df_shape(_logger)
def _pick_best_sampletype(df):
    orig_cols = df.columns
    xtab = df.pipe(utils.refresh_index).unstack(level="sampletype")
    for col in orig_cols:
        grabvalues = numpy.where(
            xtab[(col, "composite")].isnull(), xtab[(col, "grab")], numpy.nan
        )
        xtab = wqio.utils.assign_multilevel_column(xtab, grabvalues, col, "grab")

    data = xtab.loc[:, xtab.columns.map(lambda c: c[1] != "unknown")].stack(
        level=["sampletype"]
    )
    return data


@wqio.utils.log_df_shape(_logger)
def _maybe_filter_onesided_BMPs(df, balanced_only):
    grouplevels = ["site", "bmp", "parameter", "category"]
    pivotlevel = "station"

    if balanced_only:
        return (
            df.unstack(level=pivotlevel)
            .groupby(level=grouplevels)
            .filter(lambda g: numpy.all(g["res"].describe().loc["count"] > 0))
            .stack(level=pivotlevel)
        )
    else:
        return df


@wqio.utils.log_df_shape(_logger)
def _filter_by_storm_count(df, minstorms):
    # filter out all monitoring stations with less than /N/ storms
    grouplevels = ["site", "bmp", "parameter", "station"]

    data = df.groupby(level=grouplevels).filter(lambda g: g.count()["res"] >= minstorms)
    return data


@wqio.utils.log_df_shape(_logger)
def _filter_by_BMP_count(df, minbmps):
    grouplevels = ["category", "parameter", "station"]

    data = df.groupby(level=grouplevels).filter(
        lambda g: g.index.get_level_values("bmp").unique().shape[0] >= minbmps
    )
    return data


@wqio.utils.log_df_shape(_logger)
def _maybe_combine_WB_RP(df, combine_WB_RP, catlevel="category"):
    if combine_WB_RP:
        # merge Wetland Basins and Retention ponds, keeping
        # the original records
        wbrp_indiv = ["Retention Pond", "Wetland Basin"]
        wbrp_combo = "Wetland Basin/Retention Pond"
        level_pos = utils.get_level_position(df, catlevel)
        return wqio.utils.redefine_index_level(
            df,
            catlevel,
            wbrp_combo,
            dropold=False,
            criteria=lambda row: row[level_pos] in wbrp_indiv,
        ).pipe(
            checks.verify_any,
            lambda df: df.index.get_level_values(catlevel) == wbrp_combo,
        )
    else:
        return df


@wqio.utils.log_df_shape(_logger)
def _maybe_combine_nox(
    df,
    combine_nox,
    paramlevel="parameter",
    rescol="res",
    qualcol="qual",
    finalunits="mg/L",
):
    if combine_nox:
        # combine NO3+NO2 and NO3 into NOx
        nitro_components = [
            "Nitrogen, Nitrite (NO2) + Nitrate (NO3) as N",
            "Nitrogen, Nitrate (NO3) as N",
        ]
        nitro_combined = "Nitrogen, NOx as N"

        picker = partial(
            _pick_non_null, preferred=nitro_components[0], secondary=nitro_components[1]
        )

        return transform_parameters(
            df,
            nitro_components,
            nitro_combined,
            finalunits,
            partial(picker, maincol=rescol),
            partial(picker, maincol=qualcol),
        ).pipe(
            checks.verify_any,
            lambda df: df.index.get_level_values(paramlevel) == nitro_combined,
        )
    else:
        return df


@wqio.utils.log_df_shape(_logger)
def _maybe_fix_PFCs(df, fix_PFCs, catlevel="category", typelevel="bmptype"):
    if fix_PFCs:
        PFC = "Permeable Friction Course"
        type_level_pos = utils.get_level_position(df, typelevel)
        return wqio.utils.redefine_index_level(
            df,
            catlevel,
            PFC,
            dropold=True,
            criteria=lambda row: row[type_level_pos] == "PF",
        ).pipe(checks.verify_any, lambda df: df.index.get_level_values(catlevel) == PFC)
    else:
        return df


@wqio.utils.log_df_shape(_logger)
def _maybe_remove_grabs(df, remove_grabs, grab_ok_bmps="default"):
    if remove_grabs:
        if grab_ok_bmps.lower() == "default":
            grab_ok_bmps = [
                "Retention Pond",
                "Wetland Basin",
                "Wetland Basin/Retention Pond",
            ]

        grab_ok_bmps = wqio.validate.at_least_empty_list(grab_ok_bmps)

        querytxt = (
            "(sampletype == 'composite') | "
            "(((category in @grab_ok_bmps) | (paramgroup == 'Biological')) & "
            "  (sampletype != 'unknown'))"
        )
        return df.query(querytxt)
    return df


def _load_raw_data(csvfile=None):
    csvfile = Path(csvfile or wqio.download("bmpdata"))
    return pandas.read_csv(csvfile, parse_dates=["sampledate"], encoding="utf-8")


@wqio.utils.log_df_shape(_logger)
def _clean_raw_data(raw_df, nd_correction=2):
    _row_headers = [
        "category",
        "epazone",
        "state",
        "site",
        "bmp",
        "station",
        "storm",
        "sampletype",
        "watertype",
        "paramgroup",
        "units",
        "parameter",
        "fraction",
        "wq_initialscreen",
        "ms_indivscreen",
        "wq_catscreen",
        "bmptype",
        "ws_id",
        "site_id",
        "bmp_id",
        "dot_type",
    ]

    units_norm = {u["unicode"]: info.getNormalization(u["name"]) for u in info.units}

    target_units = {
        p["name"].lower(): info.getUnitsFromParam(p["name"], attr="unicode")
        for p in info.parameters
    }

    expected_rows = raw_df.loc[:, "res"].groupby(lambda x: x > 0).count().loc[True]

    drop_columns = ["ms", "_parameter"]
    prepped = (
        raw_df.fillna({"qual": "="})
        .dropna(subset=["res"])
        .assign(qual=lambda df: df["qual"].str.strip())
        .assign(
            res=lambda df: df["res"]
            * _handle_ND_factors(df, nd_correction=nd_correction)
        )
        .assign(qual=lambda df: _handle_ND_qualifiers(df))
        .assign(wq_initialscreen=lambda df: _process_screening(df, "wq_initialscreen"))
        .assign(ms_indivscreen=lambda df: _process_screening(df, "ms_indivscreen"))
        .assign(wq_catscreen=lambda df: _process_screening(df, "wq_catscreen"))
        .assign(station=lambda df: df["station"].str.lower())
        .assign(sampletype=lambda df: _process_sampletype(df, "sampletype"))
        .assign(sampledatetime=lambda df: df.apply(wqio.utils.makeTimestamp, axis=1))
        .assign(
            units=lambda df: df["units"].map(lambda u: info.getUnits(u, attr="unicode"))
        )
        .assign(_parameter=lambda df: df["parameter"].str.lower().str.strip())
        .assign(
            fraction=lambda df: numpy.where(
                df["_parameter"].str.contains("dissolved"), "dissolved", "total"
            )
        )
        .pipe(
            wqio.utils.normalize_units,
            units_norm,
            target_units,
            paramcol="_parameter",
            rescol="res",
            unitcol="units",
            napolicy="raise",
        )
        .drop(drop_columns, axis=1)
        .query("res > 0")
        .pipe(checks.none_missing, columns=_row_headers)
        .groupby(by=_row_headers)
        .agg({"res": "mean", "qual": "min", "sampledatetime": "min"})
        .set_index("sampledatetime", append=True)
        .pipe(checks.unique_index)
    )
    return prepped


@wqio.utils.log_df_shape(_logger)
def _prepare_for_summary(
    df,
    minstorms=3,
    minbmps=3,
    combine_nox=True,
    combine_WB_RP=True,
    remove_grabs=True,
    grab_ok_bmps="default",
    balanced_only=True,
    fix_PFCs=True,
    excluded_bmps=None,
    excluded_params=None,
):
    """ Prepare data for categorical summaries

    Parameter
    ---------
    df : pandas.DataFrame
    minstorms : int (default = 3)
        Minimum number of storms (monitoring events) for a BMP study to be included
    minbmps : int (default = 3)
        Minimum number of BMP studies for a parameter to be included
    combine_nox : bool (default = True)
        Toggles combining NO3 and NO2+NO3 into as new parameter NOx, giving
        preference to NO2+NO3 when both parameters are observed for an event.
        The underlying assuption is that NO2 concentrations are typically much
        smaller than NO3, thus NO2+NO3 ~ NO3.
    combine_WB_RP : bool (default = True)
        Toggles combining Retention Pond and Wetland Basin data into a new
        BMP category: Retention Pond/Wetland Basin.
    remove_grabs : bool (default = True)
        Toggles removing grab samples from the dataset except for:
          - biological parameters
          - BMPs categories that are whitelisted via *grab_ok_bmps*
    grab_ok_bmps : sequence of str, optional
        BMP categories for which grab data should be included. By default, this
        inclues Retention Ponds, Wetland Basins, and the combined
        Retention Pond/Wetland Basin category created when *combine_WB_RP* is
        True.
    balanced_only : bool (default = True)
        Toggles removing BMP studies which have only influent or effluent data,
        exclusively.
    fix_PFCs : bool (default = True)
        Makes correction to the category of Permeable Friction Course BMPs
    excluded_bmps, excluded_params : sequence of str, optional
        List of BMPs studies and parameters to exclude from the data.

    Returns
    -------
    summarizable : pandas.DataFrame

    """

    excluded_bmps = wqio.validate.at_least_empty_list(excluded_bmps)
    excluded_params = wqio.validate.at_least_empty_list(excluded_params)

    return (
        df.pipe(_maybe_combine_WB_RP, combine_WB_RP)
        .pipe(_maybe_combine_nox, combine_nox)
        .pipe(_maybe_fix_PFCs, fix_PFCs)
        .pipe(_maybe_remove_grabs, remove_grabs, grab_ok_bmps)
        .query("bmp not in @excluded_bmps")
        .query("parameter not in @excluded_params")
        .pipe(_pick_best_sampletype)
        .pipe(_pick_best_station)
        .pipe(_maybe_filter_onesided_BMPs, balanced_only)
        .pipe(_filter_by_storm_count, minstorms)
        .pipe(_filter_by_BMP_count, minbmps)
    )


def load_data(
    datapath=None,
    minstorms=3,
    minbmps=3,
    combine_nox=True,
    combine_WB_RP=True,
    remove_grabs=True,
    grab_ok_bmps="default",
    balanced_only=True,
    fix_PFCs=True,
    excluded_bmps=None,
    excluded_params=None,
    as_dataframe=False,
    **dc_kwargs
):
    """ Prepare data for categorical summaries

    Parameter
    ---------
    datapath : Path-like, optional
        Path to the raw data CSV. If not provided, the latest data will be
        downloaded.
    minstorms : int (default = 3)
        Minimum number of storms (monitoring events) for a BMP study to be included
    minbmps : int (default = 3)
        Minimum number of BMP studies for a parameter to be included
    combine_nox : bool (default = True)
        Toggles combining NO3 and NO2+NO3 into as new parameter NOx, giving
        preference to NO2+NO3 when both parameters are observed for an event.
        The underlying assuption is that NO2 concentrations are typically much
        smaller than NO3, thus NO2+NO3 ~ NO3.
    combine_WB_RP : bool (default = True)
        Toggles combining Retention Pond and Wetland Basin data into a new
        BMP category: Retention Pond/Wetland Basin.
    remove_grabs : bool (default = True)
        Toggles removing grab samples from the dataset except for:
          - biological parameters
          - BMPs categories that are whitelisted via *grab_ok_bmps*
    grab_ok_bmps : sequence of str, optional
        BMP categories for which grab data should be included. By default, this
        inclues Retention Ponds, Wetland Basins, and the combined
        Retention Pond/Wetland Basin category created when *combine_WB_RP* is
        True.
    balanced_only : bool (default = True)
        Toggles removing BMP studies which have only influent or effluent data,
        exclusively.
    fix_PFCs : bool (default = True)
        Makes correction to the category of Permeable Friction Course BMPs
    excluded_bmps, excluded_params : sequence of str, optional
        List of BMPs studies and parameters to exclude from the data.
    as_dataframe : bool (default = False)
        When False, a wqio.DataCollection is returned

    Additional Parameters
    ---------------------
    Any additional keword arguments will be passed to wqio.DataCollection.

    Returns
    -------
    bmp : pandas.DataFrame or wqio.DataCollection

    """
    othergroups = dc_kwargs.pop("othergroups", ["category", "units"])
    pairgroups = dc_kwargs.pop(
        "pairgroups", ["category", "units", "bmp_id", "site_id", "storm"]
    )
    rescol = dc_kwargs.pop("rescol", "res")
    qualcol = dc_kwargs.pop("qualcol", "qual")
    ndval = dc_kwargs.pop("ndval", ["ND", "<"])
    stationcol = dc_kwargs.pop("stationcol", "station")
    paramcol = dc_kwargs.pop("paramcol", "parameter")
    bmp = (
        _load_raw_data(datapath)
        .pipe(_clean_raw_data)
        .pipe(
            _prepare_for_summary,
            minstorms=minstorms,
            minbmps=minbmps,
            combine_nox=combine_nox,
            combine_WB_RP=combine_WB_RP,
            remove_grabs=remove_grabs,
            grab_ok_bmps=grab_ok_bmps,
            balanced_only=balanced_only,
            fix_PFCs=fix_PFCs,
            excluded_bmps=excluded_bmps,
            excluded_params=excluded_params,
        )
    )
    if as_dataframe:
        return bmp
    return wqio.DataCollection(
        bmp,
        rescol=rescol,
        qualcol=qualcol,
        ndval=ndval,
        stationcol=stationcol,
        paramcol=paramcol,
        othergroups=othergroups,
        pairgroups=pairgroups,
        **dc_kwargs
    )
