import os
import sys
import glob
from textwrap import dedent
from io import StringIO
from pkg_resources import resource_filename
from tempfile import TemporaryDirectory

from unittest import mock
import pytest
import pandas.util.testing as pdtest
from wqio.tests import helpers

import numpy
import pandas

from wqio.utils import numutils

from pybmpdb import utils


def test__sig_figs_helper():
    x = 1.2
    assert utils._sig_figs(x) == numutils.sigFigs(x, 3, tex=True)


def test_refresh_index():
    idx = pandas.MultiIndex.from_product([list('ABC'), list('ABC')], names=['A', 'B'])
    df = pandas.DataFrame(
        index=idx,
        columns=list('abc'),
        data=numpy.arange(27).reshape(9, 3)
    )
    pdtest.assert_frame_equal(df, utils.refresh_index(df))

    dfr = df.reset_index()
    assert dfr is utils.refresh_index(dfr)


def test_get_level_position():
    idx = pandas.MultiIndex.from_product([
        list('ABC'), ['cat', 'dog', 'fox', 'deer']
    ], names=['forest', 'animal'])
    df = pandas.DataFrame(index=idx, columns=list('abc'))

    assert utils.get_level_position(df, 'animal') == 1


def test_sanitizeTex():
    inputstring = r""" \
    \$x\_\{4\}\textasciicircum\{2\} \textbackslashtimes \% ug/L$ \textbackslash \\
    """
    desiredstring = r""" \
    $x_{4}^{2} \times \% \si[per-mode=symbol]{\micro\gram\per\liter}$  \tabularnewline
    """

    assert utils.sanitizeTex(inputstring) == desiredstring


@pytest.mark.skipif(True, reason="WIP")
def test_makeBoxplotLegend():
    utils.makeBoxplotLegend(helpers.test_data_path('bplegendtest'))


@pytest.fixture
def inputpath():
    return StringIO("Date,A,B,C,D\nX,1,2,3,4\nY,5,6,7,8\nZ,9,0,1,2")


def test_csvToTex(inputpath):
    result = utils.csvToTex(inputpath)
    knownfile = resource_filename("pybmpdb.tests._data", 'testtable_toTex_Known.tex')
    with open(knownfile, 'r') as known:
        expected = known.read()
        assert result == expected


def test_csvToXlsx(inputpath):
    with mock.patch.object(pandas.DataFrame, 'to_excel') as toxl:
        outputpath = resource_filename("pybmpdb.tests._data", 'testtable_toXL.xlsx')
        utils.csvToXlsx(inputpath, outputpath)
        toxl.assert_called_once_with(outputpath, float_format=None,
                                     na_rep='--', index=False)


def test_makeTexTable_normal():
    known = dedent(r"""
        \begin{table}[h!]
            \rowcolors{1}{CVCWhite}{CVCLightGrey}
            \caption{test caption}
            \centering
            \input{fake.tex}
        \end{table}


    """)

    test = utils.makeTexTable('fake.tex', 'test caption')
    assert known == test


def test_makeTexTable_allOptions():
    known = dedent(r"""
    \begin{sidewaystable}[bt]
        \rowcolors{1}{CVCWhite}{CVCLightGrey}
        \caption{test caption}
        \centering
        \input{fake.tex}
    \end{sidewaystable}
    test footnote
    \clearpage
    """)
    test = utils.makeTexTable('fake.tex', 'test caption', sideways=True,
                              footnotetext='test footnote', clearpage=True,
                              pos='bt')
    assert known == test


@pytest.fixture
def long_landscape_tables():
    tables = {
        None: dedent(r"""
            \begin{landscape}
                \centering
                \rowcolors{1}{CVCWhite}{CVCLightGrey}
                \begin{longtable}{lcc}
                    \caption{test caption} \label{label} \\
                    \toprule
                    \multicolumn{1}{l}{W} &
                    \multicolumn{1}{p{16mm}}{X} &
                    \multicolumn{1}{p{16mm}}{Y} \\
                    \toprule
                    \endfirsthead

                    \multicolumn{3}{c}
                    {{\bfseries \tablename\ \thetable{} -- continued from previous page}} \\
                    \toprule
                    \multicolumn{1}{l}{W} &
                    \multicolumn{1}{p{16mm}}{X} &
                    \multicolumn{1}{p{16mm}}{Y} \\
                    \toprule
                    \endhead

                    \toprule
                    \rowcolor{CVCWhite}
                    \multicolumn{3}{r}{{Continued on next page...}} \\
                    \bottomrule
                    \endfoot

                    \bottomrule
                    \endlastfoot

             0.844 & 0.700 & -1.35 \\
            -0.221 &  1.48 & -1.19 \\

                \end{longtable}
            \end{landscape}

            \clearpage
        """),
        'test note': dedent(r"""
            \begin{landscape}
                \centering
                \rowcolors{1}{CVCWhite}{CVCLightGrey}
                \begin{longtable}{lcc}
                    \caption{test caption} \label{label} \\
                    \toprule
                    \multicolumn{1}{l}{W} &
                    \multicolumn{1}{p{16mm}}{X} &
                    \multicolumn{1}{p{16mm}}{Y} \\
                    \toprule
                    \endfirsthead

                    \multicolumn{3}{c}
                    {{\bfseries \tablename\ \thetable{} -- continued from previous page}} \\
                    \toprule
                    \multicolumn{1}{l}{W} &
                    \multicolumn{1}{p{16mm}}{X} &
                    \multicolumn{1}{p{16mm}}{Y} \\
                    \toprule
                    \endhead

                    \toprule
                    \rowcolor{CVCWhite}
                    \multicolumn{3}{r}{{Continued on next page...}} \\
                    \bottomrule
                    \endfoot

                    \bottomrule
                    \endlastfoot

             0.844 & 0.700 & -1.35 \\
            -0.221 &  1.48 & -1.19 \\

                \end{longtable}
            \end{landscape}
            test note
            \clearpage
        """)
    }
    return tables


