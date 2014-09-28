#from __future__ import division
import os

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import openpyxl

from .. import utils

from . import dataAccess
from . import analysis


from statsmodels.tools.decorators import (resettable_cache,
                                          cache_readonly,
                                          cache_writable)


# __all__ = ['dataDump', 'statDump', 'diffStatsDump', 'sbpat_stats',
#            'latexInputFile', 'latexReport', 'paramTables',
#            'paramBoxplots']

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
    def __init__(self, dataset, paramgroup, figpath):
        self.figpath = figpath
        self.paramgroup = paramgroup
        self.ds = dataset
        self.parameter = self.ds.definition['parameter']
        self.parameter.usingTex = True
        self.bmp = self.ds.definition['category']

        # properties
        self._latex_file_name = None
        self._scatter_fig_name = None
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
    def scatter_fig_name(self):
        if self._scatter_fig_name is None:
            figname = utils.processFilename('{}_scatter.pdf'.format(self.latex_file_name))
            self._scatter_fig_name = self.figpath + '/scatterplot/' + figname
        return self._scatter_fig_name
    @scatter_fig_name.setter
    def scatter_fig_name(self, value):
        self._scatter_fig_name = value

    @property
    def stat_fig_name(self):
        if self._stat_fig_name is None:
            figname = utils.processFilename('{}_stats.pdf'.format(self.latex_file_name))
            self._stat_fig_name = self.figpath + '/statplot/' + figname
        return self._stat_fig_name
    @stat_fig_name.setter
    def stat_fig_name(self, value):
        self._stat_fig_name = value

    def _tex_table_row(self, name, attribute, rule='mid', twoval=False,
                       sigfigs=3, ci=False, fromdataset=False, pval=False,
                       tex=False):
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
                val = utils.sigFigs(getattr(self.ds, attribute),
                                    sigfigs, pval=pval, tex=tex)
            else:
                val = 'NA'

            row = r"""
                {ruler}
                {name} & \multicolumn{{2}}{{c}} {{{value}}} \\""".format(
                **dict(ruler=thisrule, name=name, value=val)
            )
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
                            thisstring = '{}, {}'.format(
                                utils.sigFigs(val[0], sigfigs, pval=pval, tex=tex),
                                utils.sigFigs(val[1], sigfigs, pval=pval, tex=tex)
                            )

                            if ci:
                                thisstring = '({})'.format(thisstring)

                        else:
                            thisstring = utils.sigFigs(val, sigfigs, pval=pval, tex=tex)
                else:
                    thisstring = 'NA'

                valstrings.append(thisstring)

            row = r"""
                {ruler}
                {name} & {val_in} & {val_out} \\""".format(
                **dict(ruler=thisrule, name=name,
                       val_in=valstrings[0],
                       val_out=valstrings[1])
            )

        return row

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
            {'name': 'Count', 'attribute': 'N', 'rule': 'top', 'sigfigs': 1},
            {'name': 'Number of NDs', 'attribute': 'ND', 'sigfigs': 1},
            #{'name': 'Number of Studies', 'attribute': 'JUNK', 'sigfigs': 0},
            {'name': 'Min, Max', 'attribute': ['min', 'max'], 'twoval': True},
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
            {'name': 'Covariance', 'attribute': 'cov', },
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
                'rule': 'top', 'fromdataset': True, 'sigfigs': 1
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
        self.filtercount= filtercount
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
                filterlocation(ds.influent, count=self.filtercount,
                               column=self.filtercolumn)
                filterlocation(ds.effluent, count=self.filtercount,
                               column=self.filtercolumn)
                if ds.n_pairs is None or ds.paired_data is None or ds.n_pairs < 5:
                    ds.include = False
                else:
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
                statfig = ds.statplot(ylabel=dsum.parameter.paramunit())
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
                self._make_report_IO(templateIO, inputpath, reportIO, report_title)




