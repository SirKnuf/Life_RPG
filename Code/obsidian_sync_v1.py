#!/usr/bin/env python3
# obsidian_sync.py
# Ziel: ETL-Tool für ein Life-RPG Overlay in Obsidian mit zeitbasierter XP-Kalkulation und Tageslog.

import os, json, datetime, re
import sys

# Konstanten für die Skill-Kategorien
SKILL_CATEGORIES = ["Finanziell", "Intellektuell", "Spirituell", "Physisch", "Sozial", "Sprachlich"]
# Basis-XP wird pro 30 Minuten (Basiseinheit) vergeben.
BASE_XP_UNIT_MINUTES = 30 

# Tag-Mapping ohne "_xp" Suffix. Format: "#tag_name": (Skill-Kategorie, BASE XP pro 30min)
ACTION_TAG_MAPPING = {
    "#social": ("Sozial", 2.5),
    "#language": ("Sprachlich", 1.8),
    "#study": ("Intellektuell", 3.0),
    "#finance": ("Finanziell", 4.0),
    "#meditation": ("Spirituell", 1.5),
    "#workout": ("Physisch", 2.0),
    # Allgemeines Tag für Basis-XP, falls kein Skill betroffen ist
    "#task": ("Allgemein", 0.5), 
}

def parse_duration(task_text):
    """
    Parst Dauerangaben wie '(30m)', '(1h 15m)' oder '(90min)' aus dem Aufgabentext 
    und gibt die Gesamtdauer in Minuten zurück.
    """
    # Sucht nach Mustern wie (1h 30m) oder (45m)
    match = re.search(r'\((?:(\d+)\s*h)?\s*(?:(\d+)\s*(?:m|min))?\)', task_text, re.IGNORECASE)
    
    if not match:
        # Standard-Dauer, falls keine Angabe gefunden wird, um minimalen XP-Gewinn zu sichern
        return 5 
    
    hours_str, mins_str = match.groups()
    total_minutes = 0
    
    if hours_str:
        total_minutes += int(hours_str) * 60
    if mins_str:
        total_minutes += int(mins_str)
        
    return total_minutes if total_minutes > 0 else 5 # Mindestens 5 Minuten, falls nur Klammern gefunden

