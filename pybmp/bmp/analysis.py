from __future__ import division
import os

import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from . import dataAccess
from .. import utils

__all__ = ['Location', 'Statsummary', 'Dataset']


class Location:
    def __init__(self, table, parameter, bmpCat, station, minStudies=3, minDataPts=3):
        '''
        A class containing all the data from the inlets or outlets of a
        single BMP category for a single parameter.

        Input:
            table (bmp.dataAccess.Table object) : the original table passed
            bmpCat (string) : two-letter abbreviation of the BMP Category
            station (string): monitorign location at the BMP (Influent or Effluent)
            minStudies (int) : minimum number of studies required to use a dataset
            minDataPts (int) : minimum number of data points required to use a study

        Writes:
            None

        Returns:
            self.
                table (bmp.dataAccess.Table object) : the original table passed
                parameter (bmp.dataAccess.Parameter object) : the parameter included in the data
                bmpCat (string) : two-letter abbreviation of the BMP Category
                station (string): Influent or Effluent
                station_name (string) : Inflow or Outflow
                NStudies (int) : number of studies contributing to the data
                NDataPts (int) : number of valid results in the data
                exclude (bool) : True if data do not meet the requirements of
                    `minStudies` and `minDataPts`
                include (bool) : the opposite of exclude
                data (pandas dataframe) : cross-section the `table` from `table.getData;
                    NAs and irrelevent columns are dropped
                ros (utils.ros.MR object) : Regression on order statistics estimate of the dataset
                stats (analysis.statsummary object) : object containing convenient access to stats
                color (string) : color of the lines and markers in the plots
                marker (string) : shape of the markers for detected results
                markerND (string) : shape of the marker for non-detect results
        '''
        # check that we've got a valid BMP
        if not bmpCat in table.bmpCats:
            raise ValueError('BMP %s not present' % (bmpCat,))

        # meta data mappings based on station
        station_names = {'Influent': 'Inflow', 'Effluent': 'Outflow'}
        markers = {'Influent': ['o', 'v'], 'Effluent': ['s', '<']}
        colors = {'Influent': 'b', 'Effluent': 'g'}

        # basic attributes based on input
        self.table = table
        self.parameter = parameter
        self.bmpCat = bmpCat
        self.station = station
        try:
            self.station_name = station_names[station]
        except KeyError:
            raise ValueError("Station is either 'Influent' or 'Effluent'")

        # get data from `table`
        data = table.getData(parameter, bmpCat)[self.station_name]
        data = data.dropna(axis=0, subset=['res'])

        # get the unique studies and their number of data points
        all_studies = data.groupby(level='bmpid').size()

        # select out all of the studies with enough data
        good_studies = all_studies[all_studies >= minDataPts]

        # filter the data down to  just the studies with enough data
        # (x in the lambda express is the index of the data and
        #    and x[1] pulls out the BMP ID)
        data = data.select(lambda x: x[1] in good_studies)

        # determine the number if studies and data points
        self.NDataPts = good_studies.sum()
        self.NStudies = int(good_studies.shape[0])

        # if there's insufficient data, leave everythign out
        if (self.NStudies < minStudies):
            self.exclude = True
            self.data = None
            self.ros = None
            self.stats = None
        # otherwise stuff it all in there
        else:
            self.exclude = False
            self.data = data
            self.ros = utils.ros.MR(self.data)
            self.stats = Statsummary(self.ros.data)

        # remaining attributes
        self.include = not self.exclude
        self.marker = markers[self.station][0]
        self.markerND = markers[self.station][1]
        self.color = colors[self.station]


