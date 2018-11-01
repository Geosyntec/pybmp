import os
import sys
from pkg_resources import resource_filename
from functools import partial

import numpy
import matplotlib
from matplotlib import pyplot
import seaborn
import pandas
from statsmodels.tools.decorators import (
    resettable_cache, cache_readonly
)
from engarde import checks

import wqio

from . import bmpdb, info, utils
try:
    from tqdm import tqdm
except ImportError:
    tdqm = wqio.utils.misc.no_op


def filterlocation(location, count=5, column='bmp'):
    location.filtered_data = (
        location.filtered_data
        .groupby(level=column)
        .filter(lambda g: g.count() >= count)
    )

    location.include = (
        location.filtered_data
                .index
                .get_level_values(column)
                .unique()
                .shape[0]
    ) >= count


def _pick_non_null(df, maincol, preferred, secondary):
    return df[(maincol, preferred)].combine_first(df[(maincol, secondary)])


def _pick_best_station(df):
    def best_col(df, mainstation, backupstation, valcol):
        for sta in [mainstation, backupstation]:
            if (sta, valcol) not in df.columns:
                df = wqio.utils.assign_multilevel_column(df, numpy.nan, sta, valcol)

        return df[(mainstation, valcol)].combine_first(df[(backupstation, valcol)])

    orig_index = df.index.names
    data = (
        df.pipe(utils.refresh_index)
          .unstack(level='station')
          .pipe(wqio.utils.swap_column_levels, 0, 1)
          .pipe(wqio.utils.assign_multilevel_column,
                lambda df: best_col(df, 'outflow', 'subsurface', 'res'),
                'final_outflow', 'res')
          .pipe(wqio.utils.assign_multilevel_column,
                lambda df: best_col(df, 'outflow', 'subsurface', 'qual'),
                'final_outflow', 'qual')
          .pipe(wqio.utils.assign_multilevel_column,
                lambda df: best_col(df, 'inflow', 'reference outflow', 'res'),
                'final_inflow', 'res')
          .pipe(wqio.utils.assign_multilevel_column,
                lambda df: best_col(df, 'inflow', 'reference outflow', 'qual'),
                'final_inflow', 'qual')
          .loc[:, lambda df: df.columns.map(lambda c: 'final_' in c[0])]
          .rename(columns=lambda col: col.replace('final_', ''))
          .stack(level='station')
    )

    return data


def _pick_best_sampletype(df):
    orig_cols = df.columns
    xtab = df.pipe(utils.refresh_index).unstack(level='sampletype')
    for col in orig_cols:
        grabvalues = numpy.where(
            xtab[(col, 'composite')].isnull(),
            xtab[(col, 'grab')],
            numpy.nan
        )
        xtab = wqio.utils.assign_multilevel_column(xtab, grabvalues, col, 'grab')

    data = (
        xtab.loc[:, xtab.columns.map(lambda c: c[1] != 'unknown')]
            .stack(level=['sampletype'])
    )
    return data


def _maybe_filter_onesided_BMPs(df, balanced_only):
    grouplevels = ['site', 'bmp', 'parameter', 'category']
    pivotlevel = 'station'

    if balanced_only:
        return (
            df.unstack(level=pivotlevel)
              .groupby(level=grouplevels)
              .filter(lambda g: numpy.all(g['res'].describe().loc['count'] > 0))
              .stack(level=pivotlevel)
        )
    else:
        return df


def _filter_by_storm_count(df, minstorms):
    # filter out all monitoring stations with less than /N/ storms
    grouplevels = ['site', 'bmp', 'parameter', 'station']

    data = (
        df.groupby(level=grouplevels)
          .filter(lambda g: g.count()['res'] >= minstorms)
    )
    return data


def _filter_by_BMP_count(df, minbmps):
    grouplevels = ['category', 'parameter', 'station']

    data = (
        df.groupby(level=grouplevels)
          .filter(lambda g: g.index.get_level_values('bmp').unique().shape[0] >= minbmps)
    )
    return data