def scan_vault(vault_path):
    """
    Scans the vault, collects raw data, and processes daily logs for time-based activity.
    """
    stats = {
        "skills": {}, "people": {}, "mood_tags": {}, "thought_activity": {},
        # Akkumulierte Stats über den gesamten Vault (Basis für Skill_Levels.md)
        "daily_activities": {
            "skill_time_spent_minutes": {cat: 0 for cat in SKILL_CATEGORIES + ["Allgemein"]}, 
            "person_interactions": {} 
        },
        # Speichert Stats nur für den neuesten Journal-Eintrag (Basis für YYYY-MM-DD.md)
        "latest_daily_stats": {
            "skill_time_spent_minutes": {cat: 0 for cat in SKILL_CATEGORIES + ["Allgemein"]}, 
        },
        "latest_date": None 
    }

    # --- Initialisierung der People-Liste VOR der Journal-Verarbeitung (FIX für UnboundLocalError) ---
    people_dir = os.path.join(vault_path, "02_People")
    known_people = set([f[:-3] for f in os.listdir(people_dir) if f.endswith(".md")] if os.path.isdir(people_dir) else [])
    
    # 1. Journal Parsing (für erledigte Aufgaben, Zeit-Tracking und NEUE TAGESLOGIK)
    journal_dir = os.path.join(vault_path, "07_Journal")
    if os.path.isdir(journal_dir):
        
        # NEU: Bestimme den neuesten Journal-Eintrag
        latest_date_obj = None
        journal_files = [f for f in os.listdir(journal_dir) if f.endswith(".md")]

        for f in journal_files:
            try:
                date_str = f[:-3]
                current_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                if latest_date_obj is None or current_date > latest_date_obj:
                    latest_date_obj = current_date
            except ValueError:
                continue # Ignoriert Dateien, die nicht dem Datumsformat entsprechen
        
        if latest_date_obj:
            stats["latest_date"] = latest_date_obj.strftime("%Y-%m-%d")
        
        # Durchlaufe alle Journal-Dateien (für akkumulierte Stats)
        for f in journal_files:
            try:
                date_str = f[:-3]
                # Stelle sicher, dass das Datum valide ist, um Fehler zu vermeiden
                datetime.datetime.strptime(date_str, "%Y-%m-%d")
                
                is_latest = date_str == stats["latest_date"]

                file_path = os.path.join(journal_dir, f)
                with open(file_path, "r", encoding="utf-8") as infile:
                    content = infile.read()
                        
                completed_tasks = re.findall(r'^- \[x\]\s*(.*)', content, re.MULTILINE)

                for task in completed_tasks:
                    duration_minutes = parse_duration(task)
                        
                    found_xp_tags = [tag for tag in ACTION_TAG_MAPPING if tag in task.lower()]
                    is_specific_skill_task = False
                        
                    for tag in found_xp_tags:
                        skill_cat, _ = ACTION_TAG_MAPPING[tag] # XP-Basis wird in calculate_xp verwendet
                            
                        if skill_cat: 
                            # 1. Akkumulierte Stats (GESAMT) - Für Skill_Levels.md
                            current_total_time = stats["daily_activities"]["skill_time_spent_minutes"].get(skill_cat, 0)
                            stats["daily_activities"]["skill_time_spent_minutes"][skill_cat] = current_total_time + duration_minutes
                            
                            # 2. Tages-Stats (NUR NEUESTE DATEI) - Für YYYY-MM-DD.md
                            if is_latest:
                                current_daily_time = stats["latest_daily_stats"]["skill_time_spent_minutes"].get(skill_cat, 0)
                                stats["latest_daily_stats"]["skill_time_spent_minutes"][skill_cat] = current_daily_time + duration_minutes

                            is_specific_skill_task = True
                        
                    # Behandlung von Aufgaben ohne spezifischen Skill-Tag, aber mit Zeitangabe
                    if not is_specific_skill_task and duration_minutes > 0:
                        # 1. Akkumulierte Stats (GESAMT)
                        stats["daily_activities"]["skill_time_spent_minutes"]["Allgemein"] = \
                            stats["daily_activities"]["skill_time_spent_minutes"].get("Allgemein", 0) + duration_minutes

                        # 2. Tages-Stats (NUR NEUESTE DATEI)
                        if is_latest:
                            stats["latest_daily_stats"]["skill_time_spent_minutes"]["Allgemein"] = \
                                stats["latest_daily_stats"]["skill_time_spent_minutes"].get("Allgemein", 0) + duration_minutes

                    # Personen-Interaktionen suchen (GESAMT)
                    person_links = re.findall(r'\[\[(.*?)\]\]', task)
                    for person_name in person_links:
                        # Nur zählen, wenn die Person im 02_People Ordner existiert
                        if person_name in known_people:
                            stats["daily_activities"]["person_interactions"][person_name] = \
                                stats["daily_activities"]["person_interactions"].get(person_name, 0) + 1

            except (IOError, ValueError) as e:
                # Fängt Fehler beim Lesen oder Parsen des Datums/der Datei ab
                print(f"Fehler beim Lesen oder Parsen der Journal-Datei {f}: {e}")
                continue # Geht zur nächsten Datei über


    # 2. Individuelle Skills sammeln
    skill_dir = os.path.join(vault_path, "03_Skills")
    if os.path.isdir(skill_dir):
        for root, dirs, files in os.walk(skill_dir):
            for f in files:
                if f.endswith(".md"):
                    name = f[:-3]
                    cat = os.path.basename(root)
                    stats["skills"].setdefault(cat, []).append(name)

    # 3. People-Stats sammeln (Nähe-Werte lesen)
    # known_people ist nun bereits definiert
    if os.path.isdir(people_dir):
        for f in os.listdir(people_dir):
            if f.endswith(".md"):
                name = f[:-3]
                try:
                    file_path = os.path.join(people_dir, f)
                    with open(file_path, "r", encoding="utf-8") as infile:
                        content = infile.read()
                        
                    val = 0
                    if "nähe:" in content.lower():
                        try:
                            val_str = content.lower().split("nähe:")[1].splitlines()[0].strip()
                            val = float(val_str)
                        except (ValueError, IndexError):
                            val = 0
                            
                    stats["people"][name] = val
                except IOError as e:
                    print(f"Error reading file {f}: {e}")

    # 4. Emotion Tags sammeln
    mood_dir = os.path.join(vault_path, "04_Emotions/Moodlog")
    if os.path.isdir(mood_dir):
        for f in os.listdir(mood_dir):
            if f.endswith(".md"):
                try:
                    file_path = os.path.join(mood_dir, f)
                    with open(file_path, "r", encoding="utf-8") as infile:
                        content = infile.read()
                        
                    for word in content.split():
                        cleaned_word = word.strip().rstrip('.,!?"\'')
                        if cleaned_word.startswith("#"):
                            stats["mood_tags"][cleaned_word] = stats["mood_tags"].get(cleaned_word, 0) + 1
                except IOError as e:
                    print(f"Error reading file {f}: {e}")

    # 5. Thought Activity sammeln
    thought_dir = os.path.join(vault_path, "05_Thoughts")
    stats["thought_activity"] = {}
    if os.path.isdir(thought_dir):
        for category in ["Daily", "Deep_Thoughts", "Insights"]:
            cat_path = os.path.join(thought_dir, category)
            count = 0
            if os.path.isdir(cat_path):
                count = len([f for f in os.listdir(cat_path) if f.endswith(".md")])
            stats["thought_activity"][category] = count
            
    return stats

