from pathlib import Path

import pandas
from engarde import checks

import wqio


def load_data(datapath=None, as_dataframe=False, *args, **kwargs):
    datapath = Path(datapath or wqio.download('nsqd'))
    nsqd = pandas.read_csv(datapath, encoding='utf-8')
    if as_dataframe:
        return nsqd
    return wqio.DataCollection(nsqd, *args, **kwargs)
