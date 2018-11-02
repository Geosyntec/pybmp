import sys
import os
import tempfile
import zipfile
from io import StringIO
from pkg_resources import resource_filename
from urllib import request
from pathlib import Path

from unittest.mock import patch
import pytest
import numpy.testing as nptest
import pandas.util.testing as pdtest

import numpy
import pandas

from pybmpdb import bmpdb
import wqio


def get_data_file(filename):
    return resource_filename("pybmpdb.tests._data", filename)


@pytest.fixture
def df_for_quals():
    df = pandas.DataFrame([
        {'res': 1, 'DL': 2, 'qual': 'U'},
        {'res': 1, 'DL': 2, 'qual': 'UK'},
        {'res': 1, 'DL': 2, 'qual': 'UA'},
        {'res': 1, 'DL': 2, 'qual': 'UC'},
        {'res': 1, 'DL': 2, 'qual': 'K'},
        {'res': 5., 'DL': 15., 'qual': 'UJ'},
        {'res': 5., 'DL': 10., 'qual': 'UJ'},
        {'res': 10., 'DL': 5., 'qual': 'UJ'},
        {'res': 10., 'DL': 10., 'qual': 'UJ'},
        {'res': 5., 'DL': 5., 'qual': 'junk'},
    ])
    return df


def test__handle_ND_factors(df_for_quals):
    expected = numpy.array([2, 2, 2, 2, 2, 3, 2, 1, 1, 1])
    result = bmpdb._handle_ND_factors(df_for_quals)
    nptest.assert_array_equal(result, expected)


def test__handle_ND_qualifiers(df_for_quals):
    result = bmpdb._handle_ND_qualifiers(df_for_quals)
    expected = numpy.array(['ND', 'ND', 'ND', 'ND', 'ND', 'ND', 'ND', '=', 'ND', '='])
    nptest.assert_array_equal(result, expected)


def test__process_screening():
    df = pandas.DataFrame({
        'screen': ['Yes', 'INC', 'No', 'eXC', 'junk']
    })
    expected = numpy.array(['yes', 'yes', 'no', 'no', 'invalid'])
    result = bmpdb._process_screening(df, 'screen')
    nptest.assert_array_equal(result, expected)


def test__process_sampletype():
    df = pandas.DataFrame({
        'sampletype': ['SRL GraB asdf', 'SeL cOMPositE df', 'jeL LSDR as']
    })
    expected = numpy.array(['grab', 'composite', 'unknown'])
    result = bmpdb._process_sampletype(df, 'sampletype')
    nptest.assert_array_equal(result, expected)


def test__check_levelnames():
    bmpdb._check_levelnames(['epazone', 'category'])

    with pytest.raises(ValueError):
        bmpdb._check_levelnames(['site', 'junk'])


@patch.object(pandas, 'read_csv')
def test_load_data(read_csv):
    bmpdb.load_data('bmp.csv')
    read_csv.assert_called_once_with(Path('bmp.csv'), parse_dates=['sampledate'], encoding='utf-8')


@pytest.mark.skipif(True, reason='test not ready')
def test_clean_raw_data():
    pass


def test_transform_parameters():
    index_cols = ['storm', 'param', 'units']
    df = pandas.DataFrame({
        'storm': [1, 1, 2, 2, 3, 3],
        'param': list('ABABAB'),
        'units': ['mg/L'] * 6,
        'res': [1, 2, 3, 4, 5, 6],
        'qual': ['<', '='] * 3,
    }).set_index(index_cols)

    expected = pandas.DataFrame({
        'storm': [1, 1, 2, 2, 3, 3, 1, 2, 3],
        'param': list('ABABABCCC'),
        'units': (['mg/L'] * 6) + (['ug/L'] * 3),
        'res': [1, 2, 3, 4, 5, 6, 3000, 7000, 11000],
        'qual': (['<', '='] * 3) + (['='] * 3),
    }).set_index(index_cols)

    old_params = ['A', 'B']
    new_param = 'C'
    result = bmpdb.transform_parameters(
        df, old_params, new_param, 'ug/L',
        lambda x: 1000 * x['res'].sum(axis=1),
        lambda x: x[('qual', 'B')],
        paramlevel='param'
    )
    pdtest.assert_frame_equal(result, expected)


