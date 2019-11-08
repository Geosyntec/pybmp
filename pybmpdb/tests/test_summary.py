import sys
import os
from io import StringIO
from pkg_resources import resource_filename
from textwrap import dedent
from tempfile import TemporaryDirectory

from unittest import mock
import pytest
import numpy.testing as nptest
import pandas.util.testing as pdtest
from wqio.tests import helpers

import numpy
from matplotlib import pyplot
import pandas
from engarde import checks

import wqio
from pybmpdb import summary, utils, bmpdb


mock_figure = mock.Mock(spec=pyplot.Figure)

PYTHON2 = sys.version_info.major == 2
SKIP_DB = True  # pyodbc is None or os.name == 'posix'


def get_data_file(filename):
    return resource_filename("pybmpdb.tests._data", filename)


def get_tex_file(filename):
    return resource_filename("pybmpdb.tex", filename)


class mock_parameter(object):
    def __init__(self):
        self.name = 'Carbon Dioxide'
        self.tex = r'$[\mathrm{CO}_2]$'
        self.units = 'mg/L'

    def paramunit(self, *args, **kwargs):
        return 'Carbon Dioxide (mg/L)'


class mock_location(object):
    def __init__(self, include):
        self.N = 25
        self.ND = 5
        self.min = 0.123456
        self.max = 123.456
        self.mean = 12.3456
        self.mean_conf_interval = numpy.array([-1, 1]) + self.mean
        self.logmean = 12.3456
        self.logmean_conf_interval = numpy.array([-1, 1]) + self.logmean
        self.geomean = 12.3456
        self.geomean_conf_interval = numpy.array([-1, 1]) + self.geomean
        self.std = 4.56123
        self.logstd = 4.56123
        self.cov = 5.61234
        self.skew = 6.12345
        self.pctl25 = 0.612345
        self.median = 1.23456
        self.median_conf_interval = numpy.array([-1, 1]) + self.median
        self.pctl75 = 2.34561
        self.include = include
        self.exclude = not self.include


class mock_dataset(object):
    def __init__(self, infl_include, effl_include):
        self.influent = mock_location(infl_include)
        self.effluent = mock_location(effl_include)

        self.n_pairs = 22
        self.wilcoxon_p = 0.0005
        self.mannwhitney_p = 0.456123
        self.definition = {
            'parameter': mock_parameter(),
            'category': 'testbmp'
        }
        self.scenario = (infl_include, effl_include)

    def scatterplot(self, *args, **kwargs):
        return mock_figure()

    def statplot(self, *args, **kwargs):
        return mock_figure()


@pytest.fixture(params=[
    (True, True),
    (True, False),
    (False, False),
    (False, True)
])
def dset_sum(request):
    ds = mock_dataset(request.param[0], request.param[1])
    return summary.DatasetSummary(ds, 'Metals', 'testfigpath')


def test_DatasetSummary_paramgroup(dset_sum):
    assert dset_sum.paramgroup == 'Metals'


def test_DatasetSummary_ds(dset_sum):
    assert isinstance(dset_sum.ds, mock_dataset)


def test_DatasetSummary_parameter(dset_sum):
    assert dset_sum.parameter is dset_sum.ds.definition['parameter']


def test_DatasetSummary_bmp(dset_sum):
    assert dset_sum.bmp is dset_sum.ds.definition['category']


def test_DatasetSummary_latex_file_name(dset_sum):
    assert dset_sum.latex_file_name == 'metalstestbmpcarbondioxide'


def test_DatasetSummary__tex_table_row_basic(dset_sum):
    expected = {
        (True, True): r'''
                \midrule
                The Medians & 1.23 & 1.23 \\''',
        (True, False): r'''
                \midrule
                The Medians & 1.23 & NA \\''',
        (False, True): r'''
                \midrule
                The Medians & NA & 1.23 \\''',
        (False, False): r'''
                \midrule
                The Medians & NA & NA \\'''
    }
    result_row = dset_sum._tex_table_row('The Medians', 'median')
    assert result_row == expected[dset_sum.ds.scenario]


