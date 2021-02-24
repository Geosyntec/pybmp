import os
from pathlib import Path
from datetime import datetime
from functools import partial
from math import ceil

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
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from pybmpdb import summary
from wqio.utils import sigFigs, no_op

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
_HEADERSTYLE.alignment = TA_CENTER


def _table_float(x):
    if pandas.isnull(x):
        return "N/A"
    return sigFigs(x, 3, tex=False, pval=False, forceint=False)


def _table_int(x):
    if pandas.isnull(x):
        return "N/A"
    return str(int(x))


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


def _paragraph(text):
    styleN = STYLES["BodyText"]
    styleN.alignment = TA_LEFT
    styleN.leading = 9
    return Paragraph(f"{text}", styleN)


class NumberedCanvas(canvas.Canvas):
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
        self.drawRightString(
            10.5 * inch, 0.35 * inch, f"Page {self._pageNumber} of {page_count}"
        )
        # self.drawCentredString(6.5 * inch, 0.5 * inch, "Test centred")
        self.drawString(0.5 * inch, 0.35 * inch, f"Generated: {TODAY}")


def get_sites_info():
    return pandas.read_json(BASEURL + "/DOTSites", dtype={"PDFID": str}).sort_values(
        by=["PDFID"]
    )


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
    elements = pandas.read_json(
        BASEURL + f"/vBMPDesignElements?pdf_id={pdfid}", dtype=dtype
    )

    if elements.shape[0] == 0:
        elements = None

    title = meta["BMPName"]
    return meta, elements, title


def dot_table(meta):
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
    data = {value[0]: value[1](meta.get(key)) for key, value in dot_columns.items()}

    return pandas.Series(data).fillna("N/A").reset_index()


def watershed_table(meta):
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
    data = {value[0]: value[1](meta.get(key)) for key, value in watershed_names.items()}

    return pandas.Series(data).fillna("N/A").reset_index()


def location_info_table(meta):
    if not pandas.isnull(meta["ZipCode"]):
        address = "{City}, {State} {ZipCode}, {Country}"
    else:
        address = "{City}, {State}, {Country}"

    data = {
        "Description": meta.get("BMPType_Desc", "N/A"),
        "Test Site": meta.get("SiteName", "N/A"),
        "Location": address.format(**meta),
    }

    return pandas.Series(data).fillna("N/A").reset_index()


def bmpinfo_table(meta):
    data = {
        "BMP Type": "{BMPCategory_Desc} ({BMPType})".format(**meta),
        "BMP Category": meta["BMPCategory_Code"],
        "Install Date": _table_date(meta["DateInstalled"]),
    }
    return pandas.Series(data).fillna("N/A").reset_index()


def cost_table(meta):
    cost_names = {"CostYear": "Cost per year", "CostTotal": "Total Cost"}

    data = {value: _table_cost(meta.get(key)) for key, value in cost_names.items()}
    return pandas.Series(data).fillna("N/A").reset_index()


def design_table(elements):
    if elements is not None:
        table = (
            elements.assign(
                Value=lambda df: df["Value_Final"].combine_first(df["Narrative_Descr"])
            )
            .rename(columns={"DesignParameter_Final": "Design Parameter"})
            .reindex(columns=["Design Parameter", "Value"])
        )
        return table


