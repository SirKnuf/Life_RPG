import json
import os
import re

# --- Konfiguration ---
# Pfad zur Obsidian-Datei, aus der die Attribute gelesen werden
ATTRIBUTES_MD_PATH = '01_Core/attributes.md'
# Pfad zur Haupt-JSON-Datei, die Ihre Kerndaten enthält
JSON_DATA_PATH = '08_System/life_rpg_data.json'
# Pfad zur HTML-Datei, die aktualisiert werden soll
HTML_FILE_PATH = 'rpg_dashboard.html'
# Ordner, der die täglichen Journal-Dateien enthält, aus denen die XP berechnet wird
JOURNAL_FOLDER = '07_Journal'

# Markierungskommentare im HTML-Code
START_MARKER = '// <START_JSON_INJECTION>'
END_MARKER = '// <END_JSON_INJECTION>'
JSON_INDENT_SPACES = 4

def parse_attributes_from_md(file_path):
    """
    Liest die Markdown-Datei und extrahiert Attribute im Format:
    [*-] **[Titel]**: [Beschreibung]
    Gibt eine Liste von Dictionaries zurück: [{"title": "...", "description": "..."}]
    """
    attributes_list = []
    
    if not os.path.exists(file_path):
        print(f"Warnung: Attribut-Datei nicht gefunden unter {file_path}. Attribute werden als leer gesetzt.")
        return attributes_list

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Fehler beim Lesen der Attribut-Datei: {e}")
        return attributes_list

    # NEUER REGEX: Akzeptiert sowohl '*' als auch '-' als Listenpunkt am Anfang der Zeile.
    # Muster: ^[*-]\s+\*\*(.+?)\*\*: (.+)$
    attribute_pattern = re.compile(r'^[*-]\s+\*\*(.+?)\*\*: (.+)$', re.MULTILINE)
    
    for match in attribute_pattern.finditer(content):
        title = match.group(1).strip()
        description = match.group(2).strip()
        
        if title and description:
            attributes_list.append({
                "title": title,
                "description": description
            })
            
    print(f"Erfolg: {len(attributes_list)} Attribute aus {ATTRIBUTES_MD_PATH} gelesen.")
    return attributes_list

def calculate_xp_from_journal_files():
    """
    NEU: Geht den Journal-Ordner durch, berechnet die kumulierten XP und gibt sie zurück.
    
    ACHTUNG: DIES IST EINE PLATZHALTER-FUNKTION. Sie müssen die Logik
    anpassen, um das YAML-Frontmatter und die Tags Ihrer tatsächlichen
    Journal-Dateien auszulesen.
    """
    xp_breakdown = {
        "Intellektuell": 0.0,
        "Physisch": 0.0,
        "Finanziell": 0.0,
        "Sozial": 0.0,
        "Gesamt_Tags": 0.0,
        "Gesamt_Thoughts": 0.0,
    }
    
    if not os.path.isdir(JOURNAL_FOLDER):
        print(f"Warnung: Journal-Ordner '{JOURNAL_FOLDER}' nicht gefunden. XP-Berechnung übersprungen.")
        return 0.0, xp_breakdown

    journal_files = [f for f in os.listdir(JOURNAL_FOLDER) if f.endswith('.md')]
    
    # --- BASIS-XP-PLATZHALTER-LOGIK ---
    # Nimmt an, dass jede Journal-Datei einen festen Betrag zur XP beiträgt.
    xp_per_entry = {
        "Intellektuell": 30.0,
        "Physisch": 15.0,
        "Gesamt_Tags": 10.0,
        "Gesamt_Thoughts": 5.0
    }
    
    for _ in journal_files:
        # Hier würden Sie die Journal-Datei öffnen und die Zeiten/Tags auslesen
        
        xp_breakdown['Intellektuell'] += xp_per_entry['Intellektuell']
        xp_breakdown['Physisch'] += xp_per_entry['Physisch']
        xp_breakdown['Gesamt_Tags'] += xp_per_entry['Gesamt_Tags']
        xp_breakdown['Gesamt_Thoughts'] += xp_per_entry['Gesamt_Thoughts']
        
    
    # Gesamtsummen berechnen
    xp_breakdown['Gesamt_Aktiv'] = (
        xp_breakdown['Intellektuell'] + 
        xp_breakdown['Physisch'] + 
        xp_breakdown['Finanziell'] + 
        xp_breakdown['Sozial'] + 
        xp_breakdown['Gesamt_Tags'] + 
        xp_breakdown['Gesamt_Thoughts']
    )
    
    total_xp = xp_breakdown['Gesamt_Aktiv'] # Aktuell: Gesamt-Aktiv = Total XP
    
    print(f"Erfolg: {len(journal_files)} Journal-Dateien gefunden. Gesamt XP berechnet: {total_xp:.2f}")
    return total_xp, xp_breakdown


