from pkg_resources import resource_filename
from pathlib import Path

import numpy as np
import pandas

import pytest
import numpy.testing as nptest
from unittest.mock import patch

import pybmpdb
from pybmpdb import nsqd
import wqio


@pytest.mark.parametrize('as_df', [True, False])
@patch.object(wqio, 'DataCollection')
@patch.object(wqio, 'download', return_value=Path('./data/nsqd.csv'))
@patch.object(pandas, 'read_csv', return_value='NSQD_DataFrame')
def test_load_data(read_csv, download, dc, as_df):
    nsqd.load_data()
    download.assert_called_once_with('nsqd')
    read_csv.assert_called_once_with(Path('./data/nsqd.csv'), encoding='utf-8')
    if not as_df:
        dc.assert_called_once_with('NSQD_DataFrame')
