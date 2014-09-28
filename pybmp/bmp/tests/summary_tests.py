import sys
import os

pythonversion = sys.version_info.major
if pythonversion == 3:
    from io import StringIO
else:
    from StringIO import StringIO

from nose.tools import *
import numpy as np
import numpy.testing as nptest

from pybmp import bmp
from pybmp import utils


@nottest
class mock_figure(object):
    def savefig(self, *args, **kwargs):
        pass

@nottest
class mock_parameter(object):
    def __init__(self):
        self.name = 'Carbon Dioxide'
        self.tex = r'$[\mathrm{CO}_2]$'
        self.units = 'mg/L'

    def paramunit(self, *args, **kwargs):
        return 'Carbon Dioxide (mg/L)'

@nottest
class mock_location(object):
    def __init__(self, include):
        self.N = 20
        self.ND = 5
        self.min = 0.123456
        self.max = 123.456
        self.mean = 12.3456
        self.mean_conf_interval = np.array([-1, 1]) + self.mean
        self.logmean = 12.3456
        self.logmean_conf_interval = np.array([-1, 1]) + self.logmean
        self.geomean = 12.3456
        self.geomean_conf_interval = np.array([-1, 1]) + self.geomean
        self.std = 4.56123
        self.logstd = 4.56123
        self.cov = 5.61234
        self.skew = 6.12345
        self.pctl25 = 0.612345
        self.median = 1.23456
        self.median_conf_interval = np.array([-1, 1]) + self.median
        self.pctl75 = 2.34561
        self.include = include
        self.exclude = not self.include

    pass

@nottest
class mock_dataset(object):
    def __init__(self, infl_include, effl_include):
        self.influent = mock_location(infl_include)
        self.effluent = mock_location(effl_include)

        self.n_pairs = 20
        self.wilcoxon_p = 0.0005
        self.mannwhitney_p = 0.456123
        self.definition = {
            'parameter': mock_parameter(),
            'category': 'testbmp'
        }

    def scatterplot(self, *args, **kwargs):
        return mock_figure()

    def statplot(self, *args, **kwargs):
        return mock_figure()