def update_rpg_dashboard():
    """
    Hauptfunktion: Liest Attribute, berechnet XP, aktualisiert JSON-Daten und injiziert diese in HTML.
    """
    # 1. Attribute aus Markdown lesen
    attributes = parse_attributes_from_md(ATTRIBUTES_MD_PATH)

    # 2. XP aus Journal-Dateien berechnen
    total_xp, xp_breakdown = calculate_xp_from_journal_files()

    # 3. Bestehende JSON-Daten laden
    if not os.path.exists(JSON_DATA_PATH):
        print(f"Fehler: Hauptdaten-JSON nicht gefunden unter {JSON_DATA_PATH}. Erzeuge leere Struktur.")
        data = {} # Erstelle leere Daten, wenn die Datei fehlt
    else:
        try:
            with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Fehler beim Parsen der JSON-Datei: {e}. Verwende leere Struktur.")
            data = {}
    
    # 4. Datenstruktur aktualisieren (XP und Attribute mergen)
    data['total_xp'] = total_xp
    # Füge alle berechneten XP-Breakdown-Werte zu den Hauptdaten hinzu
    data['xp_breakdown'] = {**data.get('xp_breakdown', {}), **xp_breakdown} 
    data['attributes'] = attributes

    # 5. JSON-Daten mit neuen Werten zurückschreiben
    try:
        # ensure_ascii=False stellt sicher, dass Umlaute korrekt geschrieben werden
        with open(JSON_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=JSON_INDENT_SPACES, ensure_ascii=False)
        print(f"Erfolg: JSON-Daten in {JSON_DATA_PATH} mit neuen XP-Werten und Attributen aktualisiert.")
    except Exception as e:
        print(f"Fehler beim Schreiben der JSON-Datei: {e}")
        return
    
    # 6. HTML-Inhalt laden und Injektionsblock erstellen
    if not os.path.exists(HTML_FILE_PATH):
        print(f"Fehler: HTML-Datei nicht gefunden unter {HTML_FILE_PATH}")
        return

    try:
        with open(HTML_FILE_PATH, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Fehler beim Lesen der HTML-Datei: {e}")
        return
    
    # Den JSON-Inhalt als formatierten JavaScript-Code-Block vorbereiten
    json_string = json.dumps(data, indent=JSON_INDENT_SPACES, ensure_ascii=False)

    new_data_block = f"""{START_MARKER}
    const MOCK_DATA = {json_string};
{END_MARKER}"""

    # 7. Ersetzen und Speichern
    try:
        start_index = html_content.index(START_MARKER)
        end_index = html_content.index(END_MARKER) + len(END_MARKER)
    except ValueError:
        print(f"Fehler: Start- oder End-Marker nicht in der HTML-Datei gefunden.")
        return

    # Setze den neuen HTML-Inhalt zusammen
    new_html_content = html_content[:start_index].rstrip() + '\n' + new_data_block + html_content[end_index:]

    try:
        with open(HTML_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(new_html_content)
        print(f"Erfolg: Daten erfolgreich in {HTML_FILE_PATH} injiziert und gespeichert.")
    except Exception as e:
        print(f"Fehler beim Schreiben der HTML-Datei: {e}")


if __name__ == "__main__":
    update_rpg_dashboard()