import json
import os
import re
import sys

# Markierungskommentare im HTML-Code (Unverändert)
START_MARKER = '// <START_JSON_INJECTION>'
END_MARKER = '// <END_JSON_INJECTION>'
JSON_INDENT_SPACES = 4

def parse_attributes_from_md(file_path):
    """ Liest die Markdown-Datei und extrahiert Attribute. """
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

    attribute_pattern = re.compile(r'^[*-]\s+\*\*(.+?)\*\*: (.+)$', re.MULTILINE)
    
    for match in attribute_pattern.finditer(content):
        title = match.group(1).strip()
        description = match.group(2).strip()
        
        if title and description:
            attributes_list.append({
                "title": title,
                "description": description
            })
            
    return attributes_list


def update_rpg_dashboard(vault_path):
    """ Hauptfunktion: Liest Attribute, lädt die V4 JSON-Daten und injiziert diese in das V4 HTML. """
    
    # 1. Pfade relativ zum Vault Root berechnen
    attributes_md_path = os.path.join(vault_path, '01_Core/attributes.md')
    json_data_path = os.path.join(vault_path, '08_System/life_rpg_data_v4.json')
    html_file_path = os.path.join(vault_path, 'rpg_dashboard_v4.html')

    attributes = parse_attributes_from_md(attributes_md_path)

    # 2. JSON-Daten laden
    if not os.path.exists(json_data_path):
        print(f"Fehler: Hauptdaten-JSON V4 nicht gefunden unter {json_data_path}. Erzeuge leere Struktur.")
        data = {"total_xp": 0.0, "xp_breakdown": {}, "attributes": [], "skill_xp_gained": {}, "skills": {}, 
                "daily_activities": {"skill_minutes_spent": {}, "skill_task_xp_gained": {}}, 
                "latest_daily_stats": {"minutes_spent_total": 0.0, "tasks_completed_total": 0, "total_xp_gained_today": 0.0}} 
    else:
        try:
            with open(json_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Fehler beim Parsen der JSON-Datei: {e}. Verwende leere Struktur.")
            data = {"total_xp": 0.0, "xp_breakdown": {}, "attributes": [], "skill_xp_gained": {}, "skills": {},
                    "daily_activities": {"skill_minutes_spent": {}, "skill_task_xp_gained": {}},
                    "latest_daily_stats": {"minutes_spent_total": 0.0, "tasks_completed_total": 0, "total_xp_gained_today": 0.0}}
    
    data['attributes'] = attributes

    # 3. HTML-Inhalt laden und Injektionsblock erstellen
    if not os.path.exists(html_file_path):
        print(f"Fehler: HTML-Datei V4 nicht gefunden unter {html_file_path}")
        return

    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Fehler beim Lesen der HTML-Datei: {e}")
        return
    
    # JSON-Daten in HTML injizieren
    json_string = json.dumps(data, indent=JSON_INDENT_SPACES, ensure_ascii=False)

    new_data_block = f"""{START_MARKER}
    const MOCK_DATA = {json_string};
{END_MARKER}"""

    # 4. Ersetzen und Speichern
    try:
        start_index = html_content.index(START_MARKER)
        end_index = html_content.index(END_MARKER) + len(END_MARKER)
    except ValueError:
        print(f"Fehler: Start- oder End-Marker nicht in der HTML-Datei V4 gefunden. (Prüfen Sie rpg_dashboard_v4.html)")
        return

    new_html_content = html_content[:start_index].rstrip() + '\n' + new_data_block + html_content[end_index:]

    try:
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(new_html_content)
        print(f"Erfolg: Daten erfolgreich in {html_file_path} injiziert und gespeichert.")
    except Exception as e:
        print(f"Fehler beim Schreiben der HTML-Datei: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Fehler: Der Pfad zum Vault fehlt. (Wird vom start_rpg_sync.py erwartet)")
        sys.exit(1)
        
    vault_path = sys.argv[1]
    
    if not os.path.isdir(vault_path):
        print(f"Fehler: Der Pfad '{vault_path}' ist kein gültiges Verzeichnis.")
        sys.exit(1)

    update_rpg_dashboard(vault_path)