class _base_DatasetSummary_Mixin(object):
    def main_setup(self):
        self.known_paramgroup = 'Metals'
        self.known_bmp = 'testbmp'
        self.known_latex_file_name = 'metalstestbmpcarbondioxide'
        self.ds_sum = bmp.DatasetSummary(self.ds, self.known_paramgroup, 'testfigpath')
        self.known_latex_input_tt = r"""\subsection{testbmp}
        \begin{table}[h!]
            \caption{test table title}
            \centering
            \begin{tabular}{l l l l l}
                \toprule
                \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\
                \toprule
                Count & 20 & 20 \\
                \midrule
                Number of NDs & 5 & 5 \\
                \midrule
                Min, Max & 0.123, 123 & 0.123, 123 \\
                \midrule
                Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Log. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Log. Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Geo. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Covariance & 5.61 & 5.61 \\
                \midrule
                Skewness & 6.12 & 6.12 \\
                \midrule
                Median & 1.23 & 1.23 \\
                %%
                (95\% confidence interval) & (0.235, 2.23) & (0.235, 2.23) \\
                \midrule
                Quartiles & 0.612, 2.35 & 0.612, 2.35 \\
                \toprule
                Number of Pairs & \multicolumn{2}{c} {20} \\
                \midrule
                Wilcoxon p-value & \multicolumn{2}{c} {$<0.001$} \\
                \midrule
                Mann-Whitney p-value & \multicolumn{2}{c} {0.456} \\
                \bottomrule
            \end{tabular}
        \end{table}

        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfigpath/statplot/metalstestbmpcarbondioxidestats.pdf}
            \caption{Box and Probability Plots of Carbon Dioxide at testbmp BMPs}
        \end{figure}

        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfigpath/scatterplot/metalstestbmpcarbondioxidescatter.pdf}
            \caption{Influent vs. Effluent Plots of Carbon Dioxide at testbmp BMPs}
        \end{figure} \clearpage""" + '\n'

        self.known_latex_input_ff = ''
        self.known_latex_input_ft = r"""\subsection{testbmp}
        \begin{table}[h!]
            \caption{test table title}
            \centering
            \begin{tabular}{l l l l l}
                \toprule
                \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\
                \toprule
                Count & NA & 20 \\
                \midrule
                Number of NDs & NA & 5 \\
                \midrule
                Min, Max & NA & 0.123, 123 \\
                \midrule
                Mean & NA & 12.3 \\
                %%
                (95\% confidence interval) & NA & (11.3, 13.3) \\
                \midrule
                Standard Deviation & NA & 4.56 \\
                \midrule
                Log. Mean & NA & 12.3 \\
                %%
                (95\% confidence interval) & NA & (11.3, 13.3) \\
                \midrule
                Log. Standard Deviation & NA & 4.56 \\
                \midrule
                Geo. Mean & NA & 12.3 \\
                %%
                (95\% confidence interval) & NA & (11.3, 13.3) \\
                \midrule
                Covariance & NA & 5.61 \\
                \midrule
                Skewness & NA & 6.12 \\
                \midrule
                Median & NA & 1.23 \\
                %%
                (95\% confidence interval) & NA & (0.235, 2.23) \\
                \midrule
                Quartiles & NA & 0.612, 2.35 \\
                \toprule
                Number of Pairs & \multicolumn{2}{c} {NA} \\
                \midrule
                Wilcoxon p-value & \multicolumn{2}{c} {NA} \\
                \midrule
                Mann-Whitney p-value & \multicolumn{2}{c} {NA} \\
                \bottomrule
            \end{tabular}
        \end{table}

        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfigpath/statplot/metalstestbmpcarbondioxidestats.pdf}
            \caption{Box and Probability Plots of Carbon Dioxide at testbmp BMPs}
        \end{figure}

        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfigpath/scatterplot/metalstestbmpcarbondioxidescatter.pdf}
            \caption{Influent vs. Effluent Plots of Carbon Dioxide at testbmp BMPs}
        \end{figure} \clearpage""" + '\n'

    def test_paramgroup(self):
        assert_true(hasattr(self.ds_sum, 'paramgroup'))
        assert_true(isinstance(self.ds_sum.paramgroup, str))
        assert_equal(self.ds_sum.paramgroup, self.known_paramgroup)

    def test_ds(self):
        assert_true(hasattr(self.ds_sum, 'ds'))
        assert_true(isinstance(self.ds_sum.ds, mock_dataset))

    def test_parameter(self):
        assert_true(hasattr(self.ds_sum, 'parameter'))
        assert_true(isinstance(self.ds_sum.parameter, mock_parameter))

    def test_bmp(self):
        assert_true(hasattr(self.ds_sum, 'bmp'))
        assert_true(isinstance(self.ds_sum.bmp, str))
        assert_equal(self.ds_sum.bmp, self.known_bmp)

    def test_latex_file_name(self):
        assert_true(hasattr(self.ds_sum, 'latex_file_name'))
        assert_true(isinstance(self.ds_sum.latex_file_name, str))
        assert_equal(self.ds_sum.latex_file_name, self.known_latex_file_name)

    def test__tex_table_row_basic(self):
        r = self.ds_sum._tex_table_row('The Medians', 'median')
        assert_equal(r, self.known_r_basic)

    def test__tex_table_row_advanced(self):
        r = self.ds_sum._tex_table_row('Mean CI', 'mean_conf_interval', rule='top',
                                   twoval=True, ci=True, sigfigs=2)
        assert_equal(r, self.known_r_advanced)

    def test__text_table_row_twoattrs(self):
        r = self.ds_sum._tex_table_row('Quartiles', ['pctl25', 'pctl75'], twoval=True)
        assert_equal(r, self.known_r_twoattrs)

    def test__make_tex_figure(self):
        fig = self.ds_sum._make_tex_figure('testfig.png', 'test caption')
        known_fig = r"""
        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfig.png}
            \caption{test caption}
        \end{figure} \clearpage""" + '\n'
        assert_equal(fig, known_fig)

    def test_makeTexInput(self):
        if self.scenario == 'TT':
            known_tstring = self.known_latex_input_tt
        elif self.scenario == 'FT':
            known_tstring = self.known_latex_input_ft
        else:
            known_tstring = self.known_latex_input_ff

        tstring = self.ds_sum.makeTexInput('test table title')

        try:
            assert_equal(tstring, known_tstring)
        except:
            with open('{}_out_test.test'.format(self.scenario), 'w') as test:
                test.write(tstring)

            with open('{}_out_known.test'.format(self.scenario), 'w') as known:
                known.write(known_tstring)
            raise