""""
    def dataDump(tablename):
        '''
        Dumps raw and ROS'd data into a csv for Marc
        CSV has the following columns:
            'bmptype', 'parameter', 'loc', 'raw_val', 'ros_val'
            ('loc' refers to influent or effluent)

        Input:
            tablname (string) : name of the table in the Access database.

        Writes:
            A CSV file with the ROS and raw data for peer-review/comparison

        Returns:
            None
        '''
        # get the data from the table
        table = dataAccess.Table(tablename)

        # setup the output files with headers
        filename = 'bmp/summary/datadump-%s.csv' % (tablename,)
        dumpfile = open(filename, 'w')
        headers = ('bmptype', 'parameter', 'loc', 'raw_val', 'ros_val')
        dumpfile.write('%s,%s,%s,%s,%s\n' % headers)

        # loop through each parameter and bmp category
        for param in table.parameters:
            for bmp in table.bmpCats:

                # create a dataset and write each location's data to the output file
                # if there are enough data to do the ROS estimation
                ds = analysis.Dataset(table, param, bmp, exclLevel='points', exclThreshold=3)

                if ds.influent.include:
                    for raw, ros in zip(ds.influent.ros.data.res, ds.influent.ros.final_data):
                        dumpfile.write('%s,"%s",%s,%f,%f\n' % (bmp, param.name, 'influent', raw, ros))

                if ds.effluent.include:
                    for raw, ros in zip(ds.effluent.ros.data.res, ds.effluent.ros.final_data):
                        dumpfile.write('%s,"%s",%s,%f,%f\n' % (bmp, param.name, 'effluent', raw, ros))

        # we're done here
        dumpfile.close()


    def statDump(tablename):
        '''
        Dumps stats to a flat Excel (.xlsx) file
        The table has the following columns:
            'parameter', 'bmp', 'location', 'stat', 'result']
            ('location' refers to influent or effluent)

        Input:
            tablname (string) : name of the table in the Access database.

        Writes:
            A Excel (.xlsx) file with the stats summary for peer-review

        Returns:
            None
        '''
        # setup the Excel file
        filename = 'bmp/summary/%s_statdump.xlsx' % tablename
        wkbook = openpyxl.workbook.Workbook()
        headers = ['parameter', 'bmp', 'location', 'stat', 'result']
        sht = wkbook.create_sheet(title='%s stats' % tablename)

        # read the data
        table = dataAccess.Table(tablename)

        # write all the headers
        for col, h in enumerate(headers):
            sht.cell(row=0, column=col).value = h

        # loop through each parameter and BMP cat
        #   create a dataset
        #      write the stats if there are enough
        #      data at each location
        row = 1
        for param in table.parameters:
            print('\t%s' % param.name)
            for bmp in table.bmpCats:
                ds = analysis.Dataset(table, param, bmp, exclLevel='points', exclThreshold=3)
                if ds.influent.include:
                    row = _write_stat_line(sht, param.paramunit, bmp, 'influent',
                                           ds.influent.stats, ds.influent.NStudies,
                                           row)

                if ds.effluent.include:
                    row = _write_stat_line(sht, param.paramunit, bmp, 'effluent',
                                           ds.effluent.stats, ds.effluent.NStudies,
                                           row)

        # we're done here
        wkbook.save(filename=filename)


    def _write_stat_line(sht, param, bmp, loc, statsummary, nstudies, startrow):
        '''
        Helper function to write statsummary attributes to an
        openpyxl worksheet

        Input:
            sht (openpyxl worksheet) : the destination worksheet
            param (string) : the parameter we're looking at
            bmp (string) : the BMP category of the data
            loc (string) : influent or effluent
            statsummary (`analysis.Statsummary`) : statsummary object to write
            NStudies (int) : number of studies in the dataset
            startrow (int) : the first row number recieving output

        Writes:
            Statsummary data to an openpyxl worksheet

        Returns:
            row (int) : the next empty row below the row last written
        '''

        # setup the stats we're going to use
        row = startrow
        stats = ['N', 'ND', 'min', 'max', 'mean', 'std', 'logmean',
                 'logstd', 'geomean', 'geostd', 'cov', 'skew',
                 'median',  'pctl10', 'pctl25', 'pctl75', 'pctl90',
                 'pnorm', 'plognorm', 'analysis_space']

        # write the row headings and the the number of studies
        sht.cell(row=row, column=0).value = param
        sht.cell(row=row, column=1).value = bmp
        sht.cell(row=row, column=2).value = loc
        sht.cell(row=row, column=3).value = 'NStudies'
        sht.cell(row=row, column=4).value = nstudies
        row += 1

        # write all of the mainline stats
        for stat in stats:
            sht.cell(row=row, column=0).value = param
            sht.cell(row=row, column=1).value = bmp
            sht.cell(row=row, column=2).value = loc
            sht.cell(row=row, column=3).value = stat
            sht.cell(row=row, column=4).value = eval('statsummary.%s' % stat)
            row += 1

        # write all of the things with confidence intervals
        conf_intervals = ['mean_conf_interval', 'logmean_conf_interval',
                          'geomean_conf_interval', 'median_conf_interval']

        for ci in conf_intervals:
            sht.cell(row=row, column=0).value = param
            sht.cell(row=row, column=1).value = bmp
            sht.cell(row=row, column=2).value = loc
            sht.cell(row=row, column=3).value = '%s (lower)' % ci
            sht.cell(row=row, column=4).value = eval('statsummary.%s[0]' % ci)
            row += 1

            sht.cell(row=row, column=0).value = param
            sht.cell(row=row, column=1).value = bmp
            sht.cell(row=row, column=2).value = loc
            sht.cell(row=row, column=3).value = '%s (upper)' % ci
            sht.cell(row=row, column=4).value = eval('statsummary.%s[1]' % ci)
            row += 1

        # we're done here
        return row


    def _write_diff_stat_line(sht, param, bmp, diffstats, NPairs, infl_nd, effl_nd, startrow):
        '''
        Helper function to write diff statsummary attributes to an
        openpyxl worksheet (diff -> influent vs effluent)

        Input:
            sht (openpyxl worksheet) : the destination worksheet
            param (string) : the parameter we're looking at
            bmp (string) : the BMP category of the data
            diffstats (`analysis.Statsummary`) : statsummary object to write
            NPairs (int) : number of paired observations in the dataset
            infl_nd (int) : number of non-detects in the influent data
            effl_nd (int) : number of non-detects in the effluent data
            startrow (int) : the first row number recieving output

        Writes:
            Statsummary data to an openpyxl worksheet

        Returns:
            row (int) : the next empty row below the row last written
        '''
        # get setup
        row = startrow

        # write row headings and the number of pairs
        sht.cell(row=row, column=0).value = param
        sht.cell(row=row, column=1).value = bmp
        sht.cell(row=row, column=2).value = 'Num. Pairs'
        sht.cell(row=row, column=3).value = NPairs
        row += 1

        # write row headings and the number influent NDs
        sht.cell(row=row, column=0).value = param
        sht.cell(row=row, column=1).value = bmp
        sht.cell(row=row, column=2).value = 'NDs (influent)'
        sht.cell(row=row, column=3).value = infl_nd
        row += 1

        # write row headings and the number effluent NDs
        sht.cell(row=row, column=0).value = param
        sht.cell(row=row, column=1).value = bmp
        sht.cell(row=row, column=2).value = 'NDs (effluent)'
        sht.cell(row=row, column=3).value = effl_nd
        row += 1

        # loop though the basic stats and write
        stats = ['mean', 'std', 'cov', 'median']
        for stat in stats:
            sht.cell(row=row, column=0).value = param
            sht.cell(row=row, column=1).value = bmp
            sht.cell(row=row, column=2).value = stat
            sht.cell(row=row, column=3).value = eval('diffstats.%s' % stat)
            row += 1

        # loop through the confidence intervales
        conf_intervals = ['median_conf_interval']
        for ci in conf_intervals:
            sht.cell(row=row, column=0).value = param
            sht.cell(row=row, column=1).value = bmp
            sht.cell(row=row, column=2).value = '%s (lower)' % ci
            sht.cell(row=row, column=3).value = eval('diffstats.%s[0]' % ci)
            row += 1

            sht.cell(row=row, column=0).value = param
            sht.cell(row=row, column=1).value = bmp
            sht.cell(row=row, column=2).value = '%s (upper)' % ci
            sht.cell(row=row, column=3).value = eval('diffstats.%s[1]' % ci)
            row += 1

        # we're done here
        return row


    def diffStatsDump(tablename, log=False):
        '''
        Dumps diff (influent vs effluent) stats to a flat Excel (.xlsx) file
        The table has the following columns:
            'parameter', 'bmp', 'location', 'stat', 'result']
            ('location' refers to influent or effluent)

        Input:
            tablname (string) : name of the table in the Access database.
            log (bool) : toggles on/off whether the data should be log-
                transformed before the diff

        Writes:
            A Excel (.xlsx) file with the stats summary for peer-review

        Returns:
            None
        '''
        # grab the data
        table = dataAccess.Table(tablename)

        # setup the workbook
        wkbook = openpyxl.workbook.Workbook()
        sht = wkbook.create_sheet(title='%s stats' % tablename)

        # write the header columns
        headers = ['parameter', 'bmp', 'stat', 'result']
        for col, h in enumerate(headers):
            sht.cell(row=0, column=col).value = h

        # go through each parameter and BMP, dump the stats
        row = 1
        for param in table.parameters:
            print('\t%s' % param.name)
            for bmp in table.bmpCats:
                #ds = analysis.Dataset(table, parameter, bmpCat)

                # get the stats
                if log:
                    diffstats = analysis.Statsummary(table.paired_data['logdiff'], np.array([0]))
                else:
                    diffstats = analysis.Statsummary(table.paired_data['diff'], np.array([0]))

                # dump the stats if they're available
                if diffstats is not None:
                    row = _write_diff_stat_line(sht, param.paramunit, bmp, diffstats,
                                                NPairs, infl_nd, effl_nd, row)

        # save the file
        if log:
            filename = 'bmp/summary/%s_logdiffstatdump.xlsx' % tablename
        else:
            filename = 'bmp/summary/%s_diffstatdump.xlsx' % tablename
        wkbook.save(filename=filename)


    def stats_xtab(table, minStudies=3, minDataPts=3, ignoreROS=False):
        '''
            Writes cross-tab of stats for all parameter-BMP combinations to a csv
            Input:
                tablename (string) : name of the table with data you want

            Writes:
                A sort of xtab csv file with a bunch of stats in the columns
                and bmp/parameters in the rows

            Returns:
                None
        '''

        # setup the output file
        with open('bmp/summary/sbpat_%s.csv' % table.name.lower(), 'w') as xtab:
            headers = '"Parameter","BMP Category","Units",' \
                      '"N inf","ND inf","N eff","ND eff","N Pairs","Distribution",' \
                      '"logmean eff","logmean lcl","logmean ucl","logstd eff","logp",' \
                      '"arimean eff","airmean lcl","arimean ucl","aristd eff","arip",' \
                      '"10th eff","median eff","90th eff","m-w","wilc"\n'
            xtab.write(headers)


            # loop through parameters and BMPs
            for param in table.parameters:
                for bmp in table.data.index.levels[0]:
                    ds = analysis.Dataset(table, param, bmp,
                                          minStudies=minStudies,
                                          minDataPts=minDataPts)
                    ds.writeSBPAT_stats(xtab, ignoreROS=ignoreROS)


    def sbpat_stats(tablename):
        '''
        Writes SBPAT stats for all parameter-BMP combinations to a csv
        Input:
            tablename (string) : name of the table with data you want

        Writes:
            A sort of xtab csv file with a bunch of stats in the columns
            and bmp/parameters in the rows

        Returns:
            None
        '''

        # set some options based on which table we're using
        if tablename == 'bacteria':
            ignoreROS = True
        else:
            ignoreROS = False

        # setup the output file
        sbpat = open('bmp/summary/sbpat_%s.csv' % tablename, 'w')
        headers = ['Parameter,', 'BMP Category,', 'Units,',
                   'N inf,', 'ND inf,', 'N eff,', 'ND eff,', 'N Pairs,',
                   'Distribution,', 'log mean eff,', 'log std eff,', 'log p,',
                   'ari mean eff,', 'ari std eff,', 'ari p,',
                   '10th eff,', 'median eff,', '90th eff,',
                   'm-w,', 'wilc\n']
        sbpat.writelines(headers)

        # grab all the data
        table = dataAccess.Table(tablename)

        # loop through parameters and BMPs
        for param in table.parameters:
            for bmp in table.bmpCats:

                # select only a few parameters if we're looking at metals
                if tablename == 'metals':
                    approved_params = ['Zinc, Total', 'Zinc, Dissolved',
                                       'Lead, Total', 'Lead, Dissolved',
                                       'Copper, Total', 'Copper, Dissolved']

                    # make the dataset, wrire the stats
                    if param.name in approved_params:
                        ds = analysis.Dataset(table, param, bmp, exclLevel='points', exclThreshold=3)
                        ds.writeSBPAT_stats(sbpat, ignoreROS=ignoreROS)

                # make the dataset, wrire the stats
                else:
                    ds = analysis.Dataset(table, param, bmp, exclLevel='points', exclThreshold=3)
                    ds.writeSBPAT_stats(sbpat, ignoreROS=ignoreROS)

        # we're done here
        sbpat.close()


    def latexInputFile(table, exclLevel='bmp',  minElements=3, minGroups=3, regenFigs=True):
        '''
        Creates all inputfiles for every bmp-parameter combination
        in a table and the overall input file for the entire table

        Inputs:
            tablename (string) : name of the table you're looking at
            exclLevel (string) : "points" or "studies" - the category with which
                data will be accepted as being sufficiently numerous or ignored
            exclThreshold (int) : the threshold the exclLevel category must meet
            regenFigs (bool) : if True, recreates all of the figures. Set to False
                if the figures are fine to reduce run time.

        Writes:
            The big input file for a summary report and all of the little
                files for figures and tables that it calls

        Returns:
            None
        '''

        def myFilter(df):
            newdf, include = dataAccess.defaultFilter(df, levelname=exclLevel,
                                                      minElements=minElements,
                                                      minGroups=minGroups)
            return newdf, include

        datasets = table.getDatasets('category', filterfxn=myFilter,
                                     showprogress=True)

        # progress announcement
        print('\nWriting {} input file'.format(table.name))

        # setup the file an the data
        inputname = 'bmp/tex/input_{}.tex'.format(tablename)
        inputfile = open(inputname, 'w')
        inputlines = []
        table = dataAccess.Table(tablename)

        # to ensure that we don't have sectiosn with only 1 subsection
        if len(table.parameters) == 1:
            subsection = False
        else:
            subsection = True

        # loop through each BMP
        for ds in datasets:

            # write a new section
            bmp = ds.definition['category']
            inputlines.append('\\section{%s}\n'.format(bmp))

            # progress update
            print('  %s' % (bmp, ))

            # proceed if any data meets the exclusion requirements
            if ds.influent.include or ds.effluent.include:
                bmpfilename = ds.makeTexInputFile(subsection=subsection)

                # regenerate fig is requested
                #if regenFigs:
                if regenFigs:
                    ds.statplot()
                    ds.scatterplot()

                # create input line
                inputlines.append('\\input{%s}\n' % bmpfilename)
                inputlines.append('\\clearpage\n')

        # write all the lines and close out
        inputfile.writelines(inputlines)
        inputfile.close()


    def latexReport(tablename, doctitle, template='draft'):
        '''
        Adds the table input file to either the "draft"
        or "final" template and modifies that template
        for the table

        Input:
            tablename (string) : name of the table you're looking at
            doctitle (string) : the title you want the PDF document to have
            template (string) : "draft" or "final"

        Writes:
            LaTeX report calling the file written in `latexReport`

        Returns:
            None
        '''
        print('\n%s summary report (%s)' % (doctitle, template))
        # open and read the template to get the header info
        templatefile = open(r'bmp/%s_template.tex' % (template,), 'r')
        header = templatefile.readlines()
        templatefile.close()

        # replace dummy strings in the header for customization
        for n in range(len(header)):
            #bmpCat = ''
            #header[n] = header[n].replace('__VAR01', bmpCat)
            #header[n] = header[n].replace('__VAR02', bmpCat)
            #header[n] = header[n].replace('__VAR03', bmpCat)
            header[n] = header[n].replace('__VAR04', doctitle)

        # create a new file
        newFileName = r'bmp/tex/%s_%s.tex' % (template, doctitle.replace(' ', ''))
        report = open(newFileName, 'w')

        # write the header info
        report.writelines(header)

        # write the input like and end the document
        report.write('\\input{input_%s.tex}\n' % (tablename,))
        report.write('\\end{document}\n')


    def paramTables(tablename):
        '''
        Summarized all parameter data in a table by BMP
        in an Excel file
        TODO: I bet pandas could handle this easily

        Input:
            tablename (string) : name of the table you're looking at

        Writes:
            Excel file with a bunch of sheets for each parmeter
            Each row is for the BMPs

        Returns:
            None
        '''

        # setup the workbook and data
        table = dataAccess.Table(tablename)
        wkbook = openpyxl.workbook.Workbook()

        # progress
        print('\nSummary Tables')

        # loop through each parameter, create a sheet
        for k, param in enumerate(table.parameters):
            # progress
            print('  %s' % (param.name,))
            sht = wkbook.create_sheet(title='Sheet%0.1d' % k)
            sht.cell(row=0, column=0).value = '%s (%s)' % (param.name, param.units)

            # loop through each bmp and write the row header
            for row, bmp in enumerate(table.bmpCats):
                bmpName = dataAccess.bmpCatNames[bmp]
                # progress
                print('    %s' % (bmp,))
                sht.cell(row=row+1, column=0).value = bmpName

                # create the dataset, write summary to the row data
                ds = analysis.Dataset(table, param, bmp)
                ds.writeSummaryTableRow(sht, row+1)

        # ...and we're done
        wkbook.save(filename='bmp/summary/%s_SummaryTable_src.xlsx' % (table.name,))


    def paramBoxplots(tablename):
        '''
        Summarizes all parameter data in a table by BMP
        in a collection of boxplots

        Input:
            tablename (string) : name of the table you're looking at

        Writes:
            An image of a graph of boxplots. One figure for each
            parameter and one box for each bmp category.

        Returns:
            None
        '''
        # progress
        print('\nSummary Figures')

        # get the data
        table = dataAccess.Table(tablename)

        # loop through parameters
        for param in table.parameters:
            # progress
            print('  %s' % (param.name,))

            # setup the figure
            fig, ax1 = plt.subplots(figsize=[6.40, 4.25])

            # keep track of position and labels along the boxplot x-axis
            pos = 0
            row = 1
            xlabels = []
            xlabelPositions = []

            # loop through the bmp categories
            for bmp in table.bmpCats:
                # progress
                print('    %s' % (bmp,))

                # create the dataset, increment position, do the boxplot
                ds = analysis.Dataset(table, param, bmp)
                row += 1
                pos, xlabels, xlabelPositions = _do_boxplot(ax1, ds, pos, xlabels, xlabelPositions)

            # proxy artists for legend
            ax1.plot([-5, -6], [1, 1], '-', lw=1.0, color='b', marker='o',
                     ms=4, mfc='w', mec='b', label='Influent')
            ax1.plot([-5, -6], [1, 1], '-', lw=1.0, color='g', marker='s',
                     ms=4, mfc='w', mec='g', label='Effluent')

            # x-axis tweaks
            ax1.set_xlim([0, pos-1])
            ax1.set_xticks(xlabelPositions, minor=False)
            ax1.set_xticklabels(xlabels, rotation=30, fontsize=8, minor=False,
                                rotation_mode='anchor', ha='right', va='center')
            ax1.xaxis.grid(True, which='major', linewidth=0.25,
                           linestyle='-', alpha=0.20)
            ax1.xaxis.grid(False, which='minor')

            # y-axis tweaks
            ax1.set_ylabel('%s (%s)' % (param.tex, param.units))
            ax1.set_yscale('log')
            ax1.yaxis.grid(True, which='major', linewidth=0.50,
                           linestyle='-', alpha=0.35)
            ax1.yaxis.grid(True, which='minor', linewidth=0.25,
                           linestyle='-', alpha=0.20)
            ax1.yaxis.set_major_formatter(mticker.FuncFormatter(utils.figutils.ylabelFormatter))

            # tweak the legend
            leg = ax1.legend(bbox_to_anchor=(0.00, 1.02, 1.00, 0.10),
                             loc=3, ncol=2, borderaxespad=0.05)
            leg.get_frame().set_alpha(0.00)
            leg.get_frame().set_edgecolor('none')

            # optimize the figure's layout
            # fig.tight_layout()
            fig.subplots_adjust(right=0.97, top=0.92)

            # save the figure
            figname = r'bmp/summary/%s_%s.png' % (tablename, utils.processFilename(param.tex))
            fig.savefig(figname,  dpi=300)
            plt.clf()
            plt.close(fig)


    def _do_boxplot(ax, dataset, lastPosition, xlabels, xlabelPositions):
        '''
        Helper function for paramBoxplots

        Input:
            ax (matplotlib.axes object) : axes on which the boxplot will go
            dataset (analysis.dataset object) : dataset that matters
            lastPosition (float) : the location on the x-axis of the previous boxplot
            xlabels (list of strings) : BMP names to be the labels for the set_xticks
            xlabelPositions (list of ints) : where are thouse labels will go

        Writes:
            None

        Returns:
            newPosition (int) : the location on the x-axis of the current boxplot
            xlabels (list of strings) : updated BMP names to be the labels for the set_xticks
            xlabelPositions (list of ints) : updated where are thouse labels will go
        '''
        # go to the next position
        newPosition = lastPosition + 1

        # based on the availability of data in the dataset,
        # offset from the position and get a BMP label
        if dataset.effluent.include:
            if dataset.influent.include:
                pos_offset = [-0.5, 0.5]
                thisbmplabel = _make_bmp_label(dataset.bmpCatName, efflonly=False)
            else:
                pos_offset = [0.0, 0.0]
                thisbmplabel = _make_bmp_label(dataset.bmpCatName, efflonly=True)

            # append that label
            xlabels.append(thisbmplabel)

            # loop through the offsets and locations for each dataset
            for offset, loc in zip(pos_offset, [dataset.influent, dataset.effluent]):

                # plot data if available
                if loc.include:

                    # special case for bacteria
                    if dataset.table in ['bacteria', 'bacteria_appendix', 'bacteria_sbpat']:
                        data = loc.data
                    else:
                        data = loc.ros.final_data

                    bp = ax.boxplot(data, positions=[newPosition+offset], notch=1, sym='.',
                                    widths=0.6, usermedians=[loc.stats.median],
                                    conf_intervals=[loc.stats.median_conf_interval])

                    utils.figutils.formatBoxplot(bp, color=loc.color, marker=loc.marker, linestyle='-')

            # update the label positions
            xlabelPositions.append(newPosition)
            newPosition += 2

        # if no data are available, we stay in the
        # same spot on the x-axis
        else:
            newPosition = lastPosition

        return newPosition, xlabels, xlabelPositions


    def _make_bmp_label(bmp, efflonly=False):
        '''
        Tiny bit of formatting for xlabels on paramBoxplots

        Adds line breaks with some MD categories and adds
        "(effluent only)" if requested
        '''
        bmp = bmp.replace(' or ', '/\n')
        bmp = bmp.replace('Manufactured Device - ',
                          'Manufactured Device -\n')

        if efflonly:
            bmp += '\n(effluent only)'

        return bmp

"""