def _maybe_combine_WB_RP(df, combine_WB_RP, catlevel='category'):
    if combine_WB_RP:
        # merge Wetland Basins and Retention ponds, keeping
        # the original records
        wbrp_indiv = ['Retention Pond', 'Wetland Basin']
        wbrp_combo = 'Wetland Basin/Retention Pond'
        level_pos = utils.get_level_position(df, catlevel)
        return wqio.utils.redefine_index_level(
            df, catlevel, wbrp_combo, dropold=False,
            criteria=lambda row: row[level_pos] in wbrp_indiv
        ).pipe(
            checks.verify_any,
            lambda df: df.index.get_level_values(catlevel) == wbrp_combo
        )
    else:
        return df


def _maybe_combine_nox(df, combine_nox, paramlevel='parameter', rescol='res',
                       qualcol='qual', finalunits='mg/L'):
    if combine_nox:
        # combine NO3+NO2 and NO3 into NOx
        nitro_components = [
            'Nitrogen, Nitrite (NO2) + Nitrate (NO3) as N',
            'Nitrogen, Nitrate (NO3) as N'
        ]
        nitro_combined = 'Nitrogen, NOx as N'

        picker = partial(_pick_non_null, preferred=nitro_components[0],
                         secondary=nitro_components[1])

        return bmpdb.transform_parameters(
            df, nitro_components, nitro_combined, finalunits,
            partial(picker, maincol=rescol), partial(picker, maincol=qualcol)
        ).pipe(
            checks.verify_any,
            lambda df: df.index.get_level_values(paramlevel) == nitro_combined
        )


def _maybe_fix_PFCs(df, fix_PFCs, catlevel='category', typelevel='bmptype'):
    if fix_PFCs:
        PFC = 'Permeable Friction Course'
        type_level_pos = utils.get_level_position(df, typelevel)
        return wqio.utils.redefine_index_level(
            df, catlevel, PFC, dropold=True, criteria=lambda row: row[type_level_pos] == 'PF'
        ).pipe(
            checks.verify_any,
            lambda df: df.index.get_level_values(catlevel) == PFC
        )
    else:
        return df


def _maybe_remove_grabs(df, remove_grabs, grab_ok_bmps):
    if remove_grabs:
        querytxt = (
            "(sampletype == 'composite') | "
            "(((category in @grab_ok_bmps) | (paramgroup == 'Biological')) & "
            "  (sampletype != 'unknown'))"
        )
        return df.query(querytxt)
    else:
        return df


def prep_for_summary(df, minstorms=3, minbmps=3, combine_nox=True, combine_WB_RP=True,
                     remove_grabs=True, grab_ok_bmps='default', balanced_only=True,
                     fix_PFCs=True, excluded_bmps=None, excluded_params=None):
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
          * biological parameters
          * BMPs categories that are whitelisted via *grab_ok_bmps
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

    if grab_ok_bmps == 'default':
        grab_ok_bmps = ['Retention Pond', 'Wetland Basin', 'Wetland Basin/Retention Pond']

    grab_ok_bmps = wqio.validate.at_least_empty_list(grab_ok_bmps)
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


def paired_qual(df, qualin='qual_inflow', qualout='qual_outflow'):
    ND_neither = [(df[qualin] == '=') & (df[qualout] == '='), 'Pair']
    ND_in = [(df[qualin] == 'ND') & (df[qualout] == '='), 'Influent ND']
    ND_out = [(df[qualin] == '=') & (df[qualout] == 'ND'), 'Effluent ND']
    ND_both = [(df[qualin] == 'ND') & (df[qualout] == 'ND'), 'Both ND']
    return wqio.utils.selector('=', ND_neither, ND_in, ND_out, ND_both)