class Statsummary:
    def __init__(self, rosdata, qualcol='qual', bsIter=10000):
        '''
        Object providing convenient access to statics for data
        Input:
            rosdata (utils.ros object) : dataset with ROS-estimated values of NDs
            data (pandas dataframe) : raw dataset
            qualcol (string) : name of the column in `data` containing qualifiers
            bsIter (int, default 10**4) : number of interations to use when using
                a bootstrap algorithm to refine a statistic

        Writes:
            None

        Returns:
            Notes:
                * indicates that there's an accompyaning tuple of confidence
                  interval. For example, self.mean and self.mean_conf_interval
                + indicatates that there's a equivalent stat for log-transormed
                  data. For example, self.mean and self.log_mean. This is subject
                  to the absense of negitive results)


            self (arithmetic space)
                .N (int) : total number of results
                .ND (int) : number of non-detect results
                .min (float) : minimum value of the ROS'd data
                .max (float) : maximum value of the ROS'd data
                .mean*+ (float) : bootstrapped arithmetic mean of the ROS'd data
                .std*+ (float) bootstrapped standard deviation of the ROS'd data
                .geomean* (float) : geometric mean
                .geostd (float) : geometric standard deviation
                .cov (float) : covariance (absolute value of std/mean)
                .skew (float) : skewness coefficient
                .median* : median of the dataset
                .pctl[10/25/75/90] (float) : percentiles of the ROS'd dataset
                .pnorm (float) : results of the Shapiro-Wilks test for normality
                .plognorm (float) : results of the Shapiro-Wilks test for normality
                    on log-transormed data (so test for lognormalily).
                .analysis_space (string) : Based on the results of self.pnorm and
                    self.plognorm, this is either "normal" or "lognormal".
        '''

        # bootstrapping the basic stuff
        mean_BS = utils.bootstrap.Stat(rosdata.final_data, np.mean, NIter=bsIter)
        std_BS = utils.bootstrap.Stat(rosdata.final_data, np.std, NIter=bsIter)
        median_BS = utils.bootstrap.Stat(rosdata.final_data, np.median, NIter=bsIter)

        # simple stats
        self.N = rosdata.final_data.shape[0]
        self.ND = (rosdata[qualcol] == 'ND').sum()
        self.min = rosdata.final_data.min()
        self.max = rosdata.final_data.max()
        self.mean, self.mean_conf_interval = mean_BS.BCA()
        self.std = std_BS.BCA()[0]

        # log/geo stats if there are no negative values
        if rosdata.final_data.min() > 0:
            logmean_BS = utils.bootstrap.Stat(np.log(rosdata.final_data), np.mean, NIter=bsIter)
            logstd_BS = utils.bootstrap.Stat(np.log(rosdata.final_data), np.std, NIter=bsIter)
            self.logmean, self.logmean_conf_interval = logmean_BS.BCA()
            self.logstd = logstd_BS.BCA()[0]
            self.geomean = np.exp(self.logmean)
            self.geomean_conf_interval = np.exp(self.logmean_conf_interval)
            self.geostd = np.exp(self.logstd)

        # otehrwise, return NAs
        else:
            self.logmean = np.nan
            self.logmean_conf_interval = (np.nan, np.nan)
            self.logstd = np.nan
            self.geomean = np.nan
            self.geomean_conf_interval = (np.nan, np.nan)
            self.geostd = np.nan

        # remaining basic stats
        self.cov = rosdata.final_data.std()/np.abs(self.mean)
        self.skew = stats.skew(rosdata.final_data)
        self.median, self.median_conf_interval = median_BS.BCA()
        self.pctl10 = stats.scoreatpercentile(rosdata.final_data, 10)
        self.pctl25 = stats.scoreatpercentile(rosdata.final_data, 25)
        self.pctl75 = stats.scoreatpercentile(rosdata.final_data, 75)
        self.pctl90 = stats.scoreatpercentile(rosdata.final_data, 90)

        # test for normality
        self.pnorm = stats.shapiro(rosdata.final_data)[1]

        # test for lognormality
        self.plognorm = stats.shapiro(np.log(rosdata.final_data))[1]

        # comput the result of tests
        if self.plognorm >= self.pnorm and self.plognorm > 0.1:
            self.analysis_space = 'lognormal'
        else:
            self.analysis_space = 'normal'


