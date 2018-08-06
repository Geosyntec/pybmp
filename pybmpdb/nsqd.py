from pathlib import Path

import pandas
from engarde import checks

import wqio


__all__ = ['NSQData', 'load_data']


class NSQData(object):
    """ Class representing the National Stormwater Quality Dataset.

    Parameters
    ----------
    datapath : string, optional.
        Optional path the file to read. If not provided, the bundeled
        data will be used.

    """

    def __init__(self, datapath=None):
        # read my heavily modified version of the database
        self.datapath = Path(datapath or wqio.download('nsqd'))
        self._data = None

    @property
    def data(self):
        if self._data is None:
            self._data = pandas.read_csv(self.datapath)
        return self._data

    def to_DataCollection(self, *args, **kwargs):
        return wqio.DataCollection(self.data, *args, **kwargs)


def load_data(datapath=None, as_dataframe=False, **kwargs):
    nsqd = NSQData(datapath=datapath)
    if as_dataframe:
        return nsqd.data
    return nsqd.to_DataCollection(**kwargs)
