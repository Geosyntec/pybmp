from pathlib import Path

import pandas

import wqio


def load_data(datapath=None, as_dataframe=False, **dc_kwargs):
    """
    Parameters
    ----------
    datapath : str or pathlib.Path, optional
        Path to the raw data CSV. If not provided, the latest data will be
        downloaded.
    as_dataframe : bool (default = False)
        When False, a wqio.DataCollection is returned

    Additional Parameters
    ---------------------
    Any additional keword arguments will be passed to wqio.DataCollection.

    Returns
    -------
    nsqd : pandas.DataFrame or wqio.DataCollection

    """
    datapath = Path(datapath or wqio.download("nsqd"))
    nsqd = pandas.read_csv(datapath, encoding="utf-8")
    if as_dataframe:
        return nsqd
    return wqio.DataCollection(nsqd, **dc_kwargs)