def test_DatasetSummary__tex_table_row_forceint(dset_sum):
    expected = {
        (True, True): r'''
                \midrule
                Counts & 25 & 25 \\''',
        (True, False): r'''
                \midrule
                Counts & 25 & NA \\''',
        (False, True): r'''
                \midrule
                Counts & NA & 25 \\''',
        (False, False): r'''
                \midrule
                Counts & NA & NA \\'''
    }
    result_row = dset_sum._tex_table_row('Counts', 'N', forceint=True, sigfigs=1)
    assert result_row == expected[dset_sum.ds.scenario]


def test_DatasetSummary__tex_table_row_advanced(dset_sum):
    expected = {
        (True, True): r'''
                \toprule
                Mean CI & (11; 13) & (11; 13) \\''',
        (True, False): r'''
                \toprule
                Mean CI & (11; 13) & NA \\''',
        (False, True): r'''
                \toprule
                Mean CI & NA & (11; 13) \\''',
        (False, False): r'''
                \toprule
                Mean CI & NA & NA \\''',
    }
    result_row = dset_sum._tex_table_row('Mean CI', 'mean_conf_interval', rule='top',
                                         twoval=True, ci=True, sigfigs=2)
    assert result_row == expected[dset_sum.ds.scenario]


def test_DatasetSummary__text_table_row_twoattrs(dset_sum):
    expected = {
        (True, True): r'''
                \midrule
                Quartiles & 0.612; 2.35 & 0.612; 2.35 \\''',
        (True, False): r'''
                \midrule
                Quartiles & 0.612; 2.35 & NA \\''',
        (False, True): r'''
                \midrule
                Quartiles & NA & 0.612; 2.35 \\''',
        (False, False): r'''
                \midrule
                Quartiles & NA & NA \\''',
    }
    result_row = dset_sum._tex_table_row('Quartiles', ['pctl25', 'pctl75'], twoval=True)
    assert result_row == expected[dset_sum.ds.scenario]


def test_DatasetSummary__make_tex_figure(dset_sum):
    fig = dset_sum._make_tex_figure('testfig.png', 'test caption')
    known_fig = r"""
        \begin{figure}[hb]   % FIGURE
            \centering
            \includegraphics[scale=1.00]{testfig.png}
            \caption{test caption}
        \end{figure} \clearpage""" + '\n'
    assert fig == known_fig


def test_DatasetSummary_makeTexInput(dset_sum, expected_latext_input):
    result = dset_sum.makeTexInput('test table title')
    helpers.assert_bigstring_equal(result, expected_latext_input[dset_sum.ds.scenario])


def test_DatasetSummary__make_tex_table(dset_sum):
    if dset_sum.ds.scenario == (True, True):
        expected = r"""
        \begin{table}[h!]
            \caption{test title}
            \centering
            \begin{tabular}{l l l l l}
                \toprule
                \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\
                \toprule
                Count & 25 & 25 \\
                \midrule
                Number of NDs & 5 & 5 \\
                \midrule
                Min; Max & 0.123; 123 & 0.123; 123 \\
                \midrule
                Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                \midrule
                Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Log. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                \midrule
                Log. Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Geo. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                \midrule
                Coeff. of Variation & 5.61 & 5.61 \\
                \midrule
                Skewness & 6.12 & 6.12 \\
                \midrule
                Median & 1.23 & 1.23 \\
                %%
                (95\% confidence interval) & (0.235; 2.23) & (0.235; 2.23) \\
                \midrule
                Quartiles & 0.612; 2.35 & 0.612; 2.35 \\
                \toprule
                Number of Pairs & \multicolumn{2}{c} {22} \\
                \midrule
                Wilcoxon p-value & \multicolumn{2}{c} {$<0.001$} \\
                \midrule
                Mann-Whitney p-value & \multicolumn{2}{c} {0.456} \\
                \bottomrule
            \end{tabular}
        \end{table}""" + '\n'
        result = dset_sum._make_tex_table('test title')
        helpers.assert_bigstring_equal(result, expected)
    else:
        pass