@pytest.mark.parametrize(('fxn', 'args', 'index_cols', 'infilename', 'outfilename'), [
    (bmpdb._pick_best_station, [], ['site', 'bmp', 'storm', 'parameter', 'station'],
     'test_pick_station_input.csv', 'test_pick_station_output.csv'),
    (bmpdb._pick_best_sampletype, [], ['site', 'bmp', 'storm', 'parameter', 'station', 'sampletype'],
     'test_pick_sampletype_input.csv', 'test_pick_sampletype_output.csv'),
    (bmpdb._filter_by_storm_count, [6], ['category', 'site', 'bmp', 'storm', 'parameter', 'station'],
     'test_filter_bmp-storm_counts_input.csv', 'test_filter_storm_counts_output.csv'),
    (bmpdb._filter_by_BMP_count, [4], ['category', 'site', 'bmp', 'parameter', 'station'],
     'test_filter_bmp-storm_counts_input.csv', 'test_filter_bmp_counts_output.csv',),
])
def test_summary_filter_functions(fxn, args, index_cols, infilename, outfilename):
    input_df = pandas.read_csv(get_data_file(infilename), index_col=index_cols)
    expected_df = pandas.read_csv(get_data_file(outfilename), index_col=index_cols).sort_index()

    test_df = fxn(input_df, *args).sort_index()
    pdtest.assert_frame_equal(expected_df.reset_index(), test_df.reset_index())


@pytest.mark.parametrize('doit', [True, False])
@pytest.mark.parametrize(('fxn', 'index_cols', 'infilename', 'outfilename'), [
    (bmpdb._maybe_filter_onesided_BMPs, ['category', 'site', 'bmp', 'storm', 'parameter', 'station'],
     'test_filter_onesidedbmps_input.csv', 'test_filter_onesidedbmps_output.csv'),
    (bmpdb._maybe_combine_nox, ['bmp', 'category', 'storm', 'units', 'parameter'],
     'test_WBRP_NOx_input.csv', 'test_NOx_output.csv'),
    (bmpdb._maybe_combine_WB_RP, ['bmp', 'category', 'storm', 'units', 'parameter'],
     'test_WBRP_NOx_input.csv', 'test_WBRP_output.csv'),
    (bmpdb._maybe_fix_PFCs, ['bmp', 'category', 'bmptype', 'storm', 'parameter'],
     'test_PFCs_input.csv', 'test_PFCs_output.csv'),
    (bmpdb._maybe_remove_grabs, ['bmp', 'category', 'sampletype', 'storm'],
     'test_grabsample_input.csv', 'test_grabsample_output.csv')
])
def test__maybe_filter_functions(fxn, doit, index_cols, infilename, outfilename):
    input_df = pandas.read_csv(get_data_file(infilename), index_col=index_cols)
    result = fxn(input_df, doit).sort_index()
    if doit:
        expected = pandas.read_csv(get_data_file(outfilename), index_col=index_cols).sort_index()
    else:
        expected = input_df.copy().sort_index()
    pdtest.assert_frame_equal(result, expected)


def test__pick_non_null():
    df = pandas.DataFrame({
        ('res', 'this'): [1.0, numpy.nan, 2.0, numpy.nan],
        ('res', 'that'): [numpy.nan, numpy.nan, 9.0, 3.0]
    })
    expected = numpy.array([1.0, numpy.nan, 2.0, 3.0])
    result = bmpdb._pick_non_null(df, 'res', 'this', 'that')
    nptest.assert_array_equal(result, expected)


def test_paired_qual():
    df = pandas.DataFrame({
        'in_qual': ['=', '=', 'ND', 'ND'],
        'out_qual': ['=', 'ND', '=', 'ND']
    })
    expected = ['Pair', 'Effluent ND', 'Influent ND', 'Both ND']
    result = bmpdb.paired_qual(df, 'in_qual', 'out_qual')
    nptest.assert_array_equal(result, expected)