class test_DatasetSummary_TT(_base_DatasetSummary_Mixin):
    def setup(self):
        self.scenario = 'TT'
        self.ds = mock_dataset(True, True)
        self.known_r_basic = r'''
                \midrule
                The Medians & 1.23 & 1.23 \\'''

        self.known_r_advanced = r'''
                \toprule
                Mean CI & (11, 13) & (11, 13) \\'''

        self.known_r_twoattrs = r'''
                \midrule
                Quartiles & 0.612, 2.35 & 0.612, 2.35 \\'''

        self.main_setup()

    def test__make_tex_table(self):
        table = self.ds_sum._make_tex_table('test title')
        known_table = r"""
        \begin{table}[h!]
            \caption{test title}
            \centering
            \begin{tabular}{l l l l l}
                \toprule
                \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\
                \toprule
                Count & 20 & 20 \\
                \midrule
                Number of NDs & 5 & 5 \\
                \midrule
                Min, Max & 0.123, 123 & 0.123, 123 \\
                \midrule
                Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Log. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Log. Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Geo. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Covariance & 5.61 & 5.61 \\
                \midrule
                Skewness & 6.12 & 6.12 \\
                \midrule
                Median & 1.23 & 1.23 \\
                %%
                (95\% confidence interval) & (0.235, 2.23) & (0.235, 2.23) \\
                \midrule
                Quartiles & 0.612, 2.35 & 0.612, 2.35 \\
                \toprule
                Number of Pairs & \multicolumn{2}{c} {20} \\
                \midrule
                Wilcoxon p-value & \multicolumn{2}{c} {$<0.001$} \\
                \midrule
                Mann-Whitney p-value & \multicolumn{2}{c} {0.456} \\
                \bottomrule
            \end{tabular}
        \end{table}""" + '\n'
        try:
            assert_equal(table, known_table)
        except:
            with open('make_tex_table_res.test', 'w') as f:
                f.write(table)
            with open('make_tex_table_exp.test', 'w') as f:
                f.write(known_table)
            raise


class test_DatasetSummary_TF(_base_DatasetSummary_Mixin):
    def setup(self):
        self.scenario = 'TF'
        self.ds = mock_dataset(True, False)
        self.main_setup()
        self.known_r_basic = r'''
                \midrule
                The Medians & 1.23 & NA \\'''

        self.known_r_advanced = r'''
                \toprule
                Mean CI & (11, 13) & NA \\'''

        self.known_r_twoattrs = r'''
                \midrule
                Quartiles & 0.612, 2.35 & NA \\'''


class test_DatasetSummary_FT(_base_DatasetSummary_Mixin):
    def setup(self):
        self.scenario = 'FT'
        self.ds = mock_dataset(False, True)
        self.main_setup()
        self.known_r_basic = r'''
                \midrule
                The Medians & NA & 1.23 \\'''

        self.known_r_advanced = r'''
                \toprule
                Mean CI & NA & (11, 13) \\'''

        self.known_r_twoattrs = r'''
                \midrule
                Quartiles & NA & 0.612, 2.35 \\'''


class test_DatasetSummary_FF(_base_DatasetSummary_Mixin):
    def setup(self):
        self.scenario = 'FF'
        self.ds = mock_dataset(False, False)
        self.main_setup()
        self.known_r_basic = r'''
                \midrule
                The Medians & NA & NA \\'''

        self.known_r_advanced = r'''
                \toprule
                Mean CI & NA & NA \\'''

        self.known_r_twoattrs = r'''
                \midrule
                Quartiles & NA & NA \\'''