@pytest.mark.parametrize('footnote', ['test note', None])
def test_makeLongLandscapeTexTable(footnote, long_landscape_tables):
    dfdict = {
        'W': {
            'a': 0.84386963791251501,
            'b': -0.22109837444207142,
        },
        'X': {
            'a': 0.70049867715201963,
            'b': 1.4764939161054218,
        },
        'Y': {
            'a': -1.3477794473987552,
            'b': -1.1939220296611821,
        },
    }
    df = pandas.DataFrame.from_dict(dfdict)
    result = utils.makeLongLandscapeTexTable(df, 'test caption', 'label',
                                             footnotetext=footnote)
    expected = long_landscape_tables[footnote]
    helpers.assert_bigstring_equal(result, expected)


def test_makeTexFigure():
    known = dedent(r"""
    \begin{figure}[hb]   % FIGURE
        \centering
        \includegraphics[scale=1.00]{fake.pdf}
        \caption{test caption}
    \end{figure}         % FIGURE
    \clearpage
    """)
    test = utils.makeTexFigure('fake.pdf', 'test caption')
    assert known == test


def test_processFilename():
    startname = 'This-is a, very+ &dumb$_{test/name}'
    endname = 'This-isaverydumbtestname'
    assert endname == utils.processFilename(startname)


@pytest.fixture
def deep_dir(latex_content):
    with TemporaryDirectory() as td:
        dd = os.path.join(td, 'test1', 'test2', 'test3')
        os.makedirs(dd)
        with open(os.path.join(dd, 'f.tex'), 'w') as f:
            f.write(latex_content)
        yield dd


@pytest.fixture
def latex_content():
    return dedent(r"""
        \documentclass[12pt]{article}
        \usepackage{lingmacros}
        \usepackage{tree-dvips}
        \begin{document}

        \section*{Notes for My Paper}

        Don't forget to include examples of topicalization.
        They look like this:

        {\small
        \enumsentence{Topicalization from sentential subject:\\
        \shortex{7}{a John$_i$ [a & kltukl & [el &
            {\bf l-}oltoir & er & ngii$_i$ & a Mary]]}
        { & {\bf R-}clear & {\sc comp} &
            {\bf IR}.{\sc 3s}-love   & P & him & }
        {John, (it's) clear that Mary loves (him).}}
        }

        \subsection*{How to handle topicalization}

        I'll just assume a tree structure like (\ex{1}).

        {\small
        \enumsentence{Structure of A$'$ Projections:\\ [2ex]
        \begin{tabular}[t]{cccc}
            & \node{i}{CP}\\ [2ex]
            \node{ii}{Spec} &   &\node{iii}{C$'$}\\ [2ex]
                &\node{iv}{C} & & \node{v}{SAgrP}
        \end{tabular}
        \nodeconnect{i}{ii}
        \nodeconnect{i}{iii}
        \nodeconnect{iii}{iv}
        \nodeconnect{iii}{v}
        }
        }

        \subsection*{Mood}

        Mood changes when there is a topic, as well as when
        there is WH-movement.  \emph{Irrealis} is the mood when
        there is a non-subject topic or WH-phrase in Comp.
        \emph{Realis} is the mood when there is a subject topic
        or WH-phrase.

        \end{document}
    """)


def test_LaTeXDirectory_folder_only(deep_dir):
    origdir = os.getcwd()
    with utils.LaTeXDirectory(deep_dir):
        assert os.getcwd() == deep_dir

    assert os.getcwd() == origdir


def test_LaTeXDirectory_file(deep_dir):
    origdir = os.getcwd()
    deep_file = os.path.join(deep_dir, 'f.tex')
    with utils.LaTeXDirectory(deep_file):
        assert os.getcwd() == deep_dir

    assert os.getcwd() == origdir


@pytest.mark.skipif(helpers.checkdep_tex() is None, reason='No LaTeX')
def test_compile_smoke(deep_dir, latex_content):
    deep_file = os.path.join(deep_dir, 'f.tex')

    with utils.LaTeXDirectory(deep_file) as latex:
        latex.compile(deep_file)