def calculate_xp(stats):
    """
    Kalkuliert die XP-Punkte basierend auf den Rohdaten (Zeit) aus Daily Activities.
    Berechnet die Gesamt-XP und die XP für den neuesten Tag.
    """
    xp_rules_passive = {
        "tags": {"#produktiv": 1.5, "#gelesen": 0.8, "#trainiert": 2.0, "#erfolgreich": 1.0},
        "thoughts": {"Deep_Thoughts": 5.0, "Insights": 3.0, "Daily": 0.1}
    }
    
    xp_breakdown = {}
    total_xp = 0.0

    # Passive XP (Gesamt)
    tag_xp = 0.0
    for tag, count in stats["mood_tags"].items():
        if tag in xp_rules_passive["tags"]:
            xp_gained = count * xp_rules_passive["tags"][tag]
            tag_xp += xp_gained
            xp_breakdown[tag] = xp_gained
    total_xp += tag_xp
    xp_breakdown["Gesamt_Tags"] = tag_xp

    thought_xp = 0.0
    for cat, count in stats["thought_activity"].items():
        if cat in xp_rules_passive["thoughts"]:
            xp_gained = count * xp_rules_passive["thoughts"][cat]
            thought_xp += xp_gained
            xp_breakdown[f"05_Thoughts/{cat}"] = xp_gained
    total_xp += thought_xp
    xp_breakdown["Gesamt_Thoughts"] = thought_xp

    # Hilfsfunktion zur Berechnung der XP
    def get_xp_from_time_data(time_data):
        xp_gained = {cat: 0.0 for cat in SKILL_CATEGORIES + ["Allgemein"]}
        skill_base_xp = {}
        for tag, (cat, xp_base) in ACTION_TAG_MAPPING.items():
            if cat not in skill_base_xp or cat == "Allgemein": 
                skill_base_xp[cat] = xp_base
        
        current_active_xp = 0.0
        for skill_cat, total_minutes in time_data.items():
            if total_minutes > 0 and skill_cat in skill_base_xp:
                xp_base_per_30min = skill_base_xp[skill_cat]
                xp = (total_minutes / BASE_XP_UNIT_MINUTES) * xp_base_per_30min
                xp_gained[skill_cat] = xp
                current_active_xp += xp
        return xp_gained, current_active_xp

    # Aktive XP (GESAMT)
    total_skill_xp_gained, total_active_xp = get_xp_from_time_data(stats["daily_activities"]["skill_time_spent_minutes"])
    total_xp += total_active_xp 
    xp_breakdown["Gesamt_Aktiv"] = total_active_xp
    stats["skill_xp_gained"] = total_skill_xp_gained 

    # Aktive XP (NUR HEUTE)
    daily_skill_xp_gained, daily_active_xp = get_xp_from_time_data(stats["latest_daily_stats"]["skill_time_spent_minutes"])
    stats["daily_skill_xp_gained"] = daily_skill_xp_gained

    return total_xp, xp_breakdown

def format_minutes(minutes):
    """Konvertiert Minuten in Stunden und Minuten String (z.B. '2h 15m')."""
    if minutes < 60:
        return f"{minutes}m"
    hours = int(minutes / 60)
    mins = minutes % 60
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"

