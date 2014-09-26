from .dataAccess import Database, Table, defaultFilter
from .summary import CategoricalSummary, DatasetSummary

from ..core.features import (
    Location,
    Dataset,
    DataCollection,
    Parameter,
    DrainageArea
)

from ..core.events import (
    Storm,
    CompositeSample,
    GrabSample,
    defineStorms
)

from ..testing import NoseWrapper
test = NoseWrapper().test

def style_notebook(filepath=None):
    from IPython.core.display import HTML
    if filepath is None:
        filepath = "../styles/ipynb.css"
    styles = open(filepath, "r").read()
    return HTML(styles)

