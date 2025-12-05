import json
import os
import re
import webbrowser
import sys # <--- STELLEN SIE DIESEN IMPORT SICHER!

# --- Konfiguration ---
JSON_DATA_PATH = '08_System/life_rpg_data_v5.json'
HTML_FILE_PATH = 'rpg_dashboard_v5.html'
START_MARKER = '// <START_JSON_INJECTION>'
END_MARKER = '// <END_JSON_INJECTION>'
JSON_INDENT_SPACES = 4

def update_dashboard(vault_path):
    print("\n[DEBUG] Starte update_dashboard...")
    json_full_path = os.path.join(vault_path, JSON_DATA_PATH)
    html_full_path = os.path.join(vault_path, HTML_FILE_PATH)
    
    if not os.path.exists(json_full_path):
        print(f"[FEHLER] JSON-Quelldatei nicht gefunden: {json_full_path}")
        return False
    if not os.path.exists(html_full_path):
        print(f"[FEHLER] HTML-Zieldatei nicht gefunden: {html_full_path}")
        return False
    
    try:
        # 1. Daten aus der V5 JSON-Datei laden
        with open(json_full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print("[DEBUG] JSON-Daten erfolgreich geladen.")

        # 2. HTML-Inhalt laden
        with open(html_full_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # 3. JSON-String für Injektion vorbereiten
        # Wir verwenden die geladenen Daten 'data', die Sie oben bestätigt haben
        json_string = json.dumps(data, indent=JSON_INDENT_SPACES, ensure_ascii=False)
        
        # Den Block erstellen, der ersetzt werden soll
        new_data_block = f"{START_MARKER}\n    const MOCK_DATA = {json_string};\n{END_MARKER}"
        
        # 4. Marker finden und ersetzen
        start_index = html_content.index(START_MARKER)
        end_index = html_content.index(END_MARKER) + len(END_MARKER)
        
        # Setze den neuen HTML-Inhalt zusammen
        new_html_content = html_content[:start_index].rstrip() + '\n' + new_data_block + html_content[end_index:]

        # 5. Speichern
        with open(html_full_path, 'w', encoding='utf-8') as f:
            f.write(new_html_content)
            
        print("[DEBUG] HTML-Datei erfolgreich mit neuen JSON-Daten aktualisiert.")
        return True
        
    except ValueError:
        print(f"[FEHLER] Start- oder End-Marker ('{START_MARKER}' oder '{END_MARKER}') nicht in der HTML-Datei gefunden.")
        return False
    except Exception as e:
        print(f"[KRITISCHER FEHLER] im update_rpg_dashboard: {e}") 
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Fehler: Der Pfad zum Vault fehlt.")
        sys.exit(1)
        
    vault_path = sys.argv[1]

    if update_dashboard(vault_path):
        dashboard_url = os.path.join("file://", os.path.abspath(os.path.join(vault_path, HTML_FILE_PATH)))
        print("\n--- Update abgeschlossen. Öffne Dashboard ---")
        # webbrowser.open(dashboard_url) # Kann auskommentiert bleiben, falls Sie es manuell öffnen
    else:
        print("--- Update fehlgeschlagen. Siehe Fehlermeldungen oben. ---")