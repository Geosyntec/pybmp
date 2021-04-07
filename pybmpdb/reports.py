import os
from io import BytesIO
from pathlib import Path
from datetime import datetime
from functools import partial
from math import ceil

import numpy
import pandas

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Image,
    Table,
    PageBreak,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from matplotlib import pyplot, ticker, figure
import seaborn

from pybmpdb import summary
from wqio.utils import sigFigs
from wqio import validate, viz

TODAY = datetime.today().strftime("%Y-%m-%d")
STYLES = getSampleStyleSheet()
BASEURL = "https://dot-portal-app.azurewebsites.net/api"

_FOOTERSTYLE = STYLES["Normal"].clone("footer")
_FOOTERSTYLE.fontName = "Helvetica"
_FOOTERSTYLE.fontSize = 8
_FOOTERSTYLE.alignment = TA_CENTER

_HEADERSTYLE = STYLES["Heading1"].clone("header")
_HEADERSTYLE.fontName = "Helvetica-Bold"
_HEADERSTYLE.fontSize = 16
_HEADERSTYLE.alignment = TA_RIGHT

_pal = seaborn.color_palette("deep")
BLUE = _pal[0]
GREEN = _pal[2]


def _get_units(df, col):
    if not df.empty:
        all_units = df[col].unique().tolist()
        if not len(all_units) == 1:
            raise ValueError(f"lots of {col} ({all_units})")
        else:
            return all_units[0]


def precip_flow_plot(precip, volume, punit, vunit) -> figure.Figure:
    # fig = pyplot.figure(figsize=(7, 5), dpi=300)
    # pax = fig.add_axes([0.05, 0.65, 0.90, 0.30])
    # vax = fig.add_axes([0.05, 0.05, 0.90, 0.60], sharex=pax)
    if not punit:
        punit = "No Units"
    if not vunit:
        vunit = "No Units"

    fig, (pax, vax) = pyplot.subplots(
        nrows=2,
        ncols=1,
        figsize=(7.5, 4.5),
        dpi=300,
        sharex=True,
        gridspec_kw=dict(height_ratios=[1, 2.5], hspace=0.00),
    )

    pax.yaxis.set_label_position("right")
    pax.yaxis.tick_right()
    pax.invert_yaxis()
    pax.xaxis.tick_top()
    pax.set_ylabel(f"Precip. ({punit})", rotation=270, va="top", labelpad=10)

    vax.set_ylabel(f"Flow Volume ({vunit})")

    if not precip.empty:
        pax.bar("date", "PrecipDepth_Value", color="0.425", data=precip)
    else:
        pax.annotate(
            "No Data to show",
            (0.5, 0.5),
            (0, 0),
            xycoords="axes fraction",
            textcoords="offset points",
            ha="center",
            va="center",
        )
        pax.yaxis.set_major_formatter(ticker.NullFormatter())
        pax.set_ylim(top=0)

    if not volume.empty:
        vax.plot(
            "date",
            "Volume_Total",
            marker="d",
            linestyle="none",
            label="Inflow",
            color=BLUE,
            data=volume.loc[volume["MSType"] == "Inflow"],
        )

        vax.plot(
            "date",
            "Volume_Total",
            marker="s",
            linestyle="none",
            label="Outflow",
            color=GREEN,
            data=volume.loc[volume["MSType"] == "Outflow"],
        )
        vax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f"{int(x):,d}"))
        vax.legend(loc="best")
        vax.set_ylim(bottom=0)
    else:
        vax.annotate(
            "No Data to show",
            (0.5, 0.5),
            (0, 0),
            xycoords="axes fraction",
            textcoords="offset points",
            ha="center",
            va="center",
        )
        vax.yaxis.set_major_formatter(ticker.NullFormatter())

    if precip.empty and volume.empty:
        pax.xaxis.set_major_formatter(ticker.NullFormatter())

    seaborn.despine(ax=pax, left=False, right=False, top=False, bottom=True)
    seaborn.despine(ax=vax, left=False, right=False, top=True, bottom=False)

    viz.rotateTickLabels(pax, -25, "x")
    viz.rotateTickLabels(vax, 25, "x")

    fig.tight_layout()
    return fig