class test_CategoricalSummary(object):
    def setup(self):
        includes = [
            (True, True),
            (True, False),
            (True, True),
            (False, False),
            (False, True)
        ]
        self.datasets = [mock_dataset(*inc) for inc in includes]
        self.known_paramgroup = 'Metals'
        self.known_dataset_count = 3
        self.csum = bmp.CategoricalSummary(self.datasets, self.known_paramgroup, 'basepath', 'testfigpath')
        self.known_latex_input_content = input_file_string
        self.known_latex_report_content = (
            '\\begin{document}test report title\n'
            '\\input{testpath.tex}\n'
            '\\end{document}\n'
        )

        self.test_templatefile = 'testtemplate.tex'
        with open(self.test_templatefile, 'w') as f:
            f.write('\\begin{document}__VARTITLE')

    def teardown(self):
        os.remove(self.test_templatefile)

    def test_datasets(self):
        assert_true(hasattr(self.csum, 'datasets'))
        for ds in self.csum.datasets:
            assert_true(isinstance(ds, mock_dataset))

        assert_equal(self.known_dataset_count, len(self.csum.datasets))

    def test_paramgroup(self):
        assert_true(hasattr(self.csum, 'paramgroup'))
        assert_true(isinstance(self.csum.paramgroup, str))
        assert_equal(self.csum.paramgroup, self.known_paramgroup)

    @nptest.dec.skipif(pythonversion == 2)
    def test__make_input_file_IO(self):
        with StringIO() as inputIO:
            self.csum._make_input_file_IO(inputIO)
            input_string = inputIO.getvalue()

        try:
            assert_equal(input_string, self.known_latex_input_content)
        except:
            with open('test__make_input_file_IO_res.test', 'w') as f:
                f.write(input_string)

            with open('test__make_input_file_IO_exp.test', 'w') as f:
                f.write(self.known_latex_input_content)

            raise

    @nptest.dec.skipif(pythonversion == 2)
    def test__make_report_IO(self):
        with StringIO() as reportIO:
            with open(self.test_templatefile, 'r') as templateIO:
                self.csum._make_report_IO(
                    templateIO, 'testpath.tex', reportIO, 'test report title'
                )


                assert_equal(reportIO.getvalue(), self.known_latex_report_content)



