import os
import sys
from pkg_resources import resource_filename

import numpy
import matplotlib
from matplotlib import pyplot
import seaborn
import pandas
from statsmodels.tools.decorators import (
    resettable_cache, cache_readonly
)

import wqio

from . import dataAccess, info, utils


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


def _pick_best_station(dataframe):
    def best_col(df, mainstation, backupstation, valcol):
        for sta in [mainstation, backupstation]:
            if (sta, valcol) not in df.columns:
                df = wqio.utils.assign_multilevel_column(df, numpy.nan, sta, valcol)

        values = numpy.where(
            df[(mainstation, valcol)].isnull(),
            df[(backupstation, valcol)],
            df[(mainstation, valcol)]
        )
        return values

    orig_index = dataframe.index.names    
    data = (
        dataframe
            .reset_index()
            .set_index(orig_index)
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


def _pick_best_sampletype(dataframe):
    def best_col(row):
        if pandas.isnull(row['composite']):
            return row[badval]
        else:
            return numpy.nan

    pivotlevel = 'sampletype'
    badval = 'grab'

    orig_cols = dataframe.columns
    orig_index = dataframe.index.names
    xtab = (
        dataframe
            .reset_index()
            .set_index(orig_index)
            .unstack(level=pivotlevel)
    )
    for col in orig_cols:
        xtab[(col, badval)] = xtab[col].apply(best_col, axis=1)

    data = (
        xtab.loc[:, xtab.columns.map(lambda c: c[1] != 'unknown')]
            .stack(level=['sampletype'])
    )
    return data


def _filter_onesided_BMPs(dataframe, execute=True):
    grouplevels = ['site', 'bmp', 'parameter', 'category']
    pivotlevel = 'station'

    if execute:
        data = (
            dataframe.unstack(level=pivotlevel)
                     .groupby(level=grouplevels)
                     .filter(lambda g: numpy.all(g['res'].describe().loc['count'] > 0))
                     .stack(level=pivotlevel)
        )
    else:
        data = dataframe.copy()
    return data


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


def getSummaryData(dbpath=None, catanalysis=False, minstorms=3, minbmps=3,
                   name=None, useTex=False, ndscaler=None, combine_nox=True,
                   removegrabs=True, grab_categories=None, combine_WB_RP=True,
                   excludedbmps=None, excludedparams=None,
                   balancedonly=True, **selection):
    """
    Select offical data from database.

    Parameters
    ----------
    dbpath : string
        File path to the BMP Database Access file.
    catanalysis : optional bool (default = False)
        Filters for data approved for BMP Category-level analysis.
    minstorms : option int (default = 3)
        The minimum number of storms each group defined by BMP, station,
        and parameter should have. Groups with too few storms will be
        filtered out.
    minbmps : option int (default = 3)
        The minimum number of BMPs each group defined
        by category, station, and parameter should have.
        Groups with too few BMPs will be filtered out.
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

    """

    # main dataset
    if dbpath is None:
        dbpath = wqio.download('bmpdata')

    db = dataAccess.Database(dbpath, catanalysis=catanalysis, ndscaler=ndscaler)
    db.data = db.select(**selection)

    # combine NO3+NO2 and NO3 into NOx
    nitro_components = [
        'Nitrogen, Nitrite (NO2) + Nitrate (NO3) as N',
        'Nitrogen, Nitrate (NO3) as N'
    ]
    if db._check_for_parameters(nitro_components) and combine_nox:
        nitro_combined = 'Nitrogen, NOx as N'
        db.unionParamsWithPreference(nitro_components, nitro_combined, 'mg/L')

    if grab_categories is None:
        grab_categories = ['Retention Pond', 'Wetland Basin']
    else:
        grab_categories = wqio.validate.at_least_empty_list(grab_categories)

    if catanalysis:
        # merge Wet land Basins and Retention ponds, keeping
        # the original records
        category_index_level = db.index['category']
        WBRP_combo = 'Wetland Basin/Retention Pond'
        db.redefineBMPCategory(
            category=WBRP_combo,
            criteria=lambda r: r[category_index_level] in grab_categories,
            dropold=False
        )
        grab_categories.append(WBRP_combo)

    bmptype_index_level = db.index['bmptype']
    db.redefineBMPCategory(
        category='Permeable Friction Course',
        criteria=lambda r: r[bmptype_index_level] == 'PF',
        dropold=True
    )

    # all data should be compisite data, but grabs are allowed
    # for bacteria at all BMPs, and all parameter groups at
    # retention ponds and wetland basins. Samples of an unknown
    # type are excluded
    if removegrabs:
        querytxt = (
            "(sampletype == 'composite') | "
            "(((category in @grab_categories) | (paramgroup == 'Biological')) & "
            "  (sampletype != 'unknown'))"
        ).format(grab_categories)
        subset = db.data.query(querytxt)
    else:
        subset = db.data.copy()

    excludedbmps = wqio.validate.at_least_empty_list(excludedbmps)
    excludedparams = wqio.validate.at_least_empty_list(excludedparams)

    subset = (
        subset.query("bmp not in @excludedbmps")
              .query("parameter not in @excludedparams")
              .pipe(_pick_best_sampletype)
              .pipe(_pick_best_station)
              .pipe(_filter_onesided_BMPs, execute=balancedonly)
              .pipe(_filter_by_storm_count, minstorms)
              .pipe(_filter_by_BMP_count, minbmps)
    )

    return subset, db


def paired_qual(row):
    if row['qual_inflow'] == '=':
        if row['qual_outflow'] == '=':
            val = 'Pair'
        elif row['qual_outflow'] == 'ND':
            val = 'Effluent ND'
    elif row['qual_inflow'] == 'ND':
        if row['qual_outflow'] == '=':
            val = 'Influent ND'
        elif row['qual_outflow'] == 'ND':
            val = 'Both ND'
    return val


def website_data(df):
    # Capitalize some words/phrases
    cap_old = ['composite', 'grab', 'unknown', 'ZZ']
    cap_new = ['Composite', 'Grab', 'Unknown', 'ZZ - Unknown']

    # flag the manufactured devices to be excluded from the
    # category-level analysis
    _cache_of_index_names = df.index.names
    dont_use = ['Manufactured Device']
    df = (
        df.reset_index()
          .assign(use=lambda df: numpy.where(df['category'].isin(dont_use), 'no', 'yes'))
          .replace(cap_old, cap_new)
          .set_index(_cache_of_index_names)
    )

    # To rename columns
    bmp_dict = {
        'sampledatetime': 'date',
        'res': 'value'
    }

    # Extra columns for flat data
    columns_to_drop = [
        'epazone',
        'storm',
        'watertype',
        'paramgroup',
        'wqscreen',
        'catscreen',
        'balanced',
        'WQID'
    ]

    flat = (
        df.reset_index()
          .drop(columns_to_drop, axis=1)
          .rename(columns=bmp_dict)
          .assign(date=lambda df: pandas.to_datetime(df['date']).dt.strftime('%Y-%m-%d'))
    )

    xtab = (
        df.set_index('use', append=True)
          .reset_index(level='sampledatetime')
          .assign(sampledatetime=lambda df: pandas.to_datetime(df['sampledatetime']))
          .unstack(level='station')
          .assign(date=lambda df: df['sampledatetime'].min(axis=1))
          .drop('sampledatetime', axis=1)
          .pipe(wqio.utils.flatten_columns)
          .dropna(subset=['res_inflow', 'res_outflow'])
          .rename(columns={'date_': 'sampledatetime'})
          .assign(pair=lambda df: df.apply(paired_qual, axis=1))
          .reset_index()
    )

    return flat, xtab


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


def categorical_stats(datacollection):
    diff_marks = {
        True: '◆',
        False: '◇',
        None: '◇',
    }
    stat_dict = {}
    for ds in datacollection.datasets('inflow', 'outflow'):
        pgroup = ds.definition['paramgroup']
        paramunit = '{} ({})'.format(ds.definition['parameter'], ds.definition['units'])
        key = (paramunit, pgroup, ds.definition['category'])
        fmt = _get_fmt(pgroup)

        stat_dict[key] = {}
        for n, loc in zip(['In', 'Out'], [ds.influent, ds.effluent]):
            if loc is not None:
                medians = [loc.median] + loc.median_conf_interval.tolist()
                stat_dict[key][('EMCs', n)] = loc.N
                stat_dict[key][('BMPs', n)] = loc.raw_data.reset_index()['bmp'].unique().shape[0]
                stat_dict[key][('25th', n)] = fmt(loc.pctl25)
                stat_dict[key][('Median', n)] = '{} ({}, {})'.format(*map(fmt, medians))
                stat_dict[key][('75th', n)] = fmt(loc.pctl75)
            else:
                stat_dict[key][('EMCs', n)] = 0
                stat_dict[key][('BMPs', n)] = 0
                stat_dict[key][('25th', n)] = None
                stat_dict[key][('Median', n)] = None
                stat_dict[key][('75th', n)] = None

        if ds.influent is not None and ds.effluent is not None:
            truth_array = [
                not ds.medianCIsOverlap if ds.medianCIsOverlap is not None else False,
                ds.mannwhitney_p <= 0.05 if ds.mannwhitney_p is not None else False,
                ds.wilcoxon_p <= 0.05 if ds.wilcoxon_p is not None else False,
            ]
            stat_dict[key][('Median', 'Difference')] = ''.join(map(diff_marks.get, truth_array))
        else:
            stat_dict[key][('Median', 'Difference')] = None

    final_cols = [
        ('BMPs', 'In'), ('BMPs', 'Out'),
        ('EMCs', 'In'), ('EMCs', 'Out'),
        ('25th', 'In'), ('25th', 'Out'),
        ('Median', 'In'), ('Median', 'Out'), ('Median', 'Difference'),
        ('75th', 'In'), ('75th', 'Out'),
    ]
    index_names = ['paramunit', 'paramgroup', 'BMP Category']
    stat_df = (
        pandas.DataFrame(stat_dict)
              .transpose()
              .reindex(columns=final_cols)
              .rename_axis(index_names, axis='index')
    )
    return stat_df