def _table_float(x):
    if pandas.isnull(x):
        return "N/A"
    return sigFigs(x, 3, tex=False, pval=False, forceint=False)


def _table_int(x):
    if pandas.isnull(x):
        return "N/A"
    return "{:,d}".format(int(x))


def _table_string(x):
    if pandas.isnull(x):
        return "N/A"
    return str(x)


def _table_date(d):
    if pandas.isnull(d):
        return "N/A"
    else:
        return pandas.to_datetime(d).strftime("%Y-%m-%d")


def _table_cost(x):
    if pandas.isnull(x):
        return "N/A"
    else:
        return "${:,d}".format(int(x))


def _table_paragraph(text):
    styleN = STYLES["BodyText"]
    styleN.alignment = TA_LEFT
    styleN.leading = 9
    return Paragraph(f"{text}", styleN)


def _design_param_fmt(x):
    if pandas.isnull(x):
        return "N/A"
    elif numpy.isreal(x):
        if int(x) == x:
            return _table_int(x)
        else:
            return _table_float(x)
    else:
        return _table_string(x)


def parse_dates(df):
    if not df.empty:
        return df.assign(date=lambda df: pandas.to_datetime(df["DateStart"]))
    return df


class NumberedCanvasLandscape(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """add page info to each page (page x of y)"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.setFont(_FOOTERSTYLE.fontName, _FOOTERSTYLE.fontSize)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        # Change the position of this to wherever you want the page number to be
        self.drawRightString(10.5 * inch, 0.35 * inch, f"Page {self._pageNumber} of {page_count}")
        # self.drawCentredString(6.5 * inch, 0.5 * inch, "Test centred")
        self.drawString(0.5 * inch, 0.35 * inch, f"Generated: {TODAY}")


class NumberedCanvasPortrait(NumberedCanvasLandscape):
    def draw_page_number(self, page_count):
        # Change the position of this to wherever you want the page number to be
        self.drawRightString(8 * inch, 0.35 * inch, f"Page {self._pageNumber} of {page_count}")
        # self.drawCentredString(6.5 * inch, 0.5 * inch, "Test centred")
        self.drawString(0.5 * inch, 0.35 * inch, f"Generated: {TODAY}")


def get_api_data(endpoint):
    return pandas.read_json(BASEURL + endpoint, dtype={"PDFID": str}).sort_values(by=["PDFID"])


def get_sites_info():
    return pandas.read_json(BASEURL + "/DOTSites", dtype={"PDFID": str}).sort_values(by=["PDFID"])


def get_climate_info():
    return pandas.read_json(BASEURL + "/vClimateRecords", dtype={"PDFID": str}).sort_values(by=["PDFID"])


def get_hydro_info(pdfid, all_climate, all_precip, all_flow):

    # dtype = {"PDFID": str}
    # flow = pandas.read_json(BASEURL + f"/vFlowRecords?pdf_id={pdfid}", dtype=dtype).pipe(parse_dates)
    # precip = pandas.read_json(BASEURL + f"/vPrecipRecords?pdf_id={pdfid}", dtype=dtype).pipe(parse_dates)
    selector = lambda df: df["PDFID"] == pdfid
    c = all_climate.loc[selector]
    p = all_precip.loc[selector]
    f = all_flow.loc[selector]
    assert c.shape[0] == 1

    return c.iloc[0], p, f


def get_bmp_info(pdfid, sites):
    dtype = {"PDFID": str}

    # bmp design meta data
    meta = (
        pandas.read_json(
            BASEURL + f"/vBMPDesignMetas?pdf_id={pdfid}",
            dtype=dtype,
        )
        .merge(sites, on="PDFID", suffixes=("", "_ds"), how="left")
        .loc[0, lambda df: df.columns.map(lambda c: not c.endswith("_ds"))]
    )

    # bmp design elements
    elements = pandas.read_json(BASEURL + f"/vBMPDesignElements?pdf_id={pdfid}", dtype=dtype)

    if elements.shape[0] == 0:
        elements = None

    title = meta["BMPName"]
    return meta, elements, title


def _make_table_from_df(df, headers, style, datecols=None, dateformat=None, banded=True, col_widths=None, title=None):
    """Helper function to make a reportlab table from a dataframe

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe containing the data to be tabulated
    headers : list of str
        Column labels for the rendered table
    style : list of tuples
        List of reportlab-compatible table style tuples
    banded : bool (default = True)
        When true, every other row in the table will have a light grey
        background.
    title : str, optional
        If provided, inserts a single-valued row above the column headers

    """
    if datecols:
        if not dateformat:
            dateformat = "%Y-%m-%d"
        df = df.assign(**{dc: df[dc].dt.strftime(dateformat) for dc in datecols})

    if banded:
        bands = [("BACKGROUND", (0, row), (-1, row), colors.lightgrey) for row in range(1, df.shape[0] + 1, 2)]
        style = [*style, *bands]

    _data = df.astype(str).applymap(_table_paragraph).values.tolist()
    _headers = [_table_paragraph(h) for h in headers]
    table_values = [_headers, *_data]
    if title:
        _blanks = ["" for _ in range(len(headers) - 1)]
        _title = [title, *_blanks]
        table_values = [_title, *table_values]

    table = Table(table_values, repeatRows=1, repeatCols=1, style=style, colWidths=col_widths)
    return table


def two_tables_next_to_eachother(leftdata, rightdata, leftheader, rightheader, col_widths, styled=True):
    # headers = ("Watershed Characteristics", "", "Transportation Characteristics", "")
    # col_widths = [table_width / len(headers)] * len(headers)
    data = pandas.concat([leftdata, rightdata], axis="columns").fillna("")
    headers = (leftheader, "", rightheader, "")
    if styled:
        style = [
            ("SPAN", (0, 0), (1, 0)),  # header row, merge columns 1 and 2
            ("SPAN", (2, 0), (3, 0)),  # header row, merge columns 3 and 4
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # header row is bold
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),  # watershed header col is bold
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),  # DOT header col is bold
            ("FONTNAME", (1, 1), (1, -1), "Helvetica"),  # watershed data cells are not bold
            ("FONTNAME", (3, 1), (3, -1), "Helvetica"),  # DOT data cells are not bold
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),  # header row is centered
            ("ALIGN", (0, 1), (0, -1), "LEFT"),  # header col is horizontally left-aligned
            ("ALIGN", (1, 1), (-1, -1), "LEFT"),  # all other cells are horizontally centered
            ("VALIGN", (0, 0), (-1, -1), "TOP"),  # all cells are vertically centered
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),  # line below column headers
            ("LINEAFTER", (1, 0), (1, -1), 1, colors.black),  # line btwn the two subtables
        ]
    else:
        style = [
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),  # loc header col is bold
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),  # bmp header col is bold
            ("FONTNAME", (1, 1), (1, -1), "Helvetica"),  # watershed data cells are not bold
            ("FONTNAME", (3, 1), (3, -1), "Helvetica"),  # DOT data cells are not bold
            ("ALIGN", (0, 0), (-2, -1), "LEFT"),  # first three cols are left-aligned
            ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),  # last col is right-aligned
            ("VALIGN", (0, 0), (-1, -1), "TOP"),  # all  cells are vertically centered
        ]
    table = _make_table_from_df(data, headers, style, banded=False, col_widths=col_widths)
    return table


def normal_table(data, title, col_widths):
    style = [
        ("SPAN", (0, 0), (-1, 0)),  # header row, merge all columns 1 and 2
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # title row is bold
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        # ("BACKGROUND", (0, 1), (-1, 1), colors.lightblue),
        # ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),  # header row is bold
        # ("FONTNAME", (0, 2), (0, -1), "Helvetica-Bold"),  # header col is bold
        # ("FONTNAME", (1, 2), (1, -1), "Helvetica"),  # watershed data cells are not bold
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),  # header row is centered
        ("ALIGN", (0, 1), (0, -1), "LEFT"),  # header col is horizontally left-aligned
        ("ALIGN", (1, 1), (-1, -1), "LEFT"),  # all other cells are left-aligned
        ("VALIGN", (0, 0), (-1, -1), "TOP"),  # all  cells are vertically centered
        # ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),  # line below column title
        ("LINEBELOW", (0, 1), (-1, 1), 1, colors.black),  # line below column headers
    ]
    table = _make_table_from_df(data, data.columns.tolist(), style, banded=False, col_widths=col_widths, title=title)
    return table


def single_table(data, header, col_widths):
    # headers = (f"BMP {which} Informatiom", "")
    headers = (header, "")
    style = [
        ("SPAN", (0, 0), (1, 0)),  # header row, merge columns 1 and 2
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # header row is bold
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),  # header col is bold
        ("FONTNAME", (1, 1), (1, -1), "Helvetica"),  # watershed data cells are not bold
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),  # header row is centered
        ("ALIGN", (0, 1), (0, -1), "LEFT"),  # header col is horizontally left-aligned
        ("ALIGN", (1, 1), (-1, -1), "LEFT"),  # all other cells are left-aligned
        ("VALIGN", (0, 0), (-1, -1), "TOP"),  # all  cells are vertically centered
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),  # line below column headers
    ]
    table = _make_table_from_df(data, headers, style, banded=False, col_widths=col_widths)
    return table


def no_info_table(header, col_width, msg):
    data = [(header,), (msg,)]
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # header row is bold
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),  # line below column headers
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # center everything
        ("VALIGN", (0, 0), (-1, -1), "TOP"),  # all  cells are vertically centered
    ]
    col_widths = validate.at_least_empty_list(col_width)
    table = Table(data, repeatRows=1, repeatCols=1, style=style, colWidths=col_widths)
    return table


def make_design_table(design_elements, table_width):
    header = "BMP Design Information"
    if design_elements is None:
        table = no_info_table(header, 0.25 * table_width, "No Design Information Available")
    else:
        nrows = design_elements.shape[0]
        if nrows < 10:
            col_widths = [table_width * 0.33] * 2
            table = single_table(design_elements, header, col_widths)
        else:
            half_rows = ceil(design_elements.shape[0] / 2)
            col_widths = [table_width * 0.25] * 4
            table = two_tables_next_to_eachother(
                design_elements.iloc[:half_rows].reset_index(drop=True),
                design_elements.iloc[half_rows:].reset_index(drop=True),
                header,
                header,
                col_widths,
                styled=True,
            )
    return table


def _header_footer(canvas, doc, filename, title):
    # Save the state of our canvas so we can draw on it
    canvas.saveState()

    # Header
    title = Paragraph(title, _HEADERSTYLE)
    w, h = title.wrap((doc.width - 3.5 * inch), 1 * inch)
    title.drawOn(canvas, 3.5 * inch, doc.height + doc.topMargin - 0.825 * inch)

    logo = Image("logo-withtext.png")
    logo.drawHeight *= 0.35
    logo.drawWidth *= 0.35
    logo.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - 1 * inch)

    # Footer
    footer = Paragraph(filename, _FOOTERSTYLE)
    w, h = footer.wrap(doc.width, doc.bottomMargin)
    footer.drawOn(canvas, doc.leftMargin, 0.35 * inch)

    # Release the canvas
    canvas.restoreState()


class _PDFReportMixin:
    margin = 0.5 * inch

    @property
    def table_width(self):
        return self.width - 2 * self.margin

    def render(self):
        doc = SimpleDocTemplate(
            self.buffer,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin * 3,
            bottomMargin=self.margin,
            pagesize=self.pagesize,
        )
        doc_elements = self.arrange_elements()
        self.build(doc, doc_elements)

    def build(self, doc, doc_elements):
        if self.pagesize == landscape(letter):
            canvasmaker = NumberedCanvasLandscape
        elif self.pagesize == letter:
            canvasmaker = NumberedCanvasPortrait
        else:
            raise NotImplementedError(f"Only letter paper is available, not {self.pagsize}")
        doc.build(
            doc_elements,
            onFirstPage=partial(_header_footer, filename=self.filename, title=self.title),
            onLaterPages=partial(_header_footer, filename=self.filename, title=self.title),
            canvasmaker=canvasmaker,
        )

    def save(self, *folders):
        for d in folders:
            self.buffer.seek(0)
            with Path(d, self.filename).open("wb") as out:
                out.write(self.buffer.read())


class BMPDescriptionReport(_PDFReportMixin):
    def __init__(self, buffer, filename, meta, design_elements, title):
        self.buffer = buffer
        self.pagesize = landscape(letter)
        self.width, self.height = self.pagesize
        self.meta = meta
        self.design_elements = design_elements
        self.title = title
        self.filename = filename

        self._loc_bmp_table = None
        self._wshed_dot_table = None
        self._cost_table = None
        self._design_table = None

    @property
    def loc_bmp_table(self):
        if self._loc_bmp_table is None:
            self._loc_bmp_table = two_tables_next_to_eachother(
                self.location_values(),
                self.bmp_values(),
                "",
                "",
                col_widths=[self.table_width * x for x in (0.10, 0.60, 0.15, 0.15)],
                styled=False,
            )
            self._loc_bmp_table.wrap(*self.pagesize)
        return self._loc_bmp_table

    @property
    def wshed_dot_table(self):
        if self._wshed_dot_table is None:
            self._wshed_dot_table = two_tables_next_to_eachother(
                self.watershed_values(),
                self.dot_values(),
                "Watershed Characteristics",
                "Transportation Characteristics",
                col_widths=[self.table_width / 4] * 4,
                styled=True,
            )
            self._wshed_dot_table.wrap(*self.pagesize)
        return self._wshed_dot_table

    @property
    def design_table(self):
        if self._design_table is None:
            self._design_table = make_design_table(self.design_values(), self.table_width)
            self._design_table.wrap(*self.pagesize)
        return self._design_table

    @property
    def cost_table(self):
        if self._cost_table is None:
            self._cost_table = single_table(
                self.cost_values(), "BMP Cost Informatiom", col_widths=[0.2 * self.table_width] * 2
            )
            self._cost_table.wrap(*self.pagesize)
        return self._cost_table

    def watershed_values(self):
        watershed_names = {
            "EPARainZone": ("EPA Rain Zone", _table_string),
            "WSName": ("Watershed Name", _table_string),
            "Type": ("Watershed Type", _table_string),
            "Area": ("Total Watershed Area", _table_float),
            "Area_unit": ("Area Unit", _table_string),
            "AreaImpervious_pct": ("Percent Impervious", _table_float),
            "NRCSSoilGroup": ("Soil Group", _table_string),
            "Area_Descr": ("Watershed Description", _table_string),
            "LandUse_Descr": ("Land Use Description", _table_string),
            "Vegetation_Descr": ("Vegetation Description", _table_string),
        }
        data = {value[0]: value[1](self.meta.get(key)) for key, value in watershed_names.items()}

        return pandas.Series(data).fillna("N/A").reset_index()

    def dot_values(self):
        dot_columns = {
            "DOT_ActivityType_flag": ("Activity Type", _table_string),
            "DOT_AADT": ("AADT", _table_int),
            "DOT_Lane_Count": ("Lane Count", _table_string),
            "DOT_HighwayConditions_Descr": ("Highway Conditions", _table_string),
            "DOT_HighwayMaintenance_Descr": ("Highway Maintenance", _table_string),
            "DOT_RoadType": ("Road Type", _table_string),
            "DOT_Resurfacing_Descr": ("Resurfacing", _table_string),
            "DOT_Shoulder_Descr": ("Shoulder", _table_string),
            "DOT_WinterMaintenance_Descr": ("Winter Maintenance", _table_string),
            "DOT_Conveyance_Descr": ("Conveyance", _table_string),
        }
        data = {value[0]: value[1](self.meta.get(key)) for key, value in dot_columns.items()}

        return pandas.Series(data).fillna("N/A").reset_index()

    def location_values(self):
        if not pandas.isnull(self.meta["ZipCode"]):
            address = "{City}, {State} {ZipCode}, {Country}"
        else:
            address = "{City}, {State}, {Country}"

        data = {
            "Description": self.meta.get("BMPType_Desc", "N/A"),
            "Test Site": self.meta.get("SiteName", "N/A"),
            "Location": address.format(**self.meta),
        }

        return pandas.Series(data).fillna("N/A").reset_index()

    def bmp_values(self):
        data = {
            "BMP Type": "{BMPCategory_Desc} ({BMPType})".format(**self.meta),
            "BMP Category": self.meta["BMPCategory_Code"],
            "Install Date": _table_date(self.meta["DateInstalled"]),
        }
        return pandas.Series(data).fillna("N/A").reset_index()

    def cost_values(self):
        cost_names = {"CostYear": "Annual Maintenance Cost", "CostTotal": "Capital Cost"}

        data = {value: _table_cost(self.meta.get(key)) for key, value in cost_names.items()}
        return pandas.Series(data).fillna("N/A").reset_index()

    def design_values(self):
        if self.design_elements is not None:
            table = (
                self.design_elements.assign(
                    Value=lambda df: df["Value_Final"].combine_first(df["Narrative_Descr"]).apply(_design_param_fmt)
                )
                .rename(columns={"DesignParameter_Final": "Design Parameter"})
                .reindex(columns=["Design Parameter", "Value"])
            )
            return table

    def arrange_elements(self):
        # Our container for 'Flowable' objects
        doc_elements = [
            self.loc_bmp_table,
            Spacer(self.width, 0.25 * inch),
            self.wshed_dot_table,
            Spacer(self.width, 0.25 * inch),
            self.cost_table,
        ]
        if self.design_elements is None:
            _spacer = Spacer(self.width, 0.25 * inch)
        else:
            _spacer = PageBreak()

        doc_elements.extend([_spacer, self.design_table])
        return doc_elements


class BMPHydroReport(_PDFReportMixin):
    def __init__(self, buffer, filename, meta, climate, precip, flow, title):
        self.buffer = buffer
        self.pagesize = letter
        self.width, self.height = self.pagesize
        self.meta = meta
        self.climate = climate
        self.precip = precip
        self.flow = flow
        self.title = title
        self.filename = filename

        self._loc_values = None
        self._bmp_values = None
        self._climate_values = None
        self._precip_values = None
        self._flow_values = None

        self._loc_bmp_table = None
        self._climate_table = None
        self._precip_table = None
        self._flow_table = None
        self._plot_image = None

        self.precip_units = _get_units(self.precip, "PrecipDepth_Unit")
        self.volume_units = _get_units(self.flow, "Volume_Units")

    @property
    def bmp_values(self):
        if self._bmp_values is None and (not self.meta.empty):
            data = {
                "BMP Category": self.meta["BMPCategory_Desc"],
                "BMP Type": self.meta["BMPType_Desc"],
                "Climate Station": self.climate["StationName"],
            }
            self._bmp_values = pandas.Series(data).fillna("N/A").reset_index()
        return self._bmp_values

    @property
    def loc_values(self):
        if self._loc_values is None and (not self.meta.empty):
            if not pandas.isnull(self.meta["ZipCode"]):
                address = "{City}, {State} {ZipCode}, {Country}"
            else:
                address = "{City}, {State}, {Country}"

            data = {
                "Test Site Name": self.meta["SiteName"],
                "BMP Name": self.meta["BMPName"],
                "Location": address.format(**self.meta),
            }
            self._loc_values = pandas.Series(data).fillna("N/A").reset_index()
        return self._loc_values

    @property
    def climate_values(self):
        if self._climate_values is None and not (self.climate.empty):
            columns = [
                "NbrStorms_{}Annual",
                "DepthInch_{}",
                "DurationHr_{}",
                "IntensityInchHr_{}",
                "InterEventDryDurationHr_{}",
            ]
            statistics = ("Avg", "COV")
            self._climate_value = pandas.DataFrame(
                data=[[_table_float(self.climate[col.format(stat)]) for col in columns] for stat in statistics],
                index=["Mean", "Coefficient of Variation"],
                columns=[
                    "Annual Number of Storms",
                    "Annual Total Precip. (cm)",
                    "Storm Duration (hrs)",
                    "Storm Intensity (cm/hrs)",
                    "Period Between Storms (hrs)",
                ],
            )
        return self._climate_value.rename_axis(index="Statistic").reset_index()

    @property
    def precip_values(self):
        if self._precip_values is None and (not self.precip.empty):
            d = self.precip["PrecipDepth_Value"].describe()
            self._precip_values = pandas.DataFrame(
                {
                    "Number of Events Monitored": [_table_int(d["count"])],
                    f"Average Depth of Precipitation ({self.precip_units})": [_table_float(d["mean"])],
                    f"Minimum Depth of Precipitation ({self.precip_units})": [_table_float(d["min"])],
                    f"Maximum Depth of Precipitation ({self.precip_units})": [_table_float(d["max"])],
                    f"Standard Deviation of Precipitation ({self.precip_units})": [_table_float(d["std"])],
                }
            )
        return self._precip_values

    @property
    def flow_values(self):
        if self._flow_values is None and (not self.flow.empty):
            cols = {
                "MSType": "Flow Type",
                "count": "Number of Events",
                "mean": f"Average Event Flow Volume ({self.volume_units})",
                "min": f"Minimum Event Flow Volume ({self.volume_units})",
                "max": f"Maximum Event Flow Volume ({self.volume_units})",
                "std": f"Standard Deviation of Event Flow Volume ({self.volume_units})",
            }
            self._flow_values = (
                self.flow.groupby(["MSType"])["Volume_Total"]
                .describe()
                .fillna({"std": 0})
                .astype(int)
                .applymap(_table_int)
                .reset_index()
                .loc[:, list(cols.keys())]
                .rename(columns=cols)
            )
        return self._flow_values

    @property
    def loc_bmp_table(self):
        if self._loc_bmp_table is None and self.loc_values is not None and self.bmp_values is not None:
            self._loc_bmp_table = two_tables_next_to_eachother(
                self.loc_values,
                self.bmp_values,
                "",
                "",
                col_widths=[self.table_width * x for x in (0.15, 0.35, 0.15, 0.35)],
                styled=False,
            )
            self._loc_bmp_table.wrap(*self.pagesize)
        return self._loc_bmp_table

    @property
    def climate_table(self):
        if self._climate_table is None:
            title = "Regional Climate Statistics"
            if self.climate_values is not None:
                self._climate_table = normal_table(
                    self.climate_values,
                    title,
                    col_widths=[0.16 * self.table_width] * 6,
                )
            else:
                self._climate_table = no_info_table(title, self.table_width * 0.25, "No Climate Information Available")
            self._climate_table.wrap(*self.pagesize)
        return self._climate_table

    @property
    def precip_table(self):
        if self._precip_table is None:
            title = "Measured Precipitation Statistics"
            if self.precip_values is not None:
                self._precip_table = normal_table(self.precip_values, title, col_widths=[0.2 * self.table_width] * 5)
            else:
                self._precip_table = no_info_table(
                    title,
                    self.table_width * 0.25,
                    "Precipitation Data Flagged for Limited Use or Not Available",
                )
            self._precip_table.wrap(*self.pagesize)
        return self._precip_table

    @property
    def flow_table(self):
        if self._flow_table is None:
            title = "Measured Volume Statistics"
            if self.flow_values is not None:
                self._flow_table = normal_table(self.flow_values, title, col_widths=[0.16 * self.table_width] * 6)
            else:
                self._flow_table = no_info_table(
                    title, self.table_width * 0.25, "Volume Data Flagged for Limited Use or Not Available"
                )
            self._flow_table.wrap(*self.pagesize)
        return self._flow_table

    @property
    def plot_image(self):
        if self._plot_image is None:
            _buffer = BytesIO()
            fig = precip_flow_plot(self.precip, self.flow, self.precip_units, self.volume_units)
            fig.tight_layout()
            fig.savefig(_buffer, format="png")
            _buffer.seek(0)
            self._plot_image = Image(_buffer)
            self._plot_image.drawHeight *= 0.20
            self._plot_image.drawWidth *= 0.20
            pyplot.close(fig)
        return self._plot_image

    def arrange_elements(self):
        doc_elements = [
            self.loc_bmp_table,
            Spacer(self.width, 0.25 * inch),
            self.climate_table,
            Spacer(self.width, 0.25 * inch),
            self.precip_table,
            Spacer(self.width, 0.25 * inch),
            self.flow_table,
            Spacer(self.width, 0.35 * inch),
            self.plot_image,
        ]
        return doc_elements


class StatReport:
    def __init__(self):
        self.std_tables = ["bacteria", "metals"]
        self.std_docs = ["Bacteria", "Metals"]

        self.cbay_tables = [
            "tss_cbay",
            "nutrients_cbay",
            "tss_noncbay",
            "nutrients_noncbay",
        ]
        self.cbay_docs = [
            "Total Suspended Solids in Chesapeake Bay",
            "Nutrients in Chesapeake Bay",
            "Total Suspended Solids outside of Chesapeake Bay",
            "Nutrients outside of Chesapeake Bay",
        ]

        self.md_tables = ["metals_md", "tss_md", "nutrients_md"]
        self.md_docs = [
            "Metals (Manufactured devices only)",
            "TSS (Manufactured devices only)",
            "Nutrients (Manufactured devices only)",
        ]

        self.all_tables = [
            "bacteria",
            "metals",
            "tss",
            "nutrients",
            "tss_cbay",
            "nutrients_cbay",
            "tss_noncbay",
            "nutrients_noncbay",
            "metals_md",
            "tss_md",
            "nutrients_md",
        ]

        self.all_docs = [
            "Bacteria",
            "Metals",
            "Total Suspended Solids",
            "Nutrients",
            "Total Suspended Solids in Chesapeake Bay",
            "Nutrients in Chesapeake Bay",
            "Total Suspended Solids outside of Chesapeake Bay",
            "Nutrients outside of Chesapeake Bay",
            "Metals (Manufactured devices only)",
            "TSS (Manufactured devices only)",
            "Nutrients (Manufactured devices only)",
        ]

        self.sbpat_tables = ["bacteria_sbpat", "tss", "nutrients", "metals"]

    def makeSBPAT_tables(self):
        for t in self.sbpat_tables:
            print("\n\nsummarizing %s for SBPAT" % t)
            summary.sbpat_stats(t)

    def makeBoxplots(self, tables):
        for t in tables:
            print("\n\nboxplot summaries for %s" % t)
            summary.paramBoxplots(t)

    def makeInputFiles(self, tables):
        for t in tables:
            print("\n\nmaking input files for %s" % t)
            summary.latexInputFile(t, regenFigs=True)

    def makeReports(self, tables, docs):
        versions = ["draft", "final"]
        for t, d in zip(tables, docs):
            for v in versions:
                print("\n\nsummarizing %s" % t)
                summary.latexReport(t, d, template=v)

    def compileReport(self, docs, version="draft"):
        os.chdir("bmp/tex")
        for d in docs:
            filename = "%s_%s.tex" % (version, d.replace(" ", ""))
            print("Compiling report %s" % filename)
            os.system("pdflatex -quiet %s" % filename)
            print("Updating references in %s" % filename)
            os.system("pdflatex -quiet %s" % filename)

        os.chdir("../..")

    def makeTables(self, tables):
        for t in tables:
            print("\n\nsummary table for %s" % t)
            summary.paramTables(t)

    def dumpData(self, tables):
        for t in tables:
            print("\n\ndumping %s table" % t)
            summary.dataDump(t)

    def fullSuite(self, tables, docs, version):
        self.dumpData(tables)
        self.makeTables(tables)
        self.makeBoxplots(tables)
        self.makeReports(tables, docs)
        self.makeInputFiles(tables)
        self.compileReport(docs, version=version)


def test_run():
    report = StatReport()
    report.makeInputFiles(report.std_tables)