input_file_string = r'''\section{Carbon Dioxide}
\subsection{testbmp}
        \begin{table}[h!]
            \caption{Statistics for Carbon Dioxide (mg/L) at testbmp BMPs}
            \centering
            \begin{tabular}{l l l l l}
                \toprule
                \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\
                \toprule
                Count & 20 & 20 \\
                \midrule
                Number of NDs & 5 & 5 \\
                \midrule
                Min, Max & 0.123, 123 & 0.123, 123 \\
                \midrule
                Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Log. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Log. Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Geo. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Covariance & 5.61 & 5.61 \\
                \midrule
                Skewness & 6.12 & 6.12 \\
                \midrule
                Median & 1.23 & 1.23 \\
                %%
                (95\% confidence interval) & (0.235, 2.23) & (0.235, 2.23) \\
                \midrule
                Quartiles & 0.612, 2.35 & 0.612, 2.35 \\
                \toprule
                Number of Pairs & \multicolumn{2}{c} {20} \\
                \midrule
                Wilcoxon p-value & \multicolumn{2}{c} {$<0.001$} \\
                \midrule
                Mann-Whitney p-value & \multicolumn{2}{c} {0.456} \\
                \bottomrule
            \end{tabular}
        \end{table}

        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfigpath/statplot/metalstestbmpcarbondioxidestats.pdf}
            \caption{Box and Probability Plots of Carbon Dioxide at testbmp BMPs}
        \end{figure}

        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfigpath/scatterplot/metalstestbmpcarbondioxidescatter.pdf}
            \caption{Influent vs. Effluent Plots of Carbon Dioxide at testbmp BMPs}
        \end{figure} \clearpage
\clearpage
\subsection{testbmp}
        \begin{table}[h!]
            \caption{Statistics for Carbon Dioxide (mg/L) at testbmp BMPs}
            \centering
            \begin{tabular}{l l l l l}
                \toprule
                \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\
                \toprule
                Count & 20 & 20 \\
                \midrule
                Number of NDs & 5 & 5 \\
                \midrule
                Min, Max & 0.123, 123 & 0.123, 123 \\
                \midrule
                Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Log. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Log. Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Geo. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3, 13.3) & (11.3, 13.3) \\
                \midrule
                Covariance & 5.61 & 5.61 \\
                \midrule
                Skewness & 6.12 & 6.12 \\
                \midrule
                Median & 1.23 & 1.23 \\
                %%
                (95\% confidence interval) & (0.235, 2.23) & (0.235, 2.23) \\
                \midrule
                Quartiles & 0.612, 2.35 & 0.612, 2.35 \\
                \toprule
                Number of Pairs & \multicolumn{2}{c} {20} \\
                \midrule
                Wilcoxon p-value & \multicolumn{2}{c} {$<0.001$} \\
                \midrule
                Mann-Whitney p-value & \multicolumn{2}{c} {0.456} \\
                \bottomrule
            \end{tabular}
        \end{table}

        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfigpath/statplot/metalstestbmpcarbondioxidestats.pdf}
            \caption{Box and Probability Plots of Carbon Dioxide at testbmp BMPs}
        \end{figure}

        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfigpath/scatterplot/metalstestbmpcarbondioxidescatter.pdf}
            \caption{Influent vs. Effluent Plots of Carbon Dioxide at testbmp BMPs}
        \end{figure} \clearpage
\clearpage
\subsection{testbmp}
        \begin{table}[h!]
            \caption{Statistics for Carbon Dioxide (mg/L) at testbmp BMPs}
            \centering
            \begin{tabular}{l l l l l}
                \toprule
                \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\
                \toprule
                Count & NA & 20 \\
                \midrule
                Number of NDs & NA & 5 \\
                \midrule
                Min, Max & NA & 0.123, 123 \\
                \midrule
                Mean & NA & 12.3 \\
                %%
                (95\% confidence interval) & NA & (11.3, 13.3) \\
                \midrule
                Standard Deviation & NA & 4.56 \\
                \midrule
                Log. Mean & NA & 12.3 \\
                %%
                (95\% confidence interval) & NA & (11.3, 13.3) \\
                \midrule
                Log. Standard Deviation & NA & 4.56 \\
                \midrule
                Geo. Mean & NA & 12.3 \\
                %%
                (95\% confidence interval) & NA & (11.3, 13.3) \\
                \midrule
                Covariance & NA & 5.61 \\
                \midrule
                Skewness & NA & 6.12 \\
                \midrule
                Median & NA & 1.23 \\
                %%
                (95\% confidence interval) & NA & (0.235, 2.23) \\
                \midrule
                Quartiles & NA & 0.612, 2.35 \\
                \toprule
                Number of Pairs & \multicolumn{2}{c} {NA} \\
                \midrule
                Wilcoxon p-value & \multicolumn{2}{c} {NA} \\
                \midrule
                Mann-Whitney p-value & \multicolumn{2}{c} {NA} \\
                \bottomrule
            \end{tabular}
        \end{table}

        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfigpath/statplot/metalstestbmpcarbondioxidestats.pdf}
            \caption{Box and Probability Plots of Carbon Dioxide at testbmp BMPs}
        \end{figure}

        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfigpath/scatterplot/metalstestbmpcarbondioxidescatter.pdf}
            \caption{Influent vs. Effluent Plots of Carbon Dioxide at testbmp BMPs}
        \end{figure} \clearpage
\clearpage
'''



def test_dataDump():
    pass


def test_statDump():
    pass


def test__writeStatLine():
    pass


def test_writeDiffStatLine():
    pass


def test_diffStatsDump():
    pass


def test_sbpat_stats():
    pass


def test_latexInputFile():
    pass


def test_latexReport():
    pass


def test_paramTables():
    pass


def test_paramBoxplots():
    pass


def test_doBoxPlot():
    pass


def test_makeBMPLabel():
    pass
