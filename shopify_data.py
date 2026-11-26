"""Bestand aus Shopify laden und in eine Matrix (Produkt × Farbe × Größe) umbauen."""
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

import einstellungen as cfg

API_VERSION_STANDARD = "2026-10"

QUERY = """
query Bestand($cursor: String) {
  productVariants(first: 50, after: $cursor) {
    nodes {
      sku
      selectedOptions { name value }
      product { title status }
      inventoryItem {
        tracked
        inventoryLevels(first: 5) {
          nodes {
            location { name }
            quantities(names: ["available", "on_hand"]) { name quantity }
          }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

FARB_OPTIONEN = {"farbe", "color", "colour"}
GROESSEN_OPTIONEN = {"size", "größe", "grösse", "groesse"}
GROESSEN_ALIAS = {"2XL": "XXL", "XXXL": "3XL", "XXXXL": "4XL", "ONESIZE": "ONE SIZE",
                  "ONE-SIZE": "ONE SIZE", "OS": "ONE SIZE", "DEFAULT TITLE": "ONE SIZE"}
MODELLCODE = re.compile(r"\b([A-Z]{1,2}\d{1,2})\b")


# --------------------------------------------------------------------------- Zugang
def _secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return default


def _store():
    store = str(_secret("SHOPIFY_STORE", "")).strip()
    store = store.replace("https://", "").replace("http://", "").strip("/")
    if store and "." not in store:
        store += ".myshopify.com"
    return store


@st.cache_data(ttl=60 * 60 * 20, show_spinner=False)  # Token gilt 24 h, wir erneuern nach 20 h
def _token_per_client_credentials(store, client_id, client_secret):
    r = requests.post(
        f"https://{store}/admin/oauth/access_token",
        data={"grant_type": "client_credentials",
              "client_id": client_id, "client_secret": client_secret},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Shopify-Token konnte nicht geholt werden ({r.status_code}): {r.text[:300]}")
    return r.json()["access_token"]


def _access_token(store):
    token = _secret("SHOPIFY_ACCESS_TOKEN")
    if token:
        return token
    cid, csecret = _secret("SHOPIFY_CLIENT_ID"), _secret("SHOPIFY_CLIENT_SECRET")
    if not (cid and csecret):
        raise RuntimeError("Zugangsdaten fehlen: SHOPIFY_CLIENT_ID und SHOPIFY_CLIENT_SECRET "
                           "(oder SHOPIFY_ACCESS_TOKEN) in den Streamlit-Secrets eintragen.")
    return _token_per_client_credentials(store, cid, csecret)


def _graphql(store, token, variables):
    version = _secret("SHOPIFY_API_VERSION", API_VERSION_STANDARD)
    url = f"https://{store}/admin/api/{version}/graphql.json"
    for versuch in range(6):
        r = requests.post(url, json={"query": QUERY, "variables": variables},
                          headers={"X-Shopify-Access-Token": token}, timeout=60)
        if r.status_code == 429:
            time.sleep(2 + versuch)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Shopify-API-Fehler {r.status_code}: {r.text[:300]}")
        daten = r.json()
        fehler = daten.get("errors")
        if fehler:
            if any(f.get("extensions", {}).get("code") == "THROTTLED" for f in fehler):
                time.sleep(2 + versuch)
                continue
            raise RuntimeError(f"Shopify-API-Fehler: {fehler}")
        return daten["data"]
    raise RuntimeError("Shopify drosselt gerade die Anfragen – bitte gleich nochmal aktualisieren.")


# --------------------------------------------------------------------------- Laden
@st.cache_data(ttl=cfg.AUTO_AKTUALISIERUNG_MINUTEN * 60, show_spinner=False)
def lade_bestand():
    """Holt alle Varianten inkl. Bestand je Standort. Ergebnis: (DataFrame, Zeitstempel)."""
    store = _store()
    if not store:
        raise RuntimeError("SHOPIFY_STORE fehlt in den Streamlit-Secrets (z. B. unorganizedbrand.myshopify.com).")
    token = _access_token(store)

    varianten, cursor = [], None
    while True:
        data = _graphql(store, token, {"cursor": cursor})["productVariants"]
        varianten.extend(data["nodes"])
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]

    stand = datetime.now(ZoneInfo("Europe/Berlin"))
    return aufbereiten(varianten), stand


def aufbereiten(varianten):
    """Rohdaten aus Shopify → eine Zeile je Variante und Standort."""
    zeilen = []
    for v in varianten:
        titel = (v["product"]["title"] or "").strip()
        if any(w in titel.upper() for w in cfg.AUSSCHLIESSEN):
            continue
        item = v.get("inventoryItem") or {}
        if not item.get("tracked"):
            continue
        optionen = {o["name"].strip().lower(): o["value"].strip() for o in v["selectedOptions"]}
        produkt, rest = kurzname(titel)
        farbe = next((wert for name, wert in optionen.items() if name in FARB_OPTIONEN), None)
        farbe = (farbe or rest or "–").upper()
        groesse = next((wert for name, wert in optionen.items() if name in GROESSEN_OPTIONEN), "ONE SIZE")
        groesse = normalisiere_groesse(groesse)
        sku = v.get("sku") or ""
        kanal = next((k for endung, k in cfg.KANAL_SKU_ENDUNGEN.items()
                      if sku.upper().endswith(endung.upper())), "Shop")

        for lvl in item["inventoryLevels"]["nodes"]:
            mengen = {q["name"]: q["quantity"] for q in lvl["quantities"]}
            zeilen.append({
                "produkt": produkt, "farbe": farbe, "groesse": groesse,
                "titel": titel, "status": v["product"]["status"], "sku": sku, "kanal": kanal,
                "standort": lvl["location"]["name"],
                "verfuegbar": mengen.get("available", 0) or 0,
                "lagerbestand": mengen.get("on_hand", 0) or 0,
            })
    spalten = ["produkt", "farbe", "groesse", "titel", "status", "sku", "kanal",
               "standort", "verfuegbar", "lagerbestand"]
    return pd.DataFrame(zeilen, columns=spalten)


def kurzname(titel):
    """Gibt (Produktname, Resttitel) zurück, z. B. 'CARD HOLDER KHAKI' → ('CARD HOLDER', 'KHAKI')."""
    gross = titel.upper()
    treffer = MODELLCODE.search(gross)
    if treffer:
        return treffer.group(1), ""
    for suchbegriff, name in cfg.KURZNAMEN:
        if suchbegriff.upper() in gross:
            rest = gross.replace(suchbegriff.upper(), "").strip(" -|")
            rest = re.sub(r"^UNORGANIZED\s*", "", rest).strip()
            return name, rest
    return gross, ""


def normalisiere_groesse(groesse):
    g = groesse.strip().upper()
    g = GROESSEN_ALIAS.get(g, g)
    return g if g in cfg.GROESSEN else "UNBEKANNT"


# --------------------------------------------------------------------------- Matrix
def baue_matrix(df, mengenart):
    """DataFrame → Matrix: Zeilen (Produkt, Farbe), Spalten Größen, plus GESAMT.
    Leere Zelle (NaN) = Größe existiert für diese Farbe nicht."""
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot_table(index=["produkt", "farbe"], columns="groesse",
                           values=mengenart, aggfunc="sum")
    reihenfolge = cfg.GROESSEN + ["UNBEKANNT"]
    pivot = pivot[[g for g in reihenfolge if g in pivot.columns]]
    pivot["GESAMT"] = pivot.sum(axis=1, min_count=1).fillna(0)

    def produkt_rang(name):
        return (cfg.PRODUKT_REIHENFOLGE.index(name), "") if name in cfg.PRODUKT_REIHENFOLGE \
            else (len(cfg.PRODUKT_REIHENFOLGE), name)

    pivot = pivot.reset_index()
    pivot["_rang"] = pivot["produkt"].map(produkt_rang)
    pivot = pivot.sort_values(["_rang", "GESAMT", "farbe"], ascending=[True, False, True])
    return pivot.drop(columns="_rang").set_index(["produkt", "farbe"])
