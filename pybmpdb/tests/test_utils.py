import os
import sys
import glob
from textwrap import dedent
from io import StringIO

from unittest import mock
import pytest
from wqio.tests import helpers

import pandas

from wqio.utils import numutils

from pybmpdb import utils


def test__sig_figs_helper():
    x = 1.2
    assert utils._sig_figs(x) == numutils.sigFigs(x, 3, tex=True)


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
    knownfile = 'testtable_toTex_Known.tex'
    with open(helpers.test_data_path(knownfile), 'r') as known:
        expected = known.read()
        assert result == expected


def test_csvToXlsx(inputpath):
    with mock.patch.object(pandas.DataFrame, 'to_excel') as toxl:
        outputpath = helpers.test_data_path('testtable_toXL.xlsx')
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


class Test_makeLongLandscapeTexTable(object):
    def setup(self):
        self.maxDiff = None
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
        self.df = pandas.DataFrame.from_dict(dfdict)
        self.known_nofootnote = dedent(r"""
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
        """)

        self.known_withfootnote = dedent(r"""
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

    def test_makeLongLandscapeTexTable_noFootnote(self):
        test = utils.makeLongLandscapeTexTable(self.df, 'test caption', 'label')
        assert self.known_nofootnote == test

    def test_makeLongLandscapeTexTable_Footnote(self):
        test = utils.makeLongLandscapeTexTable(self.df, 'test caption', 'label', 'test note')
        assert self.known_withfootnote == test


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


class Test_LaTeXDirectory(object):
    def setup(self):
        self.origdir = os.getcwd()
        self.deepdir = os.path.join(os.getcwd(), 'test1', 'test2', 'test3')
        self.deepfile = os.path.join(self.deepdir, 'f.tex')
        tex_content = dedent(r"""
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

        if os.path.exists(self.deepdir):
            self.teardown()

        os.makedirs(self.deepdir)
        with open(self.deepfile, 'w') as dfile:
            dfile.write(tex_content)

    def teardown(self):
        allfiles = glob.glob(os.path.join(self.deepdir, "f.*"))
        for af in allfiles:
            os.remove(af)
        os.removedirs(self.deepdir)

    def test_dir(self):
        assert os.getcwd() == self.origdir
        with utils.LaTeXDirectory(self.deepdir):
            assert os.getcwd() == self.deepdir

        assert os.getcwd() == self.origdir

    def test_file(self):
        assert os.getcwd() == self.origdir
        with utils.LaTeXDirectory(self.deepfile):
            assert os.getcwd() == self.deepdir

        assert os.getcwd() == self.origdir

    @pytest.mark.skipif(helpers.checkdep_tex() is None, reason='No LaTeX')
    def test_compile_smoke(self):
        with utils.LaTeXDirectory(self.deepfile) as latex:
            latex.compile(self.deepfile)
