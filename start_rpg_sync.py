import os
import sys  # <--- DIESE ZEILE WAR VERMUTLICH FEHLEND!

# --- Konfiguration ---
# Referenziert die V5-Skripte
SYNC_SCRIPT = 'obsidian_rpg_sync_v5.py'
UPDATE_SCRIPT = 'update_rpg_dashboard_v5.py'

if __name__ == "__main__":
    # Wenn sys.argv verwendet wird, muss sys importiert sein.
    if len(sys.argv) < 2: 
        print("Fehler: Der Pfad zum Vault fehlt.")
        sys.exit(1) # Auch sys.exit() erfordert den Import von sys
        
    vault_path = sys.argv[1]
    code_path = os.path.join(vault_path, "Code")
    
    sync_path = os.path.join(code_path, SYNC_SCRIPT)
    update_path = os.path.join(code_path, UPDATE_SCRIPT)
    
    if not os.path.exists(sync_path):
        print(f"Fehler: Sync-Skript nicht gefunden unter {sync_path}")
        sys.exit(1)
        
    if not os.path.exists(update_path):
        print(f"Fehler: Update-Skript nicht gefunden unter {update_path}")
        sys.exit(1)

    try:
        # 1. Daten-Synchronisation starten
        print(f"--- 1/2: Starte Daten-Synchronisation ({SYNC_SCRIPT}) ---")
        # Wichtig: Wir verwenden das Python-Executable, um das Skript im Child Process zu starten
        os.system(f"python \"{sync_path}\" \"{vault_path}\"")
        
        # 2. Dashboard-Update starten
        print(f"\n--- 2/2: Starte Dashboard-Update ({UPDATE_SCRIPT}) ---")
        os.system(f"python \"{update_path}\" \"{vault_path}\"")
        
    except Exception as e:
        print(f"Ein kritischer Fehler ist aufgetreten: {e}")
        sys.exit(1)