def setMPLStyle(serif=False):
    if serif:
        fontfamily = 'serif'
        preamble = [
            r'\usepackage{siunitx}',
            r'\sisetup{detect-all}',
            r'\usepackage{fourier}'
        ]
    else:
        fontfamily = 'sans-serif'
        preamble = [
            r'\usepackage{siunitx}',
            r'\sisetup{detect-all}',
            r'\usepackage{helvet}',
            r'\usepackage{sansmath}',
            r'\sansmath'
        ]
    style_dict = {
        'text.usetex': True,
        'font.family': [fontfamily],
        'font.serif': ['Utopia', 'Palantino'],
        'font.sans-serif': ['Helvetica', 'Arial'],
        'lines.linewidth': 0.5,
        'patch.linewidth': 0.5,
        'text.latex.preamble': preamble,
        'axes.linewidth': 0.5,
        'axes.grid': True,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'xtick.labelsize': 10,
        'xtick.direction': 'out',
        'ytick.labelsize': 10,
        'ytick.direction': 'out',
        'grid.linewidth': 0.5,
        'legend.fancybox': True,
        'legend.numpoints': 1,
        'legend.fontsize': 8,
        'figure.figsize': (6.5, 3.5),
        'savefig.dpi': 300
    }
    matplotlib.rcParams.update(style_dict)


