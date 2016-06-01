from .dataAccess import Database, Table
from .summary import (
    CategoricalSummary,
    DatasetSummary,
    getSummaryData,
    setMPLStyle,
    parameterBoxplots,
    bmpStatSummary
)


def style_notebook(filepath=None):
    from IPython.core.display import HTML
    if filepath is None:
        filepath = "../styles/ipynb.css"
    styles = open(filepath, "r").read()
    return HTML(styles)