class Dataset:
    def __init__(self, table, parameter, bmpCat, exclLevel='studies', minStudies=3, minDataPts=3, xlsDataDumpFile=None):
        '''
        A class containing all the data from the inlets and outlets of a
        single BMP category for a single parameter.

        Input:
            table (bmp.dataAccess.Table object) : the original table passed
            bmpCat (string) : two-letter abbreviation of the BMP Category
            minStudies (int) : minimum number of studies required to use a dataset
            minDataPts (int) : minimum number of data points required to use a study
            xlsDataDumpFile (string) : name of Excel file to dump all of the data

        Writes:
            None

        Returns:
            self.
                table (bmp.dataAccess.Table object) : the original table passed
                parameter (bmp.dataAccess.Parameter object) : the parameter included in the data
                bmpCat (string) : two-letter abbreviation of the BMP Category
                bmpCatName (string) : full name of the BMP category
                NStudies (int) : number of studies contributing to the data
                NDataPts (int) : number of valid results in the data
                minStudies (int) : minimum number of studies required to use a dataset
                minDataPts (int) : minimum number of data points required to use a study
                data (pandas dataframe) : cross-section the `table` from `table.getData
                paired_data (pandas dataframe) : same as `data` but with NAs dropped
                influent (Location instance) : influent data object
                effluent (Location instance) : effluent data object
                wilcoxon_z (float) : result of the Wilcoxon paired test for independence
                wilcoxon_p (float) : p-value of the Wilcoxon paired test for independence
                mannwhitney_u (float) : result of the Mann-Whitney test for independence (non-paired)
                mannwhitney_u (float) : p-value of the Mann-Whitney test for independence (non-paired)
                kendall_tau (float) : the tau statistic from Kendall's tau (nonparametric correlation for ordinal data)
                kendall_p (float) : the two-sided p-value for a hypothesis test whose null hypothesis is an absence of association, tau = 0.
                spearman_rho (float) : Spearman correlation coefficient
                spearman_p (float) : the two-sided p-value for a hypothesis test whose null hypothesis is that two sets of data are uncorrelated
                theil_medslope (float) : Theil slope (slope of line derived from non-parametric linear regression)
                theil_intercept (float) : Intercept of the Theil line, as median(y)-medslope*median(x)
                theil_lo_slope (float) : Lower bound of the confidence interval on medslope
                theil_hi_slope (float) : Upper bound of the confidence interval on medslope

        TODO: filenames (table, figures, input) should be attributes of the dataset
        '''

        # meta info
        self.table = table
        self.bmpCat = bmpCat
        self.bmpCatName = table.bmpCatNames[bmpCat]
        self.parameter = parameter
        self.minStudies = 3
        self.minDataPts = 3
        #self.exclusion_level = exclLevel
        #self.exclusion_threshold = exclThreshold

        # dataframes of the data and paired data
        self.data = table.getData(parameter, bmpCat, paired=False)
        self.paired_data = table.getData(parameter, bmpCat, paired=True)

        # create influent and effluent objects
        self.influent = Location(table, parameter, self.bmpCat, 'Influent',
                                 minDataPts=minDataPts, minStudies=minStudies)
        self.effluent = Location(table, parameter, self.bmpCat, 'Effluent',
                                 minDataPts=minDataPts, minStudies=minStudies)

        # excel dump file
        self.dumpFile = xlsDataDumpFile

        # place holders for stats
        self.wilcoxon_z = None
        self.wilcoxon_p = None
        self.mannwhitney_u = None
        self.mannwhitney_p = None
        self.kendall_tau = None
        self.kendall_p = None
        self.spearman_rho = None
        self.spearman_p = None
        self.theil_medslope = None
        self.theil_intercept = None
        self.theil_lo_slope = None
        self.theil_hi_slope = None

        # compute additional stats (tests for independence)
        if self.influent.stats is not None and self.effluent.stats is not None \
                and self.influent.stats.N >= 20 and self.effluent.stats.N >= 20:

            # paired tests (calls to `to_list` are for rpy)
            self.wilcoxon_z, self.wilcoxon_p = \
                stats.wilcoxon(np.log10(self.paired_data.Inflow.res),
                               np.log10(self.paired_data.Outflow.res))

            # non-paired tests (calls to `to_list` are for rpy)
            try:
                self.mannwhitney_u, self.mannwhitney_p = \
                    stats.mannwhitneyu(self.influent.ros.data.final_data,
                                       self.effluent.ros.data.final_data)

            except ValueError as e:
                print('{0} on {1} at {2}'.format(e, self.parameter.name, self.bmpCat))

            if self.paired_data.shape[0] > 10:
                # compute ROS objects for the paired data:
                paired_ros_in = utils.ros.MR(self.paired_data['Inflow'])
                paired_ros_out = utils.ros.MR(self.paired_data['Outflow'])

                percentND_in = self.influent.stats.ND / self.influent.stats.N
                percentND_out = self.effluent.stats.ND / self.effluent.stats.N

                # Section for Theil slope and Kendall's tau, Spearman's rho stats
                if percentND_in <= 0.5 and percentND_out <= 0.5:
                    self.kendall_tau, self.kendall_p = \
                        stats.kendalltau(self.paired_data.Inflow.res,
                                         self.paired_data.Outflow.res)

                    self.spearman_rho, self.spearman_p = \
                        stats.spearmanr(paired_ros_in.data.final_data.values,
                                        paired_ros_out.data.final_data.values)

                    # XXX: Theil slopes need relatively few NDs
                    try:
                        self.theil_medslope, self.theil_intercept, self.theil_lo_slope, self.theil_hi_slope = \
                            stats.mstats.theilslopes(paired_ros_out.data.final_data.values,
                                                     paired_ros_in.data.final_data.values)
                    except ValueError as e:
                        print("Can't compute Theil Slopes for %s/%s. MSG: %s" % \
                              (self.parameter.name, self.bmpCatName, e))

    def statplot(self, figprefix=r'bmp/tex/statplot', pos=0):
        '''
        Creates side-by-side boxplots and probability plots
        Inputs:
            figprefix (string, default r'bmp/tex/statplot') : start of the figure's filename.
                (the rest is filled in with attributes of the dataset)
            pos (int, default 0) : start position along x-axis where the
                boxplots should go

        Writes:
            A PDF image of the figure.

        Returns:
            None
        '''
        # setup the figure and axes
        fig = plt.figure(figsize=(6.40, 3.00), facecolor='none',
                         edgecolor='none')
        ax1 = plt.subplot2grid((1, 4), (0, 0))
        ax2 = plt.subplot2grid((1, 4), (0, 1), colspan=3)

        # initilize xtick labels for the boxplots
        datalabeltext = []

        # loop through influent and effluent and
        # plot them if there are sufficient data
        for loc in [self.influent, self.effluent]:
            if loc.include:
                pos += 1

                if self.table.name == 'bacteria':
                    meanval = loc.stats.geomean
                else:
                    meanval = loc.stats.mean

                # add the boxplot and make it pretty
                bp = utils.figutils.boxplot(ax1, loc.ros.final_data, pos,
                                            statsummary=loc.stats,
                                            meancolor=loc.color,
                                            meanmarker=loc.marker,
                                            mean=meanval)
                utils.figutils.formatBoxplot(bp, loc.color, loc.marker)

                # add the probplot
                utils.figutils.probplot(ax2, loc.ros.Z, loc.ros.final_data,
                                        loc.color, loc.marker[0], loc.station)

                # add the datalabel for this location
                datalabeltext.append(loc.station)

        # check to see if we plotted anything, makes the axes
        # ticks, labels, and scales look good.
        if pos > 0:
            utils.figutils.formatStatAxes(ax1, 'boxplot', pos=pos,
                                          datalabels=datalabeltext,
                                          parameter=self.parameter)
            utils.figutils.formatStatAxes(ax2, 'probplot', N=loc.stats.N)

        # generate a unique filename
        rawfigname = '%s_%s%s_prob.pdf' % (self.table.name, self.bmpCat, self.parameter.name)
        figname = utils.processFilename(rawfigname)
        figpath = os.path.join(figprefix, figname)

        # optimize the layout and save the figure
        fig.tight_layout()
        fig.savefig(figpath, transparent=True)
        plt.close(fig)

    def detectionIndex(self):
        '''
        Returns indices of data for every combination of
        detected and non-detect data at the inlets and outlets.

        Inputs:
            None

        Writes:
            None

        Returns:
            Four dataframes of each combination of detected/non-detect
            for the influent/effluent data.

        TODO: Deprecated this. This should be easy enough to do with
            fancy indexing (only used in self.scatterplot)
        '''

        # both detected
        d_d = self.paired_data[(self.paired_data.Inflow.qual != 'ND') &
                               (self.paired_data.Outflow.qual != 'ND')]

        # inflow detect & outflow non-detect
        d_nd = self.paired_data[(self.paired_data.Inflow.qual != 'ND') &
                                (self.paired_data.Outflow.qual == 'ND')]

        # inflow non-detect & outflow detect
        nd_d = self.paired_data[(self.paired_data.Inflow.qual == 'ND') &
                                (self.paired_data.Outflow.qual != 'ND')]

        # inflow detect & outflow detect
        nd_nd = self.paired_data[(self.paired_data.Inflow.qual == 'ND') &
                                 (self.paired_data.Outflow.qual == 'ND')]

        return d_d, d_nd, nd_d, nd_nd

    def scatterplot(self, figprefix=r'bmp/tex/scatterplot'):
        '''
        Creates a scatter plot of effluent vs influent data
        Inputs:
            figprefix (string, default r'bmp/tex/statplot') : start of the figure's filename.
                (the rest is filled in with attributes of the dataset)

        Writes:
            Image of the plot

        Returns:
            None
        '''

        # figure/axes dimentsions
        fig_w = 4.25
        fig_h = 4.5
        ax_dim = 3.23
        h_pad = 0.50
        w_pad = 0.75

        # setup the figure (square axes is important)
        fig = plt.figure(figsize=(fig_w, fig_h), facecolor='none', edgecolor='none')
        ax1 = fig.add_axes([w_pad/fig_w, h_pad/fig_h, ax_dim/fig_w, ax_dim/fig_h])

        # indices of detect/non-detect combos
        d_d, d_nd, nd_d, nd_nd = self.detectionIndex()

        # plot detect/detect
        ax1.plot(d_d.Inflow.res, d_d.Outflow.res,
                 marker='o', mec='k', mfc='none', ms=4, ls='none',
                 label='Detected data pairs', zorder=10, alpha=0.85)

        # plot non-detect/detect
        ax1.plot(nd_d.Inflow.res, nd_d.Outflow.res,
                 marker='v', mec='k', mfc='none', ms=4, ls='none',
                 label='Influent not detected', zorder=10, alpha=0.75)

        # plot detect/non-detect
        ax1.plot(d_nd.Inflow.res, d_nd.Outflow.res,
                 marker='<', mec='k', mfc='none', ms=4,  ls='none',
                 label='Effluent not detected', zorder=10, alpha=0.75)

        # plot non-detect/non-detect
        ax1.plot(nd_nd.Inflow.res, nd_nd.Outflow.res,
                 marker='d', mec='k', mfc='none', ms=4, ls='none',
                 label='Infl. and effl. not detected', zorder=10, alpha=0.70)

        # label the figure
        xlabel = 'Influent %s (%s)' % (self.parameter.tex, self.parameter.units)
        ylabel = 'Effluent %s (%s)' % (self.parameter.tex, self.parameter.units)

        # format the gridlines
        utils.figutils.gridlines(ax1, xlabel, ylabel)

        # format the x/y tick labels
        ax1.xaxis.set_major_formatter(mticker.FuncFormatter(utils.figutils.ylabelFormatter))
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(utils.figutils.ylabelFormatter))

        # set equal axes limits for x/y
        ax_min = np.min([ax1.get_xlim()[0], ax1.get_ylim()[0]])
        ax_max = np.max([ax1.get_xlim()[1], ax1.get_ylim()[1]])
        ax1.set_xlim([ax_min, ax_max])
        ax1.set_ylim([ax_min, ax_max])

        # plot the one-to-one line
        ax1.plot([ax_min, ax_max], [ax_min, ax_max], 'k-', lw=1.25,
                 zorder=9, label='1:1 line')

        # create and format the legend
        leg = ax1.legend(bbox_to_anchor=(0.00, 1.02, 1.00, 0.10), loc=3,
                         ncol=2, mode="expand", borderaxespad=0.05)
        leg.get_frame().set_alpha(0.00)
        leg.get_frame().set_edgecolor('none')

        # get a figure name
        figname = utils.processFilename('%s_%s%s_scatter.pdf' %
                                        (self.table.name, self.bmpCat,
                                         self.parameter.name))
        figpath = os.path.join(figprefix, figname)

        # enfore the square axes
        ax1.set_aspect('equal')

        # save and close everything
        fig.savefig(figpath, transparent=True)
        plt.close(fig)

    def _tex_table_row(self, name, attribute, rule='mid', twoval=False, sigfigs=3, ci=False):
        rulemap = {
            'top': r'\toprule',
            'mid': r'\midrule',
            'bottom': r'bottomrule',
            'none': r'',
        }

        try:
            rulemap[rule]
        except KeyError:
            raise KeyError('top, mid, bottom rules or none allowed')

        valstrings = []
        for loc in [self.influent, self.effluent]:
            if loc.include:
                if hasattr(attribute, 'append'):
                    val = [utils.nested_getattr(loc, attr)
                           for attr in attribute]
                else:
                    val = utils.nested_getattr(loc, attribute)

                if twoval:
                    thisstring = '%s, %s' % \
                                 (utils.sigFigs(val[0], sigfigs),
                                  utils.sigFigs(val[1], sigfigs))

                    if ci:
                        thisstring = '(%s)' % thisstring

                else:
                    thisstring = utils.sigFigs(val, sigfigs)

                valstrings.append(thisstring)

            else:
                valstrings.append('NA')

        row = r"""\\
        %s
        %s & %s & %s""" % (rulemap[rule], name, valstrings[0], valstrings[1])

        return row

    def makeTexTable(self):
        '''
            Generate a LaTeX table comparing the stats of `self.influent`
                and `self.effluent`.

            Input:
                None

            Writes:
                None

            Returns:
                statsTable (string) : the LaTeX commands for the stat
                    summary table for the appendix reports
        '''

        # helper function to format small p-values
        def processPVals(pval):
            if pval is None:
                out = 'NA'

            elif pval < 0.001:
                out = "<0.001"
            else:
                out = '%0.3f' % pval

            return out

        # title and header info in the table
        tableTitle = 'Summary of %s at %s BMPs' % (self.parameter.tex, self.bmpCatName)
        top = r"""
        \begin{table}[h!]
            \caption{%s}
            \centering
            \begin{tabular}{l l l l l}
            \toprule
            \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet}""" % \
            (tableTitle, )

        # row for the number of results
        row_count = self._tex_table_row('Count', 'stats.N', rule='top',
                                        sigfigs=0)

        # row for the number of non-detect results
        row_Nnd = self._tex_table_row('Number of Non-detects',  'stats.ND',
                                      rule='mid', sigfigs=0)

        # row for the number of studies
        row_NStudies = self._tex_table_row('Number of Studies', 'NStudies',
                                           rule='mid', sigfigs=0)

        # row for the min and max values
        # TODO: make it so that this isn't wrapped in ()'s
        row_minmax = self._tex_table_row('Min, Max (%s)' %
                                         (self.parameter.units,),
                                         ['stats.min', 'stats.max'],
                                         rule='mid', sigfigs=0, twoval=True)

        # row for the aritmetic mean
        row_mean = self._tex_table_row('Mean (%s)' % (self.parameter.units,),
                                       'stats.mean', rule='mid', sigfigs=3)

        # row for the confidence intervals around the mean
        row_meanCI = self._tex_table_row('(95\% confidence interval)',
                                         'stats.mean_conf_interval',
                                         rule='none', sigfigs=3, twoval=True)

        # row for the standard deviation
        row_std = self._tex_table_row('Standard Deviation (%s)' %
                                      (self.parameter.units,),
                                      'stats.std', rule='mid', sigfigs=3)

        # row for the mean of the logs of the data
        row_logmean = self._tex_table_row('Logarithmic Mean', 'stats.logmean',
                                          rule='mid', sigfigs=3)


        # row for the confidence intervals around logmean
        row_logmeanCI = self._tex_table_row('(95\% confidence interval)',
                                            'stats.logmean_conf_interval',
                                            rule='none', sigfigs=3, twoval=True)

        # row for the std. dev. of the logs of the data
        row_logstd = self._tex_table_row('Logarithmic Standard Deviation',
                                         'stats.logstd', rule='mid', sigfigs=3)

        # row for the geomeotric mean
        row_geomean = self._tex_table_row('Geometric Mean (%s)' %
                                          (self.parameter.units,),
                                          'stats.geomean', rule='mid',
                                          sigfigs=3)

        # row for the conf. intervals around the geomean
        row_geomeanCI = self._tex_table_row('(95\% confidence interval)',
                                            'stats.geomean_conf_interval',
                                            rule='none', sigfigs=3, twoval=True)

        # row for the geo. std. dev.
        row_geostd = self._tex_table_row('Geometric Standard Deviation (%s)' %
                                         (self.parameter.units,),
                                         'stats.geostd', rule='mid', sigfigs=3)

        # row for the coefficient of variation
        row_cov = self._tex_table_row('Coefficient of Variation',
                                      'stats.cov', rule='mid', sigfigs=3)

        # row for the skewness
        row_skew = self._tex_table_row('Skewness',
                                      'stats.skew', rule='mid', sigfigs=3)

        # row for the median
        row_med = self._tex_table_row('Median (%s)' % (self.parameter.units,),
                                      'stats.median', rule='mid', sigfigs=3)

        # row for the confidence intervals around the median
        row_medCI = self._tex_table_row('(95\% confidence interval)',
                                      'stats.median_conf_interval',
                                      rule='none', sigfigs=3, twoval=True)

        # row for the 1st and 3rd quartiles
        # TODO: make it so that this isn't wrapped in ()'s
        row_quartiles = self._tex_table_row(
                                            '25\ssu{th}, 75\ssu{th} percentiles (%s)' % \
                                            (self.parameter.units,),
                                            ['stats.pctl25', 'stats.pctl75'],
                                            rule='mid', sigfigs=3, twoval=True)

        # row for the number of data pairs
        row_npairs = r"""\\
        \toprule
        Number of data pairs & \multicolumn{2}{c}{%d}""" % \
            (self.paired_data.shape[0],)

        # row for the Wilcoxon Rank-Sum p-value
        row_wilcoxon = r""" \\
        \midrule
        Wilcoxon p-value & \multicolumn{2}{c}{%s}""" % \
            (processPVals(self.wilcoxon_p),)

        # row for the Mann-Whitney p-value
        row_mannwhit = r""" \\
        \midrule
        Mann-Whitney p-value & \multicolumn{2}{c}{%s}""" % \
            (processPVals(self.mannwhitney_p),)

        # table footer
        bottom = r""" \\
                \bottomrule
            \end{tabular}
        \end{table}"""

        # smush the whole table together
        statsTable = "%s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s\n" % \
            (top, row_count, row_Nnd, row_NStudies, row_minmax,
                row_mean, row_meanCI, row_std, row_geomean, row_geomeanCI,
                row_geostd, row_cov, row_skew, row_med, row_medCI,
                row_quartiles, row_npairs, row_wilcoxon, row_mannwhit, bottom)

        return statsTable

    def makeTexFigure(self, figFile, caption, pos='hb', clearpage=True):
        '''
        Create the LaTeX for include a figure in a document

        Input:
            figFile (string) : path to the image you want to include
            caption (string) : what it should say in the figure's caption
            pos (string, default 'hb') : placement preferences
                (h='here' or b='below')
            clearpage (bool, default True) : whether or not the LaTeX
                command "\clearpage" should be called after the figure

        Returns:
            figurestring (string) : the LaTeX string to include a figure
                in the appendix reports
        '''
        if clearpage:
            clrpage = r'\clearpage'
        else:
            clrpage = ''
        figurestring = r"""
        \begin{figure}[%s]   %% FIGURE
            \centering
            \includegraphics[scale=1.00]{%s}
            \caption{%s}
        \end{figure}         %% FIGURE
        %s
        """ % (pos, figFile, caption, clrpage)
        return figurestring

    def makeTexInputFile(self, subsection=True, figprefix=r'bmp/tex'):
        '''
        Creates an input file for a dataset  including a
            summary table, stat plot, and scatter plot.

        Input:
            subsection (bool, default True) : whether or not the data
                should go in its own subsection in the document
            figprefix (string, default r'bmp/tex') : start of the figure's filename.
                (the rest is filled in with attributes of the dataset)

        Writes:
            A full LaTeX input file for inclusion in a final or draft template

        Returns:
            filename (string) : path of the file that is written

        TODO: filenames should be attributes of the dataset
        '''
        # LaTeX file name and creation
        filename = utils.processFilename('%s_%s%s.tex' %
                                         (self.table.name, self.bmpCat,
                                         self.parameter.name))

        texfile = open(os.path.join(figprefix, 'input', filename), 'w')
        if subsection:
            texfile.write(r'\subsection{%s}' % (self.parameter.tex,))

        # filename of the stats plot
        prob_name = utils.processFilename('%s_%s%s_prob.pdf' %
                                          (self.table.name, self.bmpCat,
                                           self.parameter.name))
        #prob_path = os.path.join(figprefix, 'statplot', prob_name)
        prob_path2 = 'statplot' + '/' + prob_name

        # caption for the stats plot
        prob_caption = 'Box and Probability Plots of %s at %s BMPs' % \
            (self.parameter.tex, self.bmpCatName)

        # filename of the scatter plot
        scatter_name = utils.processFilename('%s_%s%s_scatter.pdf' %
                                             (self.table.name, self.bmpCat,
                                              self.parameter.name))

        #scatter_path = os.path.join(figprefix, 'scatterplot', scatter_name)
        scatter_path2 = 'scatterplot' + '/' + scatter_name

        # caption for the scatter plot
        scatter_caption = 'Influent vs. Effluent Plots of %s at %s BMPs' % \
            (self.parameter.tex, self.bmpCatName)

        # warning about having a lot of non-detects
        warning = '''Warning: there is a very high percentage of non-detects in
                     this data set. The hypothesis test results and other
                     statistics reported in this table may not be valid.\n'''

        # make the table and write it to the output file
        statTable = self.makeTexTable()
        texfile.write(statTable)

        # if there's enough effluent data
        if self.effluent.include:

            # if less than 80% of the data is ND
            if self.effluent.stats.ND/self.effluent.stats.N <= 0.8:

                # make the stat plot string
                statfig = self.makeTexFigure(prob_path2,
                                             prob_caption, clearpage=False)

                # make the scatter plot string
                scatterfig = self.makeTexFigure(scatter_path2,
                                                scatter_caption, clearpage=True)

                # write the strings to the file
                texfile.write(statfig)
                texfile.write(scatterfig)

            else:
                # if there are too many non-detect,
                # issue the warning
                texfile.write(warning)

        # close everything and return the filename
        texfile.close()
        return 'input' + '/' + filename

    def writeSummaryTableRow(self, xlsheet, row):
        '''
        Dump basic stats to an Excel file for the overall summaries

        Input:
            xlsheet (openpyxl worksheet) : the destination for the data
            row (int) : the row number where the data should be written

        Writes:
            Data into an existing Excel worksheet

        Returns:
            None
        '''
        # for the influent and effluent data
        for startcol, loc in zip([1, 2], [self.influent, self.effluent]):

            # if there's enough data, dump the stats
            if loc.include:
                xlsheet.cell(row=row, column=startcol+0).value = '%d, %d' % \
                    (loc.NStudies, loc.stats.N)
                xlsheet.cell(row=row, column=startcol+2).value = '%s' % \
                    (utils.sigFigs(loc.stats.pctl25, 3),)
                xlsheet.cell(row=row, column=startcol+4).value = '%s (%s, %s)' % \
                    (utils.sigFigs(loc.stats.median, 3),
                     utils.sigFigs(loc.stats.median_conf_interval[0], 3),
                     utils.sigFigs(loc.stats.median_conf_interval[1], 3))
                xlsheet.cell(row=row, column=startcol+6).value = '%s' % \
                    (utils.sigFigs(loc.stats.pctl75, 3),)

            # otherwise just write a bunch of NAs
            else:
                columns = range(startcol, 9, 2)
                for col in columns:
                    xlsheet.cell(row=row, column=col).value = 'NA'

    def writeSBPAT_stats(self, outfile, ignoreROS=False):
        '''
        Dump basic stats to an CSV file for SBPAT databases

        Input:
            outfile (file buffer): the destination for the data
            ignoreROS (bool, default false) : the row number where the data should be written

        Writes:
            Data into an existing CSV file

        Returns:
            None
        '''

        # if there's enough output data, create the row
        if self.effluent.include:

            # basuic info
            outfile.write('"%s",' % (self.parameter.name,))
            outfile.write('"%s",' % (self.bmpCat,))
            outfile.write('"%s",' % (self.parameter.std_units,))

            # quantity of input data
            if self.influent.include:
                outfile.write('%d,' % (self.influent.stats.N,))
                outfile.write('%d,' % (self.influent.stats.ND,))
            else:
                outfile.write('<3,')
                outfile.write('NA,')

            # quantity of output data
            outfile.write('%d,' % (self.effluent.stats.N,))
            outfile.write('%d,' % (self.effluent.stats.ND,))
            outfile.write('%d,' % (self.paired_data.shape[0],))
            outfile.write('"%s",' % (self.effluent.stats.analysis_space,))

            # write stats from the raw data
            if ignoreROS:
                logmean = np.mean(np.log(self.effluent.data.data))
                logmean_lcl = '--'
                logmean_ucl = '--'
                logstd = np.std(np.log(self.effluent.data.data))
                arimean = np.mean(self.effluent.data.data)
                arimean_lcl = '--'
                arimean_ucl = '--'
                aristd = np.std(self.effluent.data.data)
                pctl10 = stats.scoreatpercentile(self.effluent.data.data, 10)
                pctl50 = stats.scoreatpercentile(self.effluent.data.data, 50)
                pctl90 = stats.scoreatpercentile(self.effluent.data.data, 90)

                outfile.write('%f,' % (logmean,))
                outfile.write('%f,' % (logstd,))
                outfile.write('%f,' % (logmean_lcl))
                outfile.write('%f,' % (logmean_ucl))
                outfile.write('%f,' % (self.effluent.stats.plognorm,))
                outfile.write('%f,' % (arimean,))
                outfile.write('%f,' % (arimean_lcl))
                outfile.write('%f,' % (arimean_ucl))
                outfile.write('%f,' % (aristd,))
                outfile.write('%f,' % (self.effluent.stats.pnorm,))
                outfile.write('%f,' % (pctl10,))
                outfile.write('%f,' % (pctl50,))
                outfile.write('%f,' % (pctl90,))

            # write stats from the ROS estimates
            else:
                outfile.write('%f,' % (self.effluent.stats.logmean,))
                outfile.write('%f,' % (self.effluent.stats.logmean_conf_interval[0],))
                outfile.write('%f,' % (self.effluent.stats.logmean_conf_interval[1],))
                outfile.write('%f,' % (self.effluent.stats.logstd,))
                outfile.write('%f,' % (self.effluent.stats.plognorm,))
                outfile.write('%f,' % (self.effluent.stats.mean,))
                outfile.write('%f,' % (self.effluent.stats.mean_conf_interval[0],))
                outfile.write('%f,' % (self.effluent.stats.mean_conf_interval[1],))
                outfile.write('%f,' % (self.effluent.stats.std,))
                outfile.write('%f,' % (self.effluent.stats.pnorm,))
                outfile.write('%f,' % (self.effluent.stats.pctl10,))
                outfile.write('%f,' % (self.effluent.stats.median,))
                outfile.write('%f,' % (self.effluent.stats.pctl90,))

            # paired data stuff
            if self.wilcoxon_p < 0.1:
                outfile.write('"Yes",')
            else:
                outfile.write('"No",')

            if self.mannwhitney_p < 0.1:
                outfile.write('"Yes"\n')
            else:
                outfile.write('"No"\n')

    def transformParameters(existingparams, newparam, resfxn, qualfxn):
        for param in chain(existingparams, [newparam]):
            if preferred not in self._param_names:
                raise ValueError("Parameter %s is not in this dataset" % param)

        subset = self.data.select(lambda x: x[-1] in existingparams)

        # put the station into the row index and pivot the param into columns
        subset = subset.stack(level='Station')
        subset = subset.unstack(level='parameter')

        # put the station into the row index and pivot the param into columns
        subset = subset.stack(level='Station')
        subset = subset.unstack(level='parameter')

        # compute the right values
        subset[('qual', newname)] = subset.apply(resfxn, axis=1)
        subset[('res', newname)] = subset.apply(qualfxn, axis=1)

        # keep only the combined data
        subset = subset.select(lambda c: c[1] == newname, axis=1)

        # station goes back in into columns, parameters into rows
        subset = subset.unstack(level='Station')
        subset = subset.stack(level='parameter')

        # get the column indices in the right order
        subset.columns = subset.columns.swaplevel('Quantity', 'Station')

        # return the *full* dataset (preserving original params)
        self.data = pandas.concat([self.data, subset])

        # update the parameters
        self.parameters = self.getParameters()
        self._set_param_attributes()
