import os

import numpy
import matplotlib
from matplotlib import pyplot
import seaborn
from statsmodels.tools.decorators import cache_readonly

import wqio
from . import bmpdb, utils


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
        self._cache = {}
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
