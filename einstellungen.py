"""
Einstellungen für den Bestandsbericht.
Hier kannst du ohne Programmierkenntnisse Namen, Reihenfolgen und Filter anpassen.
"""

# Kurznamen für Produkte ---------------------------------------------------------
# 1. Steht im Shopify-Titel ein Modellcode (z. B. T15, T5, J10, H5, P10), wird
#    automatisch dieser Code als Produktname verwendet.
# 2. Sonst wird der erste passende Suchbegriff aus dieser Liste genommen.
# 3. Passt nichts, wird der volle Shopify-Titel angezeigt.
KURZNAMEN = [
    # (Suchbegriff im Shopify-Titel, Anzeigename)
    ("CHINO JOGGER", "CHINO JOGGER"),
    ("HOODIE", "HOODIE"),
    ("POLO", "POLO"),
    ("LOGO CAP", "LOGO CAP"),
    ("LOGO BAG", "LOGO BAG"),
    ("CARD HOLDER", "CARD HOLDER"),
    ("SCUBA", "SCUBA SWEATSHIRT"),
    ("UNTERZIEHSHIRT", "UNTERZIEHSHIRT"),
    ("SCHWERES COMFORT T-SHIRT", "T15"),
    ("OXFORD HEMD", "OXFORD HEMD"),
    ("JEANS HEMD", "JEANS HEMD"),
]

# Produkte, die nie im Bericht auftauchen sollen (Bundles, Mystery-Boxen usw.).
# Groß-/Kleinschreibung egal, es reicht ein Teil des Titels.
AUSSCHLIESSEN = ["DOPPELPACK", "DREIERPACK", "MYSTERY", "UMTAUSCH"]

# Reihenfolge der Produkte im Bericht. Nicht aufgeführte Produkte folgen alphabetisch.
PRODUKT_REIHENFOLGE = ["T15", "T5", "T25", "T20", "HOODIE", "SCUBA SWEATSHIRT",
                       "CHINO JOGGER", "POLO", "J10", "LOGO CAP", "CARD HOLDER"]

# Größen in dieser Reihenfolge. Alles, was hier nicht steht, landet in "UNBEKANNT".
GROESSEN = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "5XL", "ONE SIZE"]

# Verkaufskanal anhand der SKU-Endung (alles andere = "Shop")
KANAL_SKU_ENDUNGEN = {"_AY": "About You"}

# Voreinstellungen beim Öffnen der Seite
STANDARD_STANDORTE = ["Hauptstandort"]   # leer lassen = alle Standorte
STANDARD_STATUS = ["ACTIVE"]             # ACTIVE, DRAFT, ARCHIVED, UNLISTED

# Werte bis zu dieser Menge werden rot markiert (0 = aus)
WARNSCHWELLE = 5

# Wie oft die Daten automatisch neu aus Shopify geladen werden (in Minuten).
# Mit dem Button "Aktualisieren" geht es jederzeit sofort.
AUTO_AKTUALISIERUNG_MINUTEN = 10
