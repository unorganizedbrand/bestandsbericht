"""PDF-Export der Bestandsmatrix im A4-Hochformat."""
from io import BytesIO
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import einstellungen as cfg

BLAU = colors.HexColor("#1E2A78")
LINIE = colors.HexColor("#E6E8EF")
HINTERGRUND = colors.HexColor("#F6F8FC")
ROT = colors.HexColor("#D93025")


def _zahl(wert):
    if pd.isna(wert):
        return ""
    return f"{int(wert):,}".replace(",", ".")


def erstelle_pdf(matrix, stand, filter_text):
    puffer = BytesIO()
    rand = 12 * mm
    doc = SimpleDocTemplate(puffer, pagesize=A4, leftMargin=rand, rightMargin=rand,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title="Bestandsbericht", author="UNORGANIZED BRAND")

    titel = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=22, leading=26)
    produkt_stil = ParagraphStyle("p", fontName="Helvetica-Bold", fontSize=7.5, leading=9)
    klein = ParagraphStyle("k", fontName="Helvetica", fontSize=7.5, leading=10,
                           textColor=colors.HexColor("#555555"))
    elemente = [
        Paragraph("BESTANDSBERICHT", titel),
        Spacer(1, 2 * mm),
        Paragraph(f"Stand: {stand:%d.%m.%Y, %H:%M} Uhr &nbsp;·&nbsp; {filter_text}", klein),
        Spacer(1, 5 * mm),
    ]

    if matrix.empty:
        elemente.append(Paragraph("Keine Daten für die gewählten Filter.", klein))
        doc.build(elemente)
        return puffer.getvalue()

    groessen = [c for c in matrix.columns if c != "GESAMT"]
    KOPF_LABEL = {"ONE SIZE": "ONE\nSIZE", "UNBEKANNT": "UNBE-\nKANNT"}
    kopf = ["PRODUKT", "FARBE"] + [KOPF_LABEL.get(g, g) for g in groessen] + ["GESAMT"]
    daten = [kopf]
    stil = [
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7),
        ("TEXTCOLOR", (0, 0), (-1, 0), BLAU),
        ("BACKGROUND", (0, 0), (-1, 0), HINTERGRUND),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.black),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 7.5),
        ("FONT", (0, 1), (0, -1), "Helvetica-Bold", 7.5),
        ("FONT", (-1, 1), (-1, -1), "Helvetica-Bold", 7.5),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]

    gesamt_alle = 0
    for produkt, gruppe in matrix.groupby(level=0, sort=False):
        start = len(daten)
        for i, ((_, farbe), werte) in enumerate(gruppe.iterrows()):
            zeile = [Paragraph(escape(produkt), produkt_stil) if i == 0 else "", farbe]
            for spalte, g in enumerate(groessen):
                w = werte[g]
                zeile.append(_zahl(w))
                if not pd.isna(w) and cfg.WARNSCHWELLE and w <= cfg.WARNSCHWELLE:
                    stil.append(("TEXTCOLOR", (2 + spalte, len(daten)), (2 + spalte, len(daten)), ROT))
            zeile.append(_zahl(werte["GESAMT"]))
            daten.append(zeile)
            stil.append(("LINEBELOW", (1, len(daten) - 1), (-1, len(daten) - 1), 0.4, LINIE))
        summe = gruppe.sum(numeric_only=True, min_count=1)
        gesamt_alle += summe["GESAMT"] or 0
        if start > 1:
            stil.append(("LINEABOVE", (0, start), (-1, start), 0.8, colors.black))
        if len(gruppe) == 1:
            continue
        # Summenzeile je Produkt (nur bei mehreren Farben)
        daten.append(["", "SUMME"] + [_zahl(summe[g]) for g in groessen] + [_zahl(summe["GESAMT"])])
        z = len(daten) - 1
        stil += [("FONT", (1, z), (-1, z), "Helvetica-Bold", 7.5),
                 ("BACKGROUND", (0, z), (-1, z), HINTERGRUND),
                 ("LINEBELOW", (0, z), (-1, z), 0.8, colors.black)]

    gesamt = matrix.sum(numeric_only=True, min_count=1)
    daten.append(["GESAMT", ""] + [_zahl(gesamt[g]) for g in groessen] + [_zahl(gesamt_alle)])
    stil += [("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 8),
             ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.black)]

    breite = A4[0] - 2 * rand
    w_produkt, w_farbe, w_gesamt = 28 * mm, 34 * mm, 15 * mm
    w_groesse = (breite - w_produkt - w_farbe - w_gesamt) / max(len(groessen), 1)
    tabelle = Table(daten, colWidths=[w_produkt, w_farbe] + [w_groesse] * len(groessen) + [w_gesamt],
                    repeatRows=1)
    tabelle.setStyle(TableStyle(stil))
    elemente.append(tabelle)

    def fusszeile(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawString(rand, 8 * mm, f"UNORGANIZED BRAND · Bestandsbericht · {stand:%d.%m.%Y %H:%M}")
        canvas.drawRightString(A4[0] - rand, 8 * mm, f"Seite {doc_.page}")
        canvas.restoreState()

    doc.build(elemente, onFirstPage=fusszeile, onLaterPages=fusszeile)
    return puffer.getvalue()
