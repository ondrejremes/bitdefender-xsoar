import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Liberation Sans (supports Czech diacritics)
_FONT_DIR = "/usr/share/fonts/truetype/liberation"
pdfmetrics.registerFont(TTFont("LiberationSans", f"{_FONT_DIR}/LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("LiberationSans-Bold", f"{_FONT_DIR}/LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("LiberationSans-Italic", f"{_FONT_DIR}/LiberationSans-Italic.ttf"))

FONT = "LiberationSans"
FONT_BOLD = "LiberationSans-Bold"

# Colors
COLOR_DARK = colors.HexColor("#1A2235")
COLOR_LIGHT = colors.HexColor("#E8EDF5")
COLOR_MUTED = colors.HexColor("#6C757D")

styles = getSampleStyleSheet()
STYLE_TITLE = ParagraphStyle(
    "title", parent=styles["Title"],
    fontName=FONT_BOLD, fontSize=16, textColor=COLOR_DARK, spaceAfter=4,
)
STYLE_SUBTITLE = ParagraphStyle(
    "subtitle", parent=styles["Normal"],
    fontName=FONT, fontSize=10, textColor=COLOR_MUTED, spaceAfter=12,
)
STYLE_SECTION = ParagraphStyle(
    "section", parent=styles["Heading2"],
    fontName=FONT_BOLD, fontSize=11, textColor=COLOR_DARK, spaceBefore=14, spaceAfter=6,
)


def _table_style(header_rows=1):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), COLOR_DARK),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (1, header_rows), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, COLOR_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DEE2E6")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])


def build_pdf(date_from, date_to, total_h, total_billable_h,
              by_agent, by_contract, by_workorder, worklogs,
              agent_filter: str = "") -> bytes:

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    label = f" \u2014 {agent_filter}" if agent_filter else ""
    story = []

    # Header
    story.append(Paragraph(f"Intern\u00ed reporting{label}", STYLE_TITLE))
    story.append(Paragraph(f"Obdob\u00ed: {date_from} \u2013 {date_to}", STYLE_SUBTITLE))

    # Summary table
    story.append(Paragraph("Souhrn", STYLE_SECTION))
    summary_data = [
        ["Ukazatel", "Hodnota"],
        ["Celkem hodin", f"{total_h}"],
        ["Fakturovitateln\u00e9 hodiny", f"{round(total_billable_h, 2)}"],
        ["Nefakturovitateln\u00e9 hodiny", f"{round(total_h - total_billable_h, 2)}"],
        ["Po\u010det z\u00e1znam\u016f", str(len(worklogs))],
    ]
    t = Table(summary_data, colWidths=[120 * mm, 60 * mm])
    t.setStyle(_table_style())
    story.append(t)

    # By agent
    story.append(Paragraph("Podle technika", STYLE_SECTION))
    agent_data = [["Technik", "Celkem hodin", "Fakturovitateln\u00e9", "Nefakturovitateln\u00e9", "Z\u00e1znam\u016f"]]
    for row in by_agent:
        agent_data.append([
            row["agent"],
            f"{row['hours']}",
            f"{row['hours_billable']}",
            f"{round(row['hours'] - row['hours_billable'], 2)}",
            str(row["entries"]),
        ])
    t = Table(agent_data, colWidths=[80 * mm, 40 * mm, 40 * mm, 50 * mm, 30 * mm])
    t.setStyle(_table_style())
    story.append(t)

    # By contract
    story.append(PageBreak())
    story.append(Paragraph("Podle kontraktu / z\u00e1kazn\u00edka", STYLE_SECTION))
    contract_data = [["Kontrakt", "Z\u00e1kazn\u00edk", "Celkem hodin", "Fakturovitateln\u00e9", "Nefakturovitateln\u00e9"]]
    for row in by_contract:
        contract_data.append([
            row["contract"],
            row["org"],
            f"{row['hours']}",
            f"{row['hours_billable']}",
            f"{round(row['hours'] - row['hours_billable'], 2)}",
        ])
    t = Table(contract_data, colWidths=[80 * mm, 70 * mm, 35 * mm, 35 * mm, 40 * mm])
    t.setStyle(_table_style())
    story.append(t)

    # Detail
    story.append(PageBreak())
    story.append(Paragraph("Detail z\u00e1znam\u016f", STYLE_SECTION))
    detail_data = [["Datum", "Technik", "Z\u00e1kazn\u00edk", "Kontrakt", "WorkOrder", "Hodiny", "Faktur."]]
    for wl in worklogs:
        detail_data.append([
            wl["start_date"][:10],
            wl["agent"],
            wl["org"],
            wl["contract"],
            wl["workorder"],
            f"{wl['duration_h']}",
            "Ano" if wl["is_billable"] else "Ne",
        ])
    t = Table(detail_data, colWidths=[22 * mm, 40 * mm, 50 * mm, 60 * mm, 35 * mm, 20 * mm, 20 * mm])
    t.setStyle(_table_style())
    story.append(t)

    doc.build(story)
    return buf.getvalue()
