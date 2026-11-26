"""BESTANDSBERICHT – Live-Bestand aus Shopify als Matrix (Produkt × Farbe × Größe)."""
import html

import pandas as pd
import streamlit as st

import einstellungen as cfg
from pdf_export import erstelle_pdf
from shopify_data import baue_matrix, lade_bestand

st.set_page_config(page_title="Bestandsbericht", page_icon="📦", layout="wide")

STATUS_LABEL = {"ACTIVE": "Aktiv", "DRAFT": "Entwurf", "ARCHIVED": "Archiviert", "UNLISTED": "Nicht gelistet"}
MENGENART = {"Verfügbar": "verfuegbar", "Lagerbestand (on hand)": "lagerbestand"}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
html, body, [class*="css"], .stMarkdown, .stCheckbox label p { font-family: 'Inter', sans-serif; }
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 2rem; max-width: 1500px; }
h1.titel { font-weight: 900; font-size: 3rem; letter-spacing: -0.04em; margin: 0 0 .4rem 0;
           border-bottom: 4px solid #000; padding-bottom: .6rem; }
.filterkopf { font-weight: 800; letter-spacing: .12em; font-size: .95rem; padding-top: .45rem; }
.st-key-filterbox .stCheckbox label p { font-weight: 600; text-transform: uppercase; font-size: .9rem; }
[class*="st-key-alle_"] button p { color: #2B59E8 !important; font-weight: 600; }
[class*="st-key-keine_"] button p { color: #E5483B !important; font-weight: 600; }
[class*="st-key-alle_"] button, [class*="st-key-keine_"] button { padding: 0 !important; min-height: 0 !important; }
.st-key-filterbox { border: 2px solid #000; background: #F6F8FC; padding: 1.2rem 1.4rem; border-radius: 0; }
.bestand-wrap { overflow-x: auto; margin-top: 1.5rem; }
table.bestand { border-collapse: collapse; border: none !important; width: 100%; font-family: 'Inter', sans-serif; font-size: .92rem; }
table.bestand th { background: #F6F8FC; color: #1E2A78; font-weight: 800; letter-spacing: .08em;
                   text-align: right; padding: .9rem .45rem; border-bottom: 4px solid #000;
                   position: sticky; top: 0; font-size: .8rem; }
table.bestand th, table.bestand td { border-left: none !important; border-right: none !important; border-top: none; }
table.bestand th.l, table.bestand td.l { text-align: left; }
table.bestand td.produkt { white-space: nowrap; }
table.bestand td { padding: .5rem .45rem; text-align: right; color: #3A4255; font-weight: 600;
                   border-bottom: 1px solid #ECEEF3; font-variant-numeric: tabular-nums; }
table.bestand td.produkt { color: #000; font-weight: 800; }
table.bestand td.farbe { color: #3A4255; font-weight: 800; }
table.bestand td.gesamt { color: #000; font-weight: 800; }
table.bestand td.warn { color: #D93025; }
table.bestand tr.summe td { background: #F6F8FC; color: #000; font-weight: 800; border-bottom: 2px solid #000; }
table.bestand tr.total td { color: #000; font-weight: 900; border-top: 4px solid #000; border-bottom: none; font-size: 1rem; }
.info { color: #6B7280; font-size: .85rem; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- Login
def passwort_ok():
    try:
        passwort = st.secrets.get("APP_PASSWORD")
    except Exception:
        passwort = None
    if not passwort or st.session_state.get("eingeloggt"):
        return True
    st.markdown('<h1 class="titel">BESTANDSBERICHT</h1>', unsafe_allow_html=True)
    eingabe = st.text_input("Passwort", type="password")
    if eingabe:
        if eingabe == passwort:
            st.session_state["eingeloggt"] = True
            st.rerun()
        st.error("Falsches Passwort.")
    return False


if not passwort_ok():
    st.stop()


# --------------------------------------------------------------------------- Daten
with st.spinner("Lade Bestand aus Shopify …"):
    try:
        df_alle, stand = lade_bestand()
    except Exception as e:
        st.error(f"Daten konnten nicht geladen werden: {e}")
        st.stop()


# --------------------------------------------------------------------------- Sidebar
with st.sidebar:
    st.markdown("### Bestandsbericht")
    if st.button("🔄 Aktualisieren", width="stretch", type="primary"):
        lade_bestand.clear()
        st.rerun()
    st.caption(f"Stand: {stand:%d.%m.%Y, %H:%M:%S} Uhr · automatisch alle "
               f"{cfg.AUTO_AKTUALISIERUNG_MINUTEN} Min.")
    st.divider()

    standorte = sorted(df_alle["standort"].unique())
    std_standorte = [s for s in cfg.STANDARD_STANDORTE if s in standorte] or standorte
    sel_standorte = st.multiselect("Standort", standorte, default=std_standorte)

    kanaele = sorted(df_alle["kanal"].unique())
    sel_kanaele = st.multiselect("Kanal", kanaele, default=kanaele,
                                 help="About You = Varianten mit SKU-Endung _AY")

    status_werte = [s for s in STATUS_LABEL if s in set(df_alle["status"])]
    sel_status = st.multiselect("Produktstatus", status_werte,
                                default=[s for s in cfg.STANDARD_STATUS if s in status_werte],
                                format_func=lambda s: STATUS_LABEL.get(s, s))

    mengenart_label = st.radio("Menge", list(MENGENART), horizontal=False)
    mengenart = MENGENART[mengenart_label]
    nullen_ausblenden = st.checkbox("Farben ohne Bestand ausblenden", value=True)
    pdf_platz = st.container()

df_basis = df_alle[df_alle["standort"].isin(sel_standorte)
                   & df_alle["kanal"].isin(sel_kanaele)
                   & df_alle["status"].isin(sel_status)]


# --------------------------------------------------------------------------- Filterbox
def setze_alle(gruppe, werte, an):
    for w in werte:
        st.session_state[f"f_{gruppe}_{w}"] = an


def filterspalte(spalte, titel, gruppe, werte):
    with spalte:
        k1, k2, k3 = st.columns([5, 1.1, 1.3], vertical_alignment="center")
        k1.markdown(f'<div class="filterkopf">{titel}</div>', unsafe_allow_html=True)
        k2.button("Alle", key=f"alle_{gruppe}", type="tertiary",
                  on_click=setze_alle, args=(gruppe, werte, True))
        k3.button("Keine", key=f"keine_{gruppe}", type="tertiary",
                  on_click=setze_alle, args=(gruppe, werte, False))
        auswahl = []
        with st.container(height=250, border=False):
            for w in werte:
                key = f"f_{gruppe}_{w}"
                st.session_state.setdefault(key, True)
                if st.checkbox(w, key=key):
                    auswahl.append(w)
        return auswahl


def produkt_sortierung(name):
    return (cfg.PRODUKT_REIHENFOLGE.index(name), "") if name in cfg.PRODUKT_REIHENFOLGE \
        else (len(cfg.PRODUKT_REIHENFOLGE), name)


st.markdown('<h1 class="titel">BESTANDSBERICHT</h1>', unsafe_allow_html=True)

produkte = sorted(df_basis["produkt"].unique(), key=produkt_sortierung)
farben = sorted(df_basis["farbe"].unique())
groessen_reihenfolge = cfg.GROESSEN + ["UNBEKANNT"]
groessen = [g for g in groessen_reihenfolge if g in set(df_basis["groesse"])]

with st.container(key="filterbox"):
    c1, c2, c3 = st.columns(3, gap="large")
    sel_produkte = filterspalte(c1, "PRODUKTE", "produkt", produkte)
    sel_farben = filterspalte(c2, "FARBEN", "farbe", farben)
    sel_groessen = filterspalte(c3, "GRÖSSEN", "groesse", groessen)

df = df_basis[df_basis["produkt"].isin(sel_produkte)
              & df_basis["farbe"].isin(sel_farben)
              & df_basis["groesse"].isin(sel_groessen)]

matrix = baue_matrix(df, mengenart)
if not matrix.empty and nullen_ausblenden:
    matrix = matrix[matrix["GESAMT"] != 0]


# --------------------------------------------------------------------------- Tabelle
def zahl(w):
    return "" if pd.isna(w) else f"{int(w):,}".replace(",", ".")


def zelle(w):
    warn = not pd.isna(w) and cfg.WARNSCHWELLE and w <= cfg.WARNSCHWELLE
    return f'<td class="{"warn" if warn else ""}">{zahl(w)}</td>'


def tabelle_html(m):
    gr = [c for c in m.columns if c != "GESAMT"]
    kopf_label = {"ONE SIZE": "ONE<br>SIZE"}
    teile = ['<div class="bestand-wrap"><table class="bestand"><thead><tr>',
             '<th class="l">PRODUKT</th><th class="l">COLOR</th>']
    teile += [f"<th>{kopf_label.get(g, g)}</th>" for g in gr]
    teile.append("<th>GESAMT</th></tr></thead><tbody>")
    for produkt, gruppe in m.groupby(level=0, sort=False):
        for i, ((_, farbe), werte) in enumerate(gruppe.iterrows()):
            name = html.escape(produkt) if i == 0 else ""
            teile.append(f'<tr><td class="l produkt">{name}</td><td class="l farbe">{html.escape(farbe)}</td>')
            teile += [zelle(werte[g]) for g in gr]
            teile.append(f'<td class="gesamt">{zahl(werte["GESAMT"])}</td></tr>')
        if len(gruppe) > 1:
            s = gruppe.sum(numeric_only=True, min_count=1)
            teile.append('<tr class="summe"><td></td><td class="l">SUMME</td>')
            teile += [f"<td>{zahl(s[g])}</td>" for g in gr]
            teile.append(f'<td>{zahl(s["GESAMT"])}</td></tr>')
    s = m.sum(numeric_only=True, min_count=1)
    teile.append('<tr class="total"><td class="l">GESAMT</td><td></td>')
    teile += [f"<td>{zahl(s[g])}</td>" for g in gr]
    teile.append(f'<td>{zahl(s["GESAMT"])}</td></tr></tbody></table></div>')
    return "".join(teile)


if matrix.empty:
    st.info("Keine Daten für die gewählten Filter.")
else:
    st.markdown(
        f'<p class="info">{mengenart_label}: <b>{zahl(matrix["GESAMT"].sum())}</b> Teile · '
        f'{matrix.index.get_level_values(0).nunique()} Produkte · {len(matrix)} Farbvarianten · '
        f'Standort: {", ".join(sel_standorte) or "–"}</p>', unsafe_allow_html=True)
    st.markdown(tabelle_html(matrix), unsafe_allow_html=True)


# --------------------------------------------------------------------------- PDF
filter_text = (f"{mengenart_label} · Standort: {', '.join(sel_standorte) or '–'} · "
               f"Kanal: {', '.join(sel_kanaele) or '–'} · "
               f"Status: {', '.join(STATUS_LABEL.get(s, s) for s in sel_status) or '–'}")
with pdf_platz:
    st.divider()
    st.download_button("📄 PDF exportieren (A4)",
                       data=erstelle_pdf(matrix, stand, filter_text),
                       file_name=f"Bestandsbericht_{stand:%Y-%m-%d_%H%M}.pdf",
                       mime="application/pdf", width="stretch")