def _make_table_from_df(
    df, headers, style, datecols=None, dateformat=None, banded=True, col_widths=None
):
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


    """
    if datecols:
        if not dateformat:
            dateformat = "%Y-%m-%d"
        df = df.assign(**{dc: df[dc].dt.strftime(dateformat) for dc in datecols})

    if banded:
        bands = [
            ("BACKGROUND", (0, row), (-1, row), colors.lightgrey)
            for row in range(1, df.shape[0] + 1, 2)
        ]
        style = [*style, *bands]

    _data = df.astype(str).applymap(_paragraph).values.tolist()
    table_values = [headers, *_data]
    table = Table(
        table_values, repeatRows=1, repeatCols=1, style=style, colWidths=col_widths
    )
    return table


def make_wshed_dot_table(wshed, dot, table_width):
    data = pandas.concat([wshed, dot], axis="columns")
    headers = ("Watershed Characteristics", "", "Transportation Characteristics", "")
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
        (
            "ALIGN",
            (1, 1),
            (-1, -1),
            "LEFT",
        ),  # all other cells are horizontally centered
        ("VALIGN", (0, 0), (-1, -1), "TOP"),  # all  cells are vertically centered
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),  # line below column headers
        (
            "LINEAFTER",
            (1, 0),
            (1, -1),
            1,
            colors.black,
        ),  # line between the two subtables
    ]
    col_widths = [table_width / len(headers)] * len(headers)
    table = _make_table_from_df(
        data, headers, style, banded=False, col_widths=col_widths
    )
    return table


def make_bmp_info_table(loc, bmp, table_width):
    data = pandas.concat([loc, bmp], axis="columns")
    style = [
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),  # loc header col is bold
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),  # bmp header col is bold
        ("FONTNAME", (1, 1), (1, -1), "Helvetica"),  # watershed data cells are not bold
        ("FONTNAME", (3, 1), (3, -1), "Helvetica"),  # DOT data cells are not bold
        ("ALIGN", (0, 0), (-2, -1), "LEFT"),  # first three cols are left-aligned
        ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),  # last col is right-aligned
        ("VALIGN", (0, 0), (-1, -1), "TOP"),  # all  cells are vertically centered
    ]
    col_widths = [table_width * x for x in (0.10, 0.60, 0.15, 0.15)]
    table = _make_table_from_df(
        data, [""] * 4, style, banded=False, col_widths=col_widths
    )
    return table


def make_cost_or_design_table(data, which, table_width, factor):
    headers = (f"BMP {which} Informatiom", "")
    style = [
        ("SPAN", (0, 0), (1, 0)),  # header row, merge columns 1 and 2
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # header row is bold
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),  # header col is bold
        ("FONTNAME", (1, 1), (1, -1), "Helvetica"),  # watershed data cells are not bold
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),  # header row is centered
        ("ALIGN", (0, 1), (0, -1), "LEFT"),  # header col is horizontally left-aligned
        (
            "ALIGN",
            (1, 1),
            (-1, -1),
            "LEFT",
        ),  # all other cells are horizontally centered
        ("VALIGN", (0, 0), (-1, -1), "TOP"),  # all  cells are vertically centered
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),  # line below column headers
    ]
    col_widths = [factor * table_width, factor * table_width]
    table = _make_table_from_df(
        data, headers, style, banded=False, col_widths=col_widths
    )
    return table


def make_design_table(design_elements, table_width):
    if design_elements is None:
        data = [("BMP Design Information",), ("No Design Information Available",)]
        style = [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # header row is bold
            (
                "LINEBELOW",
                (0, 0),
                (-1, 0),
                1,
                colors.black,
            ),  # line below column headers
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # center everything
            ("VALIGN", (0, 0), (-1, -1), "TOP"),  # all  cells are vertically centered
        ]
        col_widths = [0.25 * table_width]
        table = Table(
            data, repeatRows=1, repeatCols=1, style=style, colWidths=col_widths
        )
    else:
        nrows = design_elements.shape[0]

        if nrows < 10:
            table = make_cost_or_design_table(
                design_elements, "Design", table_width, 0.33
            )
        else:
            half_rows = ceil(design_elements.shape[0] / 2)
            table = make_wshed_dot_table(
                design_elements.iloc[:half_rows].reset_index(drop=True),
                design_elements.iloc[half_rows:].reset_index(drop=True),
                table_width,
            )
            data = pandas.concat(
                [
                    design_elements.iloc[:half_rows].reset_index(drop=True),
                    design_elements.iloc[half_rows:].reset_index(drop=True),
                ],
                axis="columns",
            ).fillna("")
            headers = ("BMP Design Information", "", "BMP Design Information", "")
            style = [
                ("SPAN", (0, 0), (1, 0)),  # header row, merge columns 1 and 2
                ("SPAN", (2, 0), (3, 0)),  # header row, merge columns 3 and 4
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),  # header row is bold
                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold",
                ),  # watershed header col is bold
                (
                    "FONTNAME",
                    (2, 0),
                    (2, -1),
                    "Helvetica-Bold",
                ),  # DOT header col is bold
                (
                    "FONTNAME",
                    (1, 1),
                    (1, -1),
                    "Helvetica",
                ),  # watershed data cells are not bold
                (
                    "FONTNAME",
                    (3, 1),
                    (3, -1),
                    "Helvetica",
                ),  # DOT data cells are not bold
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),  # header row is centered
                (
                    "ALIGN",
                    (0, 1),
                    (0, -1),
                    "LEFT",
                ),  # header col is horizontally left-aligned
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "LEFT",
                ),  # all other cells are horizontally centered
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),  # all  cells are vertically centered
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    1,
                    colors.black,
                ),  # line below column headers
                (
                    "LINEAFTER",
                    (1, 0),
                    (1, -1),
                    1,
                    colors.black,
                ),  # line between the two subtables
            ]
            col_widths = [table_width / len(headers)] * len(headers)
            table = _make_table_from_df(
                data, headers, style, banded=False, col_widths=col_widths
            )
    return table


def _header_footer(canvas, doc, filename, title):
    # Save the state of our canvas so we can draw on it
    canvas.saveState()

    # Header
    title = Paragraph(f"BMP: {title}", _HEADERSTYLE)
    w, h = title.wrap(doc.width, doc.topMargin)
    title.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - 0.75 * inch)

    logo = Image("logo-notext.png")
    logo.drawHeight *= 0.5
    logo.drawWidth *= 0.5
    logo.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - 1 * inch)

    # Footer
    footer = Paragraph(filename, _FOOTERSTYLE)
    w, h = footer.wrap(doc.width, doc.bottomMargin)
    footer.drawOn(canvas, doc.leftMargin, 0.35 * inch)

    # Release the canvas
    canvas.restoreState()


class _PDFReportMixin:
    def build(self, doc, doc_elements):
        doc.build(
            doc_elements,
            onFirstPage=partial(
                _header_footer, filename=self.filename, title=self.title
            ),
            onLaterPages=partial(
                _header_footer, filename=self.filename, title=self.title
            ),
            canvasmaker=NumberedCanvas,
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

    def render(self):
        margin = 0.5 * inch
        doc = SimpleDocTemplate(
            self.buffer,
            rightMargin=margin,
            leftMargin=margin,
            topMargin=margin * 3,
            bottomMargin=margin,
            pagesize=self.pagesize,
        )

        # Our container for 'Flowable' objects
        loc_bmp = make_bmp_info_table(
            location_info_table(self.meta),
            bmpinfo_table(self.meta),
            table_width=self.width - 2 * doc.leftMargin,
        )
        loc_bmp.wrap(*self.pagesize)

        wshed_dot = make_wshed_dot_table(
            watershed_table(self.meta),
            dot_table(self.meta),
            table_width=self.width - 2 * doc.leftMargin,
        )
        wshed_dot.wrap(*self.pagesize)

        cost = make_cost_or_design_table(
            cost_table(self.meta),
            "Cost",
            table_width=self.width - 2 * doc.leftMargin,
            factor=0.2,
        )
        cost.wrap(*self.pagesize)

        design = make_design_table(
            design_table(self.design_elements), self.width - 2 * doc.leftMargin
        )
        design.wrap(*self.pagesize)

        doc_elements = [
            loc_bmp,
            Spacer(self.width, 0.25 * inch),
            wshed_dot,
            Spacer(self.width, 0.25 * inch),
            cost,
        ]
        if self.design_elements is None:
            _spacer = Spacer(self.width, 0.25 * inch)
        else:
            _spacer = PageBreak()

        doc_elements.extend([_spacer, design])
        self.build(doc, doc_elements)


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

    def render(self):
        margin = 0.5 * inch
        doc = SimpleDocTemplate(
            self.buffer,
            rightMargin=margin,
            leftMargin=margin,
            topMargin=margin * 3,
            bottomMargin=margin,
            pagesize=self.pagesize,
        )

        # Our container for 'Flowable' objects
        loc_bmp = make_bmp_info_table(
            location_info_table(self.meta),
            bmpinfo_table(self.meta),
            table_width=self.width - 2 * doc.leftMargin,
        )
        loc_bmp.wrap(*self.pagesize)

        wshed_dot = make_wshed_dot_table(
            watershed_table(self.meta),
            dot_table(self.meta),
            table_width=self.width - 2 * doc.leftMargin,
        )
        wshed_dot.wrap(*self.pagesize)

        cost = make_cost_or_design_table(
            cost_table(self.meta),
            "Cost",
            table_width=self.width - 2 * doc.leftMargin,
            factor=0.2,
        )
        cost.wrap(*self.pagesize)

        design = make_design_table(
            design_table(self.design_elements), self.width - 2 * doc.leftMargin
        )
        design.wrap(*self.pagesize)

        doc_elements = [
            loc_bmp,
            Spacer(self.width, 0.25 * inch),
            wshed_dot,
            Spacer(self.width, 0.25 * inch),
            cost,
        ]
        if self.design_elements is None:
            _spacer = Spacer(self.width, 0.25 * inch)
        else:
            _spacer = PageBreak()

        doc_elements.extend([_spacer, design])
        self.build(doc, doc_elements)


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
