import os
import sys
from pkg_resources import resource_filename

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas
import openpyxl

from wqio import utils
from wqio import Parameter

from . import dataAccess, info

from statsmodels.tools.decorators import (
    resettable_cache, cache_readonly, cache_writable
)


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


def getPFCs(db):
    # get BMP Name of pervious friction course (PFC) BMPs
    bmpnamecol = 'BMPNAME'
    bmptable = 'BMP INFO S02'
    bmptypecol = 'TBMPT 2009'
    query = """
    select [{0}]
    FROM [{1}]
    WHERE [{2}] = 'PF';
    """.format(bmpnamecol, bmptable, bmptypecol)

    with db.connect() as cnn:
        pfc_names = pandas.read_sql(query, cnn)[bmpnamecol].tolist()

    return pfc_names


def _pick_best_station(dataframe):
    def best_col(row, mainstation, backupstation, valcol):
        try:
            if pandas.isnull(row[(mainstation, valcol)]):
                return row[(backupstation, valcol)]
            else:
                return row[(mainstation, valcol)]
        except KeyError:
            return np.nan

    xtab = dataframe.unstack(level='station')
    xtab.columns = xtab.columns.swaplevel(0, 1)
    xtab[('final_outflow', 'res')] = xtab.apply(
        best_col, axis=1, args=('outflow', 'subsurface', 'res')
    )
    xtab[('final_outflow', 'qual')] = xtab.apply(
        best_col, axis=1, args=('outflow', 'subsurface', 'qual')
    )
    xtab[('final_inflow', 'qual')] = xtab.apply(
        best_col, axis=1, args=('inflow', 'reference outflow', 'qual')
    )
    xtab[('final_inflow', 'res')] = xtab.apply(
        best_col, axis=1, args=('inflow', 'reference outflow', 'res')
    )

    data = (
        xtab.select(lambda c: 'final_' in c[0], axis=1)
            .rename(columns=lambda col: col.replace('final_', ''))
            .stack(level='station')
    )
    return data


def _pick_best_sampletype(dataframe):
    def best_col(row):
        if pandas.isnull(row['composite']):
            return row[badval]
        else:
            return np.nan

    pivotlevel='sampletype'
    badval='grab'

    orig_cols = dataframe.columns
    xtab = dataframe.unstack(level=pivotlevel)
    for col in orig_cols:
        xtab[(col, badval)] = xtab[col].apply(best_col, axis=1)

    data = (
        xtab.select(lambda c: c[1] != 'unknown', axis=1)
            .stack(level=['sampletype'])
    )
    return data


def _filter_onesided_BMPs(dataframe):
    grouplevels = ['site', 'bmp', 'parameter', 'category']
    pivotlevel = 'station'

    xtab = dataframe.unstack(level=pivotlevel)
    xgrp = xtab.groupby(level=grouplevels)
    data = xgrp.filter(
        lambda g: np.all(g['res'].describe().loc['count'] > 0)
    )
    return data.stack(level=pivotlevel)


def _filter_by_storm_count(dataframe, minstorms):
    # filter out all monitoring stations with less than /N/ storms
    grouplevels = ['site', 'bmp', 'parameter', 'station']

    data = dataframe.groupby(level=grouplevels).filter(
        lambda g: g.count()['res'] >= minstorms
    )
    return data


def _filter_by_BMP_count(dataframe, minbmps):
    grouplevels = ['category', 'parameter', 'station']

    data = dataframe.groupby(level=grouplevels).filter(
        lambda g: g.index.get_level_values('bmp').unique().shape[0] >= minbmps
    )
    return data