def write_outputs(vault_path, stats, total_xp, xp_breakdown):
    """
    Schreibt die gesammelten und kalkulierten Daten zurück in den Vault,
    inklusive des neuen Tages-Logs und der aktualisierten Metriken.
    """
    rpg_dir = os.path.join(vault_path, "06_RPG")
    os.makedirs(rpg_dir, exist_ok=True)
    cache_dir = os.path.join(vault_path, "08_System")
    os.makedirs(cache_dir, exist_ok=True)
    
    # --- 1. NEU: Tages-Log (YYYY-MM-DD.md) im Unterordner XP_Log ---
    xp_log_dir = os.path.join(rpg_dir, "XP_Log")
    os.makedirs(xp_log_dir, exist_ok=True) # Stelle sicher, dass der Unterordner existiert

    if stats["latest_date"]:
        # Der Pfad wurde hier zu XP_Log/YYYY-MM-DD.md geändert.
        daily_log_path = os.path.join(xp_log_dir, f"{stats['latest_date']}.md")
        daily_xp = stats.get("daily_skill_xp_gained", {})
        daily_time = stats["latest_daily_stats"]["skill_time_spent_minutes"]
        total_daily_xp = sum(daily_xp.values())

        with open(daily_log_path, "w", encoding="utf-8") as f:
            f.write(f"# Tägliches RPG-Log: {stats['latest_date']}\n\n")
            f.write("## Aktiver XP-Gewinn (Zeitbasiert)\n")
            f.write(f"**Gesamt-XP heute: {total_daily_xp:.2f}**\n\n")
            f.write("| Skill | Zeit (kumuliert) | XP-Gewinn |\n")
            f.write("| :--- | ---: | ---: |\n")
            
            # Sortiere nach höchstem XP-Gewinn des Tages
            sorted_daily_xp = sorted(daily_xp.items(), key=lambda item: item[1], reverse=True)
            
            for skill, xp in sorted_daily_xp:
                if xp > 0:
                    time_spent = daily_time.get(skill, 0)
                    formatted_time = format_minutes(time_spent)
                    f.write(f"| {skill} | {formatted_time} | {xp:.2f} |\n")
            
            f.write("\n---\n\n")
            f.write("## Heutige Metriken\n")
            f.write("### Gedanken\n")
            f.write("Suche im Journal nach täglichen Notizen.\n") 
            f.write("### Interaktionen\n")
            
    # --- 2. Player Stats / Dashboard ---
    with open(os.path.join(rpg_dir, "Player_Stats.md"), "w", encoding="utf-8") as f:
        f.write("# Spieler-Dashboard\n\n")
        f.write("## Skill XP Fortschritt (Primär-Metrik)\n")
        f.write("![[Skill_XP_Breakdown#Skill XP Fortschritt]]\n") 
        f.write("![[Skill_Levels#Akkumulierte Effort-Level (Zeit)]]\n\n") 
        f.write("---")
        f.write(f"\n\n**Gesamte Kumulierte XP (inkl. Passiv): {total_xp:.2f}**\n")
        f.write("*Dient als allgemeiner Fortschritts-Tracker.*\n\n")

        f.write("## Metriken-Übersicht\n")
        f.write("### Beziehungen (Nähe & Interaktionen)\n")
        f.write("![[Relationships_Stats#Relationship Stats]]\n\n")
        f.write("### Gedanken-Aktivität\n")
        f.write("![[Thought_Activity_Stats#Thought Activity Stats]]\n\n")
        
    # --- 3. Skill XP Breakdown (GESAMT XP) ---
    with open(os.path.join(rpg_dir, "Skill_XP_Breakdown.md"), "w", encoding="utf-8") as f:
        f.write("# Skill XP Fortschritt\n\n")
        f.write("Zeigt die kumulierten XP, basierend auf der Zeit, die in Aufgaben verbracht wurde (Gesamt).\n\n")
        f.write("| Skill | Zeit (Minuten) | XP-Gewinn (Zeitbasiert) |\n")
        f.write("| :--- | ---: | ---: |\n")
        
        sorted_skills = sorted(stats.get("skill_xp_gained", {}).items(), 
                               key=lambda item: item[1], reverse=True)
                               
        for skill, xp in sorted_skills:
            if xp > 0:
                time_spent = stats["daily_activities"]["skill_time_spent_minutes"].get(skill, 0)
                f.write(f"| {skill} | {time_spent} | {xp:.2f} |\n")
        f.write("\n\n*Formel: XP = (Total Minuten / 30) * Basis-XP pro 30 Minuten.*\n")


    # --- 4. Skill Levels (Akkumulierte Zeit als 'Effort Level') ---
    with open(os.path.join(rpg_dir, "Skill_Levels.md"), "w", encoding="utf-8") as f:
        f.write("# Skill Levels\n\n")
        f.write("## Akkumulierte Effort-Level (Zeit)\n")
        f.write("Diese Liste verfolgt die Gesamtzeit, die du in jede Skill-Kategorie investiert hast (unabhängig von der Basis-XP).\n\n")
        
        # Stellt sicher, dass nur Kategorien mit mehr als 0 Minuten angezeigt werden
        filtered_effort = {k: v for k, v in stats["daily_activities"]["skill_time_spent_minutes"].items() if v > 0}
        
        sorted_effort = sorted(filtered_effort.items(),
                               key=lambda item: item[1], reverse=True)
        
        f.write("| Skill-Kategorie | Gesamtzeit (Minuten) | Gesamtzeit (Stunden) |\n")
        f.write("| :--- | ---: | ---: |\n")
        
        for cat, minutes in sorted_effort:
            f.write(f"| {cat} | {minutes} | {minutes / 60:.1f}h |\n")
        
        f.write("\n---\n\n")
        f.write("## Individuelle Skills (für zukünftiges Level-Tracking)\n")
        for cat, items in stats["skills"].items():
            if cat != "03_Skills": 
                f.write(f"### {cat}\n")
            for s in items:
                f.write(f"- [[{s}]]\n") 
        
    # --- 5. Relationships & Interaktionen (unverändert) ---
    with open(os.path.join(rpg_dir, "Relationships_Stats.md"), "w", encoding="utf-8") as f:
        f.write("# Relationship Stats\n\n")
        f.write("## Tägliche Interaktionen (Zähler)\n")
        f.write("| Person | Interaktionen (kumuliert) |\n") # 'kumuliert' statt 'seit letztem Scan', da es die Gesamtanzahl ist
        f.write("| :--- | ---: |\n")
        
        sorted_interactions = sorted(stats["daily_activities"]["person_interactions"].items(), 
                                     key=lambda item: item[1], reverse=True)
                                     
        for p, count in sorted_interactions:
            f.write(f"| [[{p}]] | {count}x |\n")
        
        f.write("\n## Näherungswerte (Manuelle Eingabe)\n")
        sorted_people = sorted(stats["people"].items(), key=lambda item: item[1], reverse=True)
        for p, v in sorted_people:
            f.write(f"- [[{p}]] (Nähe {v:.1f})\n") 

    # --- 6. Emotion Tags (unverändert) ---
    with open(os.path.join(rpg_dir, "Emotion_Stats.md"), "w", encoding="utf-8") as f:
        f.write("# Emotion Tags\n\n")
        sorted_tags = sorted(stats["mood_tags"].items(), key=lambda item: item[1], reverse=True)
        for tag, cnt in sorted_tags:
            f.write(f"- {tag}: {cnt}x\n")

    # --- 7. Thought Activity Stats (unverändert) ---
    with open(os.path.join(rpg_dir, "Thought_Activity_Stats.md"), "w", encoding="utf-8") as f:
        f.write("# Thought Activity Stats\n\n")
        sorted_thoughts = sorted(stats.get("thought_activity", {}).items(), key=lambda item: item[1], reverse=True)
        for cat, count in sorted_thoughts:
            f.write(f"- {cat}: {count} Einträge\n")

    # --- 8. Cache (JSON) Output ---
    cache = os.path.join(cache_dir, "life_rpg_data.json")
    stats["total_xp"] = total_xp
    stats["xp_breakdown"] = xp_breakdown
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Fehler: Der Pfad zum Vault fehlt.")
        sys.exit(1)
        
    path = sys.argv[1]
    
    if not os.path.isdir(path):
        print(f"Fehler: Der Pfad '{path}' ist kein gültiges Verzeichnis.")
        sys.exit(1)
        
    try:
        print(f"--- Starte Synchronisation für Vault: {path}")
        stats = scan_vault(path)
        
        # Hilfs-Output, um zu sehen, welcher Tag erkannt wurde
        if stats["latest_date"]:
             print(f"--- Neuestes Journal-Datum erkannt: {stats['latest_date']}")
        else:
             print("--- Kein Journal-Datum erkannt.")
             
        total_xp, breakdown = calculate_xp(stats)
        
        write_outputs(path, stats, total_xp, breakdown)
        print(f"--- Synchronisation abgeschlossen. Gesamte XP: {total_xp:.2f}")
    except Exception as e:
        print(f"Ein kritischer Fehler ist aufgetreten: {e}")
        sys.exit(1)