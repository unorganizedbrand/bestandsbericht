# BESTANDSBERICHT – UNORGANIZED BRAND

Live-Bestand aus Shopify als Matrix **Produkt × Farbe × Größe**, mit Filtern, Refresh-Button
und PDF-Export im A4-Hochformat. Läuft auf Streamlit Community Cloud.

- Daten werden automatisch alle 10 Minuten neu geladen, mit **🔄 Aktualisieren** sofort.
- Filter: Produkte, Farben, Größen (je mit *Alle / Keine*), dazu Standort, Kanal (Shop / About You), Produktstatus, Verfügbar vs. Lagerbestand.
- **📄 PDF exportieren** speichert genau die gefilterte Ansicht als A4-Hochformat.
- Die App **liest nur** – sie ändert nichts in Shopify.

## Einrichtung (einmalig, ca. 15 Minuten)

### 1. Shopify-App anlegen (Lesezugriff)
1. Shopify Admin → **Einstellungen → Apps → App-Entwicklung** → *Apps im Dev Dashboard erstellen*
   (oder direkt [dev.shopify.com](https://dev.shopify.com/dashboard)).
2. **App erstellen** → Name z. B. `Bestandsbericht`.
3. Unter **Versionen / Konfiguration → Zugriffsbereiche (Scopes)** eintragen:
   `read_products, read_inventory, read_locations` → Version veröffentlichen.
4. **Startseite → App installieren** → Shop `unorganizedbrand` wählen → installieren.
5. Unter **Einstellungen** der App **Client-ID** und **Client-Secret** kopieren.

> Wichtig: Der Store-Inhaber-Account muss die App anlegen (App und Store in derselben Organisation),
> sonst verweigert Shopify den Token.

### 2. Auf Streamlit veröffentlichen
1. [share.streamlit.io](https://share.streamlit.io) → mit dem GitHub-Konto `unorganizedbrand` anmelden.
2. **Create app** → Repository `unorganizedbrand/bestandsbericht`, Branch `main`, Datei `app.py`.
3. **Advanced settings → Secrets** – Inhalt aus `.streamlit/secrets.toml.example` einfügen und ausfüllen:

```toml
SHOPIFY_STORE = "unorganizedbrand.myshopify.com"
SHOPIFY_CLIENT_ID = "..."
SHOPIFY_CLIENT_SECRET = "..."
APP_PASSWORD = "dein-passwort"
```

4. **Deploy** – fertig. Die URL kannst du als Lesezeichen speichern.

## Anpassen
Alles Wichtige steht in **`einstellungen.py`** (direkt in GitHub bearbeitbar, Streamlit lädt neu):

| Einstellung | Wofür |
|---|---|
| `KURZNAMEN` | Anzeigenamen, z. B. `("CHINO JOGGER", "CITY PANTS")` |
| `AUSSCHLIESSEN` | Bundles/Boxen, die nicht in den Bericht sollen |
| `PRODUKT_REIHENFOLGE` | Reihenfolge der Produkte |
| `KANAL_SKU_ENDUNGEN` | SKU-Endung `_AY` = About You |
| `STANDARD_STANDORTE` / `STANDARD_STATUS` | Voreinstellungen beim Öffnen |
| `WARNSCHWELLE` | Bestände bis zu diesem Wert werden rot |
| `AUTO_AKTUALISIERUNG_MINUTEN` | Automatisches Neuladen |

Produktnamen: Steht ein Modellcode im Titel (T15, T5, J10 …), wird er automatisch verwendet.
Farben kommen aus der Option „Farbe“, Größen aus „Size“/„Größe“. Varianten ohne Bestandsführung
werden ignoriert.

## Lokal starten (optional)
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # ausfüllen
streamlit run app.py
```

## Dateien
- `app.py` – Oberfläche (Filter, Tabelle, Sidebar)
- `shopify_data.py` – Shopify-Abfrage (GraphQL Admin API) und Umbau zur Matrix
- `pdf_export.py` – PDF im A4-Hochformat
- `einstellungen.py` – deine Einstellungen