@pytest.fixture
def expected_latext_input():
    return {
        (False, False): '',
        (True, False): '',
        (True, True): r"""\subsection{testbmp}
        \begin{table}[h!]
            \caption{test table title}
            \centering
            \begin{tabular}{l l l l l}
                \toprule
                \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\
                \toprule
                Count & 25 & 25 \\
                \midrule
                Number of NDs & 5 & 5 \\
                \midrule
                Min; Max & 0.123; 123 & 0.123; 123 \\
                \midrule
                Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                \midrule
                Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Log. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                \midrule
                Log. Standard Deviation & 4.56 & 4.56 \\
                \midrule
                Geo. Mean & 12.3 & 12.3 \\
                %%
                (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                \midrule
                Coeff. of Variation & 5.61 & 5.61 \\
                \midrule
                Skewness & 6.12 & 6.12 \\
                \midrule
                Median & 1.23 & 1.23 \\
                %%
                (95\% confidence interval) & (0.235; 2.23) & (0.235; 2.23) \\
                \midrule
                Quartiles & 0.612; 2.35 & 0.612; 2.35 \\
                \toprule
                Number of Pairs & \multicolumn{2}{c} {22} \\
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
        \end{figure} \clearpage""" + '\n',
        (False, True): r"""\subsection{testbmp}
        \begin{table}[h!]
            \caption{test table title}
            \centering
            \begin{tabular}{l l l l l}
                \toprule
                \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\
                \toprule
                Count & NA & 25 \\
                \midrule
                Number of NDs & NA & 5 \\
                \midrule
                Min; Max & NA & 0.123; 123 \\
                \midrule
                Mean & NA & 12.3 \\
                %%
                (95\% confidence interval) & NA & (11.3; 13.3) \\
                \midrule
                Standard Deviation & NA & 4.56 \\
                \midrule
                Log. Mean & NA & 12.3 \\
                %%
                (95\% confidence interval) & NA & (11.3; 13.3) \\
                \midrule
                Log. Standard Deviation & NA & 4.56 \\
                \midrule
                Geo. Mean & NA & 12.3 \\
                %%
                (95\% confidence interval) & NA & (11.3; 13.3) \\
                \midrule
                Coeff. of Variation & NA & 5.61 \\
                \midrule
                Skewness & NA & 6.12 \\
                \midrule
                Median & NA & 1.23 \\
                %%
                (95\% confidence interval) & NA & (0.235; 2.23) \\
                \midrule
                Quartiles & NA & 0.612; 2.35 \\
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
    }


@pytest.fixture
def cat_sum():
    includes = [
        (True, True),
        (True, False),
        (True, True),
        (False, False),
        (False, True)
    ]
    cs = summary.CategoricalSummary(
        [mock_dataset(*inc) for inc in includes],
        'Metals',
        'basepath',
        'testfigpath'
    )
    return cs


@pytest.fixture
def expected_latex_report():
    report = dedent("""\
        \\begin{document}test report title
        \\input{testpath.tex}
        \\end{document}
    """)
    return report


@pytest.fixture
def temp_template():
    with TemporaryDirectory() as datadir:
        filename = os.path.join(datadir, 'testtemplate.tex')
        with open(filename, 'w') as f:
            f.write('\\begin{document}__VARTITLE')

        yield filename


def test_CategoricalSummary_datasets(cat_sum):
    for ds in cat_sum.datasets:
        assert isinstance(ds, mock_dataset)

    assert len(cat_sum.datasets) == 3


def test_CategoricalSummary_paramgroup(cat_sum):
    assert isinstance(cat_sum.paramgroup, str)
    assert cat_sum.paramgroup == 'Metals'


def test_CategoricalSummary__make_input_file_IO(cat_sum, expected_latext_content):
    with StringIO() as inputIO:
        cat_sum._make_input_file_IO(inputIO)
        input_string = inputIO.getvalue()

    helpers.assert_bigstring_equal(input_string, expected_latext_content)


def test_CategoricalSummary__make_report_IO(cat_sum, expected_latex_report, temp_template):
    with StringIO() as report, open(temp_template, 'r') as template:
        cat_sum._make_report_IO(template, 'testpath.tex', report, 'test report title')
        helpers.assert_bigstring_equal(report.getvalue(), expected_latex_report)


def test_CategoricalSummary_makeReport(cat_sum, expected_latex_report, temp_template):
    templatepath = get_tex_file('draft_template.tex')
    inputpath = get_tex_file('inputs_{}.tex'.format(cat_sum.paramgroup.lower()))
    with TemporaryDirectory() as tmpdir:
        reportpath = os.path.join(tmpdir, 'report_{}.tex'.format(cat_sum.paramgroup.lower()))
        testpath = os.path.join(tmpdir, 'testpath.tex'.format(cat_sum.paramgroup.lower()))
        cat_sum.makeReport(
            temp_template,
            testpath,
            reportpath,
            'test report title',
            regenfigs=False
        )

        with open(reportpath, 'r') as rp:
            helpers.assert_bigstring_equal(rp.read(), expected_latex_report)


@pytest.fixture
def expected_latext_content():
    content = dedent(r"""        \section{Carbon Dioxide}
        \subsection{testbmp}
                \begin{table}[h!]
                    \caption{Statistics for Carbon Dioxide (mg/L) at testbmp BMPs}
                    \centering
                    \begin{tabular}{l l l l l}
                        \toprule
                        \textbf{Statistic} & \textbf{Inlet} & \textbf{Outlet} \\
                        \toprule
                        Count & 25 & 25 \\
                        \midrule
                        Number of NDs & 5 & 5 \\
                        \midrule
                        Min; Max & 0.123; 123 & 0.123; 123 \\
                        \midrule
                        Mean & 12.3 & 12.3 \\
                        %%
                        (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                        \midrule
                        Standard Deviation & 4.56 & 4.56 \\
                        \midrule
                        Log. Mean & 12.3 & 12.3 \\
                        %%
                        (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                        \midrule
                        Log. Standard Deviation & 4.56 & 4.56 \\
                        \midrule
                        Geo. Mean & 12.3 & 12.3 \\
                        %%
                        (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                        \midrule
                        Coeff. of Variation & 5.61 & 5.61 \\
                        \midrule
                        Skewness & 6.12 & 6.12 \\
                        \midrule
                        Median & 1.23 & 1.23 \\
                        %%
                        (95\% confidence interval) & (0.235; 2.23) & (0.235; 2.23) \\
                        \midrule
                        Quartiles & 0.612; 2.35 & 0.612; 2.35 \\
                        \toprule
                        Number of Pairs & \multicolumn{2}{c} {22} \\
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
                        Count & 25 & 25 \\
                        \midrule
                        Number of NDs & 5 & 5 \\
                        \midrule
                        Min; Max & 0.123; 123 & 0.123; 123 \\
                        \midrule
                        Mean & 12.3 & 12.3 \\
                        %%
                        (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                        \midrule
                        Standard Deviation & 4.56 & 4.56 \\
                        \midrule
                        Log. Mean & 12.3 & 12.3 \\
                        %%
                        (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                        \midrule
                        Log. Standard Deviation & 4.56 & 4.56 \\
                        \midrule
                        Geo. Mean & 12.3 & 12.3 \\
                        %%
                        (95\% confidence interval) & (11.3; 13.3) & (11.3; 13.3) \\
                        \midrule
                        Coeff. of Variation & 5.61 & 5.61 \\
                        \midrule
                        Skewness & 6.12 & 6.12 \\
                        \midrule
                        Median & 1.23 & 1.23 \\
                        %%
                        (95\% confidence interval) & (0.235; 2.23) & (0.235; 2.23) \\
                        \midrule
                        Quartiles & 0.612; 2.35 & 0.612; 2.35 \\
                        \toprule
                        Number of Pairs & \multicolumn{2}{c} {22} \\
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
                        Count & NA & 25 \\
                        \midrule
                        Number of NDs & NA & 5 \\
                        \midrule
                        Min; Max & NA & 0.123; 123 \\
                        \midrule
                        Mean & NA & 12.3 \\
                        %%
                        (95\% confidence interval) & NA & (11.3; 13.3) \\
                        \midrule
                        Standard Deviation & NA & 4.56 \\
                        \midrule
                        Log. Mean & NA & 12.3 \\
                        %%
                        (95\% confidence interval) & NA & (11.3; 13.3) \\
                        \midrule
                        Log. Standard Deviation & NA & 4.56 \\
                        \midrule
                        Geo. Mean & NA & 12.3 \\
                        %%
                        (95\% confidence interval) & NA & (11.3; 13.3) \\
                        \midrule
                        Coeff. of Variation & NA & 5.61 \\
                        \midrule
                        Skewness & NA & 6.12 \\
                        \midrule
                        Median & NA & 1.23 \\
                        %%
                        (95\% confidence interval) & NA & (0.235; 2.23) \\
                        \midrule
                        Quartiles & NA & 0.612; 2.35 \\
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
    """)
    return content