def getSummaryData(dbpath=None, catanalysis=False, astable=False,
                   minstorms=3, minbmps=3, name=None, useTex=False,
                   excludedbmps=None, excludedparams=None,
                   **selection):
    '''Select offical data from database.

    Parameters
    ----------
    dbpath : string
        File path to the BMP Database Access file.
    catanalysis : optional bool (default = False)
        Filters for data approved for BMP Category-level analysis.
    wqanalysis : optional bool (default = False)
        Filters for data approvded for individual BMP analysis.
    minstorms : option int (default = 3)
        The minimum number of storms each group defined by BMP, station,
        and parameter should have. Groups with too few storms will be
        filtered out.
    minstorms : option int (default = 3)
        The minimum number of BMPs each group defined
        by category, station, and parameter should have.
        Groups with too few BMPs will be filtered out.
    astable : optional bool (default = False)
        Toggles whether the database will be returned
        as a pandas.DataFrame (default) or a bmp.Table
        object.
    excludedbmps : optional list or None (default)
        List of BMP Names to exclude form the result.
    name : optional string or None (default)
        Passed directly to the Table constuctor.
    usetex : optional bool (default = False)
        Passed directly to the Table constuctor.
    **selection : optional keyword arguments
        Selection criteria passed directly Database.selectData

    Returns
    -------
    subset : pandas.DataFrame or bmpTable

    '''

    # main dataset
    if dbpath is None:
        dbpath = resource_filename("pybmpdb.data", 'bmpdata.csv')

    db = dataAccess.Database(dbpath, catanalysis=catanalysis)

    # astable must be true here. The input value is respected later
    table = db.selectData(astable=True, useTex=useTex, **selection)

    # combine NO3+NO2 and NO3 into NOx
    nitro_components = [
        'Nitrogen, Nitrite (NO2) + Nitrate (NO3) as N',
        'Nitrogen, Nitrate (NO3) as N'
    ]
    nitros_exist = table._check_for_parameters(nitro_components)
    if nitros_exist:
        nitro_combined = 'Nitrogen, NOx as N'
        table.unionParamsWithPreference(nitro_components, nitro_combined,
                                        'mg/L')

    grab_BMPs = ['Retention Pond', 'Wetland Basin']
    if catanalysis:
        # merge Wet land Basins and Retention ponds, keeping
        # the original records
        WBRP_combo = 'Wetland Basin/Retention Pond'
        table.redefineBMPCategory(
            bmpname=WBRP_combo,
            criteria=lambda r: r[0] in grab_BMPs,
            dropold=False
        )
        grab_BMPs.append(WBRP_combo)

    # all data should be compisite data, but grabs are allowed
    # for bacteria at all BMPs, and all parameter groups at
    # retention ponds and wetland basins. Samples of an unknown
    # type are excluded
    querytxt = (
    "(sampletype == 'composite') | ("
        "(category in {}) | "
        "(paramgroup == 'Biological') "
    ") & (sampletype != 'unknown')"
    ).format(grab_BMPs)
    subset = table.data.query(querytxt)

    if excludedbmps is not None:
        # remove all of the PFCs from the dataset
        exclude_bmp_query = "bmp not in {}".format(excludedbmps)
        subset = subset.query(exclude_bmp_query)

    if excludedparams is not None:
        exclude_params_query = "parameter not in {}".format(excludedparams)
        subset = subset.query(exclude_params_query)

    subset = _pick_best_sampletype(subset)
    subset = _pick_best_station(subset)
    subset = _filter_by_storm_count(subset, minstorms)
    subset = _filter_by_BMP_count(subset, minbmps)
    subset = _filter_onesided_BMPs(subset)

    if astable:
        table = dataAccess.Table(subset, name=name, useTex=useTex)
        return table, db
    else:
        return subset, db


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
                val = utils.sigFigs(getattr(self.ds, attribute), sigfigs,
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
                                utils.sigFigs(val[0], sigfigs, pval=pval,
                                              tex=tex, forceint=forceint),
                                utils.sigFigs(val[1], sigfigs, pval=pval,
                                              tex=tex, forceint=forceint)
                            )

                            if ci:
                                thisstring = '({})'.format(thisstring)
                        else:
                            thisstring = utils.sigFigs(
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
        #tabletitle = 'Summary of {} at {} BMPs'.format(self.parameter.tex, self.bmpName)
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
            #{'name': 'Number of Studies', 'attribute': 'JUNK', 'sigfigs': 0},
            {'name': 'Min; Max', 'attribute': ['min', 'max'], 'twoval': True},
            {'name': 'Mean', 'attribute': 'mean', },
            {'name': '(95\% confidence interval)',
                'attribute': 'mean_conf_interval',
                'twoval': True, 'ci': True, 'rule':'none'
            },
            {'name': 'Standard Deviation', 'attribute': 'std', },
            {'name': 'Log. Mean', 'attribute': 'logmean', },
            {'name': '(95\% confidence interval)',
                'attribute': 'logmean_conf_interval',
                'twoval': True, 'ci': True, 'rule':'none'
            },
            {'name': 'Log. Standard Deviation', 'attribute': 'logstd', },
            {'name': 'Geo. Mean', 'attribute': 'geomean', },
            {'name': '(95\% confidence interval)',
                'attribute': 'geomean_conf_interval',
                'twoval': True, 'ci': True, 'rule':'none'
            },
            {'name': 'Coeff. of Variation', 'attribute': 'cov', },
            {'name': 'Skewness', 'attribute': 'skew', },
            {'name': 'Median', 'attribute': 'median', },
            {'name': '(95\% confidence interval)',
                'attribute': 'median_conf_interval',
                'twoval': True, 'ci': True, 'rule':'none'
            },
            {'name': 'Quartiles',
                'attribute': ['pctl25', 'pctl75'],
                'twoval': True,
            },
            {'name': 'Number of Pairs', 'attribute': 'n_pairs',
                'rule': 'top', 'fromdataset': True,
                'sigfigs': 1, 'forceint': True
            },
            {'name': 'Wilcoxon p-value', 'attribute': 'wilcoxon_p',
                'fromdataset': True, 'pval': True, 'tex': True
            },
            {'name': 'Mann-Whitney p-value', 'attribute': 'mannwhitney_p',
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

                #if ds.n_pairs is None or ds.paired_data is None or ds.n_pairs < self.filtercount:
                #    ds.include = False
                #else:
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
                    bacteria=(self.paramgroup=='Bacteria'),
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
            plt.close('all')

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


def parameterBoxplots(datacollection, prefix, bacteria=False):
    param = None
    bmplabels = datacollection.tidy['category'].unique()

    # positions of the ticks
    bmppositions = np.arange(1, len(bmplabels) + 1) * 2
    pos_map = dict(zip(bmplabels, bmppositions))

    for parameter in datacollection.tidy['parameter'].unique():

        fig, ax = plt.subplots(figsize=(6.5, 4))
        datasets = datacollection.selectDatasets(parameter=parameter)
        infl_proxy = None
        effl_proxy = None

        for n, ds in enumerate(datasets):
            pos = pos_map[ds.definition['category']]
            if ds is not None:

                bp = ds.boxplot(ax=ax, yscale='log', width=0.45,
                                bacteria=bacteria, pos=pos, offset=0.25)

                if infl_proxy is None:
                    infl_proxy, effl_proxy = _proxy_inflow_outflow(ds)

                if param is None:
                    param = ds.definition['parameter_obj']

        ax.set_xticks(bmppositions)
        ax.set_xticklabels([x.replace('/', '/\n') for x in bmplabels])
        ax.set_ylabel(param.paramunit())
        ax.set_xlabel('')
        utils.figutils.rotateTickLabels(ax, 45, 'x')
        ax.set_xlim(left=1, right=bmppositions.max()+1)
        if infl_proxy is not None:
            ax.legend(
                (infl_proxy, effl_proxy),
                ('Influent', 'Effluent'),
                ncol=2,
                frameon=False,
                bbox_to_anchor=(1.0, 1.1)
            )
        fig.tight_layout()
        figpath = 'figures/{}_{}_boxplots.png'.format(prefix, parameter.replace(', ', ''))
        fig.savefig(figpath, dpi=600, bbox_inches='tight', transparent=True)
        plt.close(fig)


def bmpStatSummary(datacollection):
    stat_dict = {}

    def getNStudies(loc):
        return loc.filtered_data.index.get_level_values('bmp').unique().shape[0]

    for ds in datacollection.datasets:
        key = (ds.definition['parameter'], ds.definition['category'])
        stat_dict[key] = {}
        for n, loc in zip(['In', 'Out'], [ds.influent, ds.effluent]):
            stat_dict[key][('N', n)] = loc.N
            stat_dict[key][('N-Studies', n)] = getNStudies(loc)
            stat_dict[key][('25th', n)] = loc.pctl25
            stat_dict[key][('Median', n)] = loc.median
            stat_dict[key][('Median CI low', n)] = loc.median_conf_interval[0]
            stat_dict[key][('Median CI high', n)] = loc.median_conf_interval[1]
            stat_dict[key][('75th', n)] = loc.pctl75

    stat_df = pandas.DataFrame(stat_dict).T

    full_index = pandas.MultiIndex.from_product([
        stat_df.index.get_level_values(0).unique(),
        stat_df.index.get_level_values(1).unique(),
    ], names=['Parameter', 'BMP Type'])

    return stat_df.reindex(full_index)