class DatasetSummary(object):
    def __init__(self, dataset, paramgroup, figpath, forcepaths=False):
        self.forcepaths = forcepaths
        self.figpath = figpath
        self.paramgroup = paramgroup
        self.ds = dataset
        self.parameter = self.ds.definition['parameter']
        self.parameter.usingTex = True
        self.bmp = self.ds.definition['category']

        # properties
        self._latex_file_name = None
        self._scatter_fig_path = None
        self._scatter_fig_name = None
        self._stat_fig_path = None
        self._stat_fig_name = None

    @property
    def latex_file_name(self):
        if self._latex_file_name is None:
            self._latex_file_name = utils.processFilename('{}_{}_{}'.format(
                self.paramgroup, self.bmp, self.parameter.name
            )).lower()
        return self._latex_file_name

    @latex_file_name.setter
    def latex_file_name(self, value):
        self._latex_file_name = value

    @property
    def scatter_fig_path(self):
        if self._scatter_fig_path is None:
            self._scatter_fig_path = self.figpath + '/scatterplot'
            if not os.path.exists(self._scatter_fig_path) and self.forcepaths:
                os.mkdir(self._scatter_fig_path)
        return self._scatter_fig_path

    @property
    def scatter_fig_name(self):
        if self._scatter_fig_name is None:
            figname = utils.processFilename('{}_scatter.pdf'.format(self.latex_file_name))
            self._scatter_fig_name = self.scatter_fig_path + '/' + figname
        return self._scatter_fig_name

    @scatter_fig_name.setter
    def scatter_fig_name(self, value):
        self._scatter_fig_name = value

    @property
    def stat_fig_path(self):
        if self._stat_fig_path is None:
            self._stat_fig_path = self.figpath + '/statplot'
            if not os.path.exists(self._stat_fig_path) and self.forcepaths:
                os.mkdir(self._stat_fig_path)
        return self._stat_fig_path

    @property
    def stat_fig_name(self):
        if self._stat_fig_name is None:
            figname = utils.processFilename('{}_stats.pdf'.format(self.latex_file_name))
            self._stat_fig_name = self.stat_fig_path + '/' + figname
        return self._stat_fig_name

    @stat_fig_name.setter
    def stat_fig_name(self, value):
        self._stat_fig_name = value

    def _tex_table_row(self, name, attribute, rule='mid', twoval=False,
                       sigfigs=3, ci=False, fromdataset=False, pval=False,
                       tex=False, forceint=False):
        rulemap = {
            'top': '\\toprule',
            'mid': '\\midrule',
            'bottom': '\\bottomrule',
            'none': '%%',
        }

        try:
            thisrule = rulemap[rule]
        except KeyError:
            raise KeyError('top, mid, bottom rules or none allowed')

        if fromdataset:
            if self.ds.effluent.include and self.ds.influent.include:
                val = wqio.utils.sigFigs(getattr(self.ds, attribute), sigfigs,
                                         pval=pval, tex=tex, forceint=forceint)
            else:
                val = 'NA'

            formatter = dict(ruler=thisrule, name=name, value=val)
            row = r"""
                {ruler}
                {name} & \multicolumn{{2}}{{c}} {{{value}}} \\"""
        else:
            valstrings = []
            for loc in [self.ds.influent, self.ds.effluent]:
                if loc.include:
                    if hasattr(attribute, 'append'):
                        val = [getattr(loc, attr)
                               for attr in attribute]
                    else:
                        val = getattr(loc, attribute)

                    if val is not None:
                        if twoval:
                            thisstring = '{}; {}'.format(
                                wqio.utils.sigFigs(val[0], sigfigs, pval=pval,
                                                   tex=tex, forceint=forceint),
                                wqio.utils.sigFigs(val[1], sigfigs, pval=pval,
                                                   tex=tex, forceint=forceint)
                            )

                            if ci:
                                thisstring = '({})'.format(thisstring)
                        else:
                            thisstring = wqio.utils.sigFigs(
                                val, sigfigs, pval=pval,
                                tex=tex, forceint=forceint
                            )

                    else:
                        thisstring = 'NA'
                else:
                    thisstring = 'NA'

                valstrings.append(thisstring)

            formatter = dict(
                ruler=thisrule,
                name=name,
                val_in=valstrings[0],
                val_out=valstrings[1]
            )
            row = r"""
                {ruler}
                {name} & {val_in} & {val_out} \\"""

        return row.format(**formatter)

    def _make_tex_table(self, tabletitle):
        '''
        Generate a LaTeX table comparing the stats of `self.influent`
            and `self.effluent`.

        Parameters
        ----------
        tabletitle : string
            Title of the table as it should appear in a LaTeX document.

        Writes
        ------

        Returns
        -------
        stattable : string
            The LaTeX commands for the statsummary table.

        '''
        stattable = r"""
        \begin{table}[h!]
            \caption{%s}
            \centering
            \begin{tabular}{l l l l l}
                \toprule
                \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\""" % tabletitle

        stats = [
            {'name': 'Count', 'attribute': 'N', 'rule': 'top', 'forceint': True},
            {'name': 'Number of NDs', 'attribute': 'ND', 'forceint': True},
            {'name': 'Min; Max', 'attribute': ['min', 'max'], 'twoval': True},
            {'name': 'Mean', 'attribute': 'mean', },
            {
                'name': '(95\% confidence interval)',
                'attribute': 'mean_conf_interval',
                'twoval': True, 'ci': True, 'rule': 'none'
            },
            {'name': 'Standard Deviation', 'attribute': 'std', },
            {'name': 'Log. Mean', 'attribute': 'logmean', },
            {
                'name': '(95\% confidence interval)',
                'attribute': 'logmean_conf_interval',
                'twoval': True, 'ci': True, 'rule': 'none'
            },
            {'name': 'Log. Standard Deviation', 'attribute': 'logstd', },
            {'name': 'Geo. Mean', 'attribute': 'geomean', },
            {
                'name': '(95\% confidence interval)',
                'attribute': 'geomean_conf_interval',
                'twoval': True, 'ci': True, 'rule': 'none'
            },
            {'name': 'Coeff. of Variation', 'attribute': 'cov', },
            {'name': 'Skewness', 'attribute': 'skew', },
            {'name': 'Median', 'attribute': 'median', },
            {
                'name': '(95\% confidence interval)',
                'attribute': 'median_conf_interval',
                'twoval': True, 'ci': True, 'rule': 'none'
            },
            {
                'name': 'Quartiles',
                'attribute': ['pctl25', 'pctl75'],
                'twoval': True,
            },
            {
                'name': 'Number of Pairs', 'attribute': 'n_pairs',
                'rule': 'top', 'fromdataset': True,
                'sigfigs': 1, 'forceint': True
            },
            {
                'name': 'Wilcoxon p-value', 'attribute': 'wilcoxon_p',
                'fromdataset': True, 'pval': True, 'tex': True
            },
            {
                'name': 'Mann-Whitney p-value', 'attribute': 'mannwhitney_p',
                'fromdataset': True, 'pval': True, 'tex': True
            },
        ]
        for s in stats:
            stattable += self._tex_table_row(**s)

        stattable += r"""
                \bottomrule
            \end{tabular}
        \end{table}"""

        return stattable + '\n'

    # doesn't need to be a class method yet
    def _make_tex_figure(self, filename, caption, position='hb', clearpage=True):
        '''
        Create the LaTeX for include a figure in a document

        Parameters
        ----------
        filename : string
            Path to the image you want to include
        caption : string
            Caption tp appear below the figure
        position : string (default = 'hb')
            Valid LaTeX "float" placement preference
            (h=here, b=bottom, t=top, !=priority)
        clearpage  : bool (default = True)
            Toggles the LaTeX command "\clearpage" after the figure

        Writes
        ------
        None

        Returns
        -------
        figurestring : string
            The LaTeX string to include a figure in a document

        '''

        if clearpage:
            clrpage = ' \\clearpage\n'
        else:
            clrpage = '\n'
        figurestring = r"""
        \begin{figure}[%s]   %% FIGURE
            \centering
            \includegraphics[scale=1.00]{%s}
            \caption{%s}
        \end{figure}%s""" % (position, filename, caption, clrpage)
        return figurestring

    def makeTexInput(self, tabletitle, subsection=True):
        '''
        Creates an input file for a dataset  including a
            summary table, stat plot, and scatter plot.

        Parameters
        ----------
        figpath : string
            Path to teh figure relative to the current directory
        subsection : bool (default = True)
            Toggles the data going in its own subsection in the document

        Writes
        ------
        A full LaTeX input file for inclusion in a final or draft template

        Returns
        -------
        filename : string
            Filename and path of the file that is written

        '''
        tablestring = ''

        # if there's enough effluent data
        if self.ds.effluent.include:
            if subsection:
                tablestring += r'\subsection{%s}' % (self.bmp,)

            # caption for the stats plot
            prob_caption = 'Box and Probability Plots of {} at {} BMPs'.format(
                self.parameter.name,
                self.bmp
            )

            # caption for the scatter plot
            scatter_caption = 'Influent vs. Effluent Plots of {} at {} BMPs'.format(
                self.parameter.name,
                self.bmp
            )

            # warning about having a lot of non-detects
            warning = '''
            Warning: there is a very high percentage of non-detects in
            this data set. The hypothesis test results and other
            statistics reported in this table may not be valid.
            '''

            # make the table and write it to the output file
            tablestring += self._make_tex_table(tabletitle)

            # if less than 80% of the data is ND
            if self.ds.effluent.ND / self.ds.effluent.N <= 0.8:

                # make the stat plot string
                statfig = self._make_tex_figure(
                    self.stat_fig_name, prob_caption, clearpage=False
                )

                # make the scatter plot string
                scatterfig = self._make_tex_figure(
                    self.scatter_fig_name, scatter_caption, clearpage=True
                )

                # write the strings to the file
                tablestring += statfig
                tablestring += scatterfig

            else:
                # if there are too many non-detect,
                # issue the warning
                tablestring += warning

        return tablestring


class CategoricalSummary(object):
    def __init__(self, datasets, paramgroup, basepath, figpath,
                 showprogress=False, applyfilters=False,
                 filtercount=5, filtercolumn='bmp'):
        self._cache = resettable_cache()
        self._applyfilters = applyfilters
        self.filtercount = filtercount
        self.filtercolumn = filtercolumn
        self._raw_datasets = [ds for ds in filter(
            lambda x: x.effluent.include,
            datasets
        )]
        self.basepath = basepath
        self.figpath = figpath
        self.showprogress = showprogress
        self.parameters = [ds.definition['parameter'] for ds in self.datasets]
        self.bmps = [ds.definition['category'] for ds in self.datasets]
        self.paramgroup = paramgroup

    @cache_readonly
    def datasets(self):
        if self._applyfilters:
            filtered_datasets = []
            for ds in self._raw_datasets:
                filterlocation(ds.effluent, count=self.filtercount,
                               column=self.filtercolumn)

                filterlocation(ds.influent, count=self.filtercount,
                               column=self.filtercolumn)

                ds.include = ds.effluent.include

                if ds.include:
                    filtered_datasets.append(ds)
        else:
            filtered_datasets = self._raw_datasets

        return filtered_datasets

    def _make_input_file_IO(self, inputIO, regenfigs=True):

        figoptions = dict(dpi=600, bbox_inches='tight', transparent=True)

        if self.showprogress:
            pbar = utils.ProgressBar(self.datasets)

        old_param = 'pure garbage'
        for n, ds in enumerate(self.datasets, 1):
            dsum = DatasetSummary(ds, self.paramgroup, self.figpath)
            new_param = dsum.parameter.name

            tabletitle = 'Statistics for {} at {} BMPs'.format(
                dsum.parameter.paramunit(), dsum.bmp
            )
            latex_input = ''
            if old_param != new_param:
                latex_input = '\\section{%s}\n' % dsum.parameter.name

            latex_input += dsum.makeTexInput(tabletitle, subsection=True)
            latex_input += '\\clearpage\n'

            if regenfigs:
                statfig = ds.statplot(
                    ylabel=dsum.parameter.paramunit(),
                    bacteria=(self.paramgroup == 'Bacteria'),
                    axtype='prob'
                )
                scatterfig = ds.scatterplot(
                    xlabel='Influent ' + dsum.parameter.paramunit(),
                    ylabel='Effluent ' + dsum.parameter.paramunit(),
                    one2one=True
                )

                statpath = os.path.join(self.basepath, dsum.stat_fig_name)
                statfig.savefig(statpath, **figoptions)

                scatterpath = os.path.join(self.basepath, dsum.scatter_fig_name)
                scatterfig.savefig(scatterpath, **figoptions)

            inputIO.write(latex_input)
            pyplot.close('all')

            old_param = new_param

            if self.showprogress:
                pbar.animate(n)

    def _make_report_IO(self, templateIO, inputpath, reportIO, report_title):
        inputname = os.path.basename(inputpath)

        documentstring = templateIO.read().replace('__VARTITLE', report_title)
        documentstring += '\n\\input{%s}\n\\end{document}\n' % (inputname,)

        reportIO.write(documentstring)

    def makeReport(self, templatepath, inputpath, reportpath, report_title,
                   regenfigs=True):

        with open(inputpath, 'w') as inputIO:
            self._make_input_file_IO(inputIO, regenfigs=regenfigs)

        with open(templatepath, 'r') as templateIO:
            with open(reportpath, 'w') as reportIO:
                self._make_report_IO(
                    templateIO,
                    inputpath,
                    reportIO,
                    report_title
                )


def _proxy_inflow_outflow(dataset):
    from matplotlib.lines import Line2D
    infl_color = dataset.influent.color
    infl = Line2D([], [], color=infl_color, linestyle='-', linewidth=1.75,
                  marker='o', markerfacecolor='white',
                  markeredgewidth=1.25, markeredgecolor=infl_color)
    effl_color = dataset.effluent.color
    effl = Line2D([], [], color=effl_color, linestyle='-', linewidth=1.75,
                  marker='s', markerfacecolor='white',
                  markeredgewidth=1.25, markeredgecolor=effl_color)
    return infl, effl


def categorical_boxplots(dc, outpath='.'):
    param = None
    bmplabels = sorted(dc.tidy['category'].unique())

    matplotlib.rc("lines", markeredgewidth=0.5)

    # positions of the ticks
    bmppositions = numpy.arange(1, len(bmplabels) + 1) * 2
    pos_map = dict(zip(bmplabels, bmppositions))

    paramunits = (
        dc.tidy[['parameter', 'paramgroup', 'units']]
          .drop_duplicates()
          .to_dict(orient='records')
    )
    for pu in paramunits:
        parameter = pu['parameter']
        group = pu['paramgroup']
        units = pu['units']
        param = wqio.Parameter(name=parameter, units=units)
        fig, ax = pyplot.subplots(figsize=(6.5, 4))
        datasets = dc.selectDatasets('inflow', 'outflow', parameter=parameter)
        infl_proxy = None

        for n, ds in enumerate(datasets):
            pos = pos_map[ds.definition['category']]
            if ds is not None:
                bp = ds.boxplot(ax=ax, yscale='log', width=0.45, bothTicks=False,
                                bacteria=group == 'Biological',
                                pos=pos, offset=0.25,
                                patch_artist=True)
                if infl_proxy is None:
                    infl_proxy, effl_proxy = _proxy_inflow_outflow(ds)

        ax.set_xticks(bmppositions)
        ax.set_xticklabels([x.replace('/', '/\n') for x in bmplabels])
        ax.set_ylabel(param.paramunit())
        ax.set_xlabel('')
        ax.yaxis.grid(True, which='major', color='0.5', linestyle='-')
        ax.yaxis.grid(False, which='minor')
        wqio.viz.rotateTickLabels(ax, 45, 'x')
        ax.set_xlim(left=1, right=bmppositions.max() + 1)
        if infl_proxy is not None:
            ax.legend(
                (infl_proxy, effl_proxy),
                ('Influent', 'Effluent'),
                ncol=2,
                frameon=False,
                bbox_to_anchor=(1.0, 1.1)
            )
        fig.tight_layout()
        seaborn.despine(fig)
        fname = '{}_{}_boxplots.png'.format(group, parameter.replace(', ', ''))

        fig.savefig(os.path.join(outpath, fname), dpi=600, bbox_inches='tight', transparent=False)
        pyplot.close(fig)


def _get_fmt(paramgroup):
    if paramgroup == 'Solids':
        return lambda x: '{:.1f}'.format(x)
    elif paramgroup == 'Biological':
        return lambda x: wqio.utils.sigFigs(x, n=2)
    else:
        return lambda x: '{:.2f}'.format(x)


def categorical_stats(dc, simple=False):
    return (
        dc.data
        .loc[:, dc.groupcols + ['bmp_id']]
        .drop_duplicates()
        .groupby(dc.groupcols)
        .size()
        .unstack(level='station')
        .fillna(0).astype(int)
        .pipe(wqio.utils.add_column_level, 'BMPs', 'result')
        .swaplevel(axis='columns')
        .join(dc.count.fillna(0).astype(int))
        .join(dc.percentile(25).round(2))
        .join(dc.median.round(2))
        .join(dc.percentile(75).round(2))
        .pipe(wqio.utils.flatten_columns)
        .assign(diff_medianci=~wqio.utils.checkIntervalOverlap(
            dc.median['inflow'], dc.median['outflow'], axis=1, oneway=False)
        )
        .assign(diff_mannwhitney=(dc.mann_whitney['pvalue'] < 0.05).xs(('inflow', 'outflow'), level=['station_1', 'station_2']))
        .assign(diff_wilcoxon=(dc.wilcoxon['pvalue'] < 0.05).xs(('inflow', 'outflow'), level=['station_1', 'station_2']))
        .assign(diff_symbol=lambda df: wqio.utils.symbolize_bools(
            df.loc[:, lambda df: df.columns.map(lambda c: c.startswith('diff'))],
            true_symbol='◆', false_symbol='◇', other_symbol='✖', join_char=' '
        ))
        .pipe(wqio.utils.expand_columns, sep='_', names=['result', 'value'])
        .swaplevel(axis='columns')
    )
