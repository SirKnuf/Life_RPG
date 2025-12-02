#!/usr/bin/env python3
# start_rpg_sync.py
# Ziel: Zentraler Starter für das Hybrid-RPG-System V4

import sys
import os
import subprocess
import webbrowser
import platform

def start_sync():
    """ Führt die Synchronisations- und Update-Skripte aus und öffnet das HTML-Dashboard. """

    # Überprüfen, ob der Vault-Pfad als Argument übergeben wurde
    if len(sys.argv) < 2:
        print("Fehler: Der Pfad zum Obsidian Vault (Basis-Ordner) fehlt.")
        print("Nutzung: python start_rpg_sync.py /pfad/zu/ihrem/obsidian-vault")
        sys.exit(1)

    # Der Vault-Pfad ist das erste Argument
    vault_path = os.path.abspath(sys.argv[1])

    if not os.path.isdir(vault_path):
        print(f"Fehler: Der Pfad '{vault_path}' ist kein gültiges Verzeichnis.")
        sys.exit(1)

    python_executable = sys.executable
    
    # 1. Execute obsidian_rpg_sync_v4.py (Datenverarbeitung)
    sync_script_path = os.path.join(vault_path, "Code", "obsidian_rpg_sync_v4.py")
    
    print("--- 1/2: Starte Daten-Synchronisation (obsidian_rpg_sync_v4.py) ---")
    try:
        # Wir übergeben den Vault-Pfad an das Sync-Skript
        result = subprocess.run([python_executable, sync_script_path, vault_path], capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"FEHLER bei der Synchronisation (Code 1):\n{e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"FEHLER: Das Skript '{sync_script_path}' wurde nicht gefunden. Stellen Sie sicher, dass es sich im 'Code'-Ordner befindet.")
        sys.exit(1)


    # 2. Execute update_rpg_dashboard_v4.py (JSON-Injektion in HTML)
    update_script_path = os.path.join(vault_path, "Code", "update_rpg_dashboard_v4.py")

    print("--- 2/2: Starte Dashboard-Update (update_rpg_dashboard_v4.py) ---")
    try:
        # Wir übergeben den Vault-Pfad an das Update-Skript
        result = subprocess.run([python_executable, update_script_path, vault_path], capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"FEHLER beim Dashboard-Update (Code 2):\n{e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"FEHLER: Das Skript '{update_script_path}' wurde nicht gefunden. Stellen Sie sicher, dass es sich im 'Code'-Ordner befindet.")
        sys.exit(1)

    print("--- Update abgeschlossen. Öffne Dashboard ---")

    # 3. Open HTML file
    html_path = os.path.join(vault_path, "rpg_dashboard_v4.html")
    
    if os.path.exists(html_path):
        # webbrowser.open_new_tab funktioniert zuverlässig
        webbrowser.open_new_tab(f'file://{os.path.abspath(html_path)}')
        print(f"Dashboard wurde im Browser geöffnet: {os.path.abspath(html_path)}")
    else:
        print(f"WARNUNG: HTML-Datei '{html_path}' nicht gefunden. Bitte stellen Sie sicher, dass sie im Vault-Root-Ordner liegt.")

if __name__ == "__main__":
    start_sync()