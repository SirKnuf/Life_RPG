#!/usr/bin/env python3
# obsidian_rpg_sync_v4.py
# Ziel: ETL-Tool für ein Hybrid Life-RPG Overlay (Zeit- und Aufgaben-basiert)

import os, json, datetime, re
import sys

# --- KONSTANTEN: Kombinierte Logik ---
SKILL_CATEGORIES = ["Finanziell", "Intellektuell", "Spirituell", "Physisch", "Sozial", "Sprachlich", "Allgemein"]
BASE_XP_UNIT_MINUTES = 30 
XP_POINTS_MAPPING = {"1p": 1.0, "3p": 3.0, "5p": 5.0, "8p": 8.0} 

# V1: Tag-Mapping für zeitbasierte Aktivitäten (Format: "#tag_name": (Skill-Kategorie, BASE XP pro 30min))
ACTION_TAG_MAPPING_V1 = {
    "#social": ("Sozial", 2.5),
    "#language": ("Sprachlich", 1.8),
    "#study": ("Intellektuell", 3.0),
    "#finance": ("Finanziell", 4.0),
    "#meditation": ("Spirituell", 1.5),
    "#workout": ("Physisch", 2.0),
    "#task": ("Allgemein", 0.5), 
    "#project": ("Allgemein", 0.5), # Neu hinzugefügt
    "#cooking": ("Allgemein", 0.5), # Neu hinzugefügt
}

# Kombiniertes Tag-Mapping für die Kategorisierung von Aufgaben und ToDos
TAG_TO_CATEGORY = {
    "#social": "Sozial",
    "#language": "Sprachlich",
    "#study": "Intellektuell",
    "#finance": "Finanziell",
    "#meditation": "Spirituell",
    "#workout": "Physisch",
    "#task": "Allgemein",
    "#project": "Allgemein", # Neu hinzugefügt
    "#cooking": "Allgemein", # Neu hinzugefügt
}

# NEU: Pfad zur zentralen ToDo-Liste (Relativ zum Vault-Root)
TODO_LIST_PATH = '01_Core/todo_list.md' 


def parse_duration(task_text):
    """ Parst Dauerangaben (1h 30m) und gibt die Gesamtdauer in Minuten zurück. (V1-Logik) """
    match = re.search(r'\((?:(?P<h>\d+)\s*h)?\s*(?P<m>\d+)\s*m(?:in)?\)', task_text, re.IGNORECASE)
    if match:
        hours = int(match.group('h') or 0)
        minutes = int(match.group('m'))
        total_minutes = hours * 60 + minutes
        return total_minutes, match.group(0)
    return 0, None

def parse_task_xp(task_text):
    """ Parst die XP-Punkte (3p) und gibt den XP-Wert zurück. (V3-Logik) """
    match = re.search(r'\((?P<points>\d+)\s*p\)', task_text, re.IGNORECASE)
    
    if match:
        key = f"{match.group('points')}p"
        return XP_POINTS_MAPPING.get(key, 0.0), match.group(0)
    
    return 0.0, None

def get_task_category(task_text):
    """ Bestimmt die Skill-Kategorie einer Aufgabe anhand der Tags. """
    task_lower = task_text.lower()
    
    # Durchsuche alle definierten Tags in TAG_TO_CATEGORY
    for tag, category in TAG_TO_CATEGORY.items():
        if tag in task_lower:
            return category
            
    # Fallback, falls kein spezifisches Tag gefunden wurde
    return "Allgemein"


def scan_vault(vault_path):
    """ Scans the vault for combined time- and task-based activity, open to-dos, and skill structure. """
    
    initial_skill_metrics = {cat: 0.0 for cat in SKILL_CATEGORIES}
    
    stats = {
        "skills": {}, "people": {}, "mood_tags": {}, "thought_activity": {},
        "daily_activities": {
            "skill_minutes_spent": initial_skill_metrics.copy(),  
            "skill_time_xp_gained": initial_skill_metrics.copy(), 
            "skill_task_xp_gained": initial_skill_metrics.copy(), 
            "skill_task_count": initial_skill_metrics.copy(),     
            "person_interactions": {} 
        },
        "open_tasks": {cat: [] for cat in SKILL_CATEGORIES}, 
        "latest_daily_stats": {
            "minutes_spent_total": 0.0,
            "tasks_completed_total": 0,
            "total_xp_gained_today": 0.0,
            "time_xp_today": 0.0,
            "task_xp_today": 0.0
        },
        "latest_date": None 
    }

    people_dir = os.path.join(vault_path, "02_People")
    known_people = set([f[:-3] for f in os.listdir(people_dir) if f.endswith(".md")] if os.path.isdir(people_dir) else [])
    
    
    # 1. Journal Parsing (für erledigte Aufgaben und XP-Zähler)
    journal_dir = os.path.join(vault_path, "07_Journal")
    
    if os.path.isdir(journal_dir):
        
        latest_date_obj = None
        journal_files = [f for f in os.listdir(journal_dir) if f.endswith(".md")]

        for f in journal_files:
            try:
                date_str = f[:-3]
                current_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                if latest_date_obj is None or current_date > latest_date_obj:
                    latest_date_obj = current_date
            except ValueError:
                continue 
        
        if latest_date_obj:
            stats["latest_date"] = latest_date_obj.strftime("%Y-%m-%d")
        
        for f in journal_files:
            try:
                date_str = f[:-3]
                datetime.datetime.strptime(date_str, "%Y-%m-%d")
                
                is_latest = date_str == stats["latest_date"]

                file_path = os.path.join(journal_dir, f)
                with open(file_path, "r", encoding="utf-8") as infile:
                    content = infile.read()
                        
                # KORRIGIERT: Erlaubt führende Leerzeichen/Einrückungen (\s*) vor dem Bindestrich
                completed_tasks = re.findall(r'^\s*- \[x\]\s*(.*)', content, re.MULTILINE)

                if is_latest and completed_tasks:
                    print(f"\n--- DEBUG: {stats['latest_date']} - Gefundene abgeschlossene Aufgaben ({len(completed_tasks)}):")

                for task in completed_tasks:
                    
                    task_xp, task_match = parse_task_xp(task)
                    total_minutes, time_match = parse_duration(task)
                    cat = get_task_category(task)
                    
                    # 1. Priorität: PUNKT-BASIERTE XP (V3)
                    if task_xp > 0.0:
                        
                        stats["daily_activities"]["skill_task_count"][cat] += 1
                        stats["daily_activities"]["skill_task_xp_gained"][cat] += task_xp
                        
                        if is_latest:
                            stats["latest_daily_stats"]["tasks_completed_total"] += 1
                            stats["latest_daily_stats"]["total_xp_gained_today"] += task_xp
                            stats["latest_daily_stats"]["task_xp_today"] += task_xp
                        
                        if is_latest:
                             print(f"  [V3] Task: {task.strip()} -> Cat: {cat}, XP: {task_xp:.2f}")

                    # 2. Fallback: ZEIT-BASIERTE XP (V1) (Nur wenn keine Punkte gefunden wurden)
                    elif total_minutes > 0.0: 
                        
                        # Finde den spezifischen V1-Tag für den XP-Multiplikator
                        found_v1_tags = {tag: action for tag, action in ACTION_TAG_MAPPING_V1.items() if tag in task.lower()}
                        
                        skill_cat_for_xp, base_xp = ACTION_TAG_MAPPING_V1.get("#task", ("Allgemein", 0.5))
                        
                        if found_v1_tags:
                            # Verwende den ersten gefundenen spezifischen Tag für Multiplikator
                            _, (skill_cat_for_xp, base_xp) = list(found_v1_tags.items())[0]

                        xp_gained = (total_minutes / BASE_XP_UNIT_MINUTES) * base_xp
                        
                        # Wir verwenden die durch get_task_category() ermittelte Kategorie 'cat' 
                        # für die Statistik-Speicherung, aber base_xp vom V1 Mapping
                        stats["daily_activities"]["skill_minutes_spent"][cat] += total_minutes
                        stats["daily_activities"]["skill_time_xp_gained"][cat] += xp_gained
                        
                        if is_latest:
                            stats["latest_daily_stats"]["minutes_spent_total"] += total_minutes
                            stats["latest_daily_stats"]["total_xp_gained_today"] += xp_gained
                            stats["latest_daily_stats"]["time_xp_today"] += xp_gained

                        if is_latest:
                             print(f"  [V1] Task: {task.strip()} -> Cat: {cat}, Minutes: {total_minutes}m, XP: {xp_gained:.2f}")

                    elif is_latest and (task_xp == 0.0 and total_minutes == 0.0):
                        print(f"  [!] Task ignoriert: '{task.strip()}' (Weder XP noch Zeit gefunden)")


                    # Personen-Interaktionen suchen (Unverändert)
                    person_links = re.findall(r'\[\[(.*?)\]\]', task)
                    for person_name in person_links:
                        if person_name in known_people:
                            stats["daily_activities"]["person_interactions"][person_name] = \
                                stats["daily_activities"]["person_interactions"].get(person_name, 0) + 1

            except (IOError, ValueError) as e:
                print(f"Fehler beim Lesen oder Parsen der Journal-Datei {f}: {e}")
                continue 
                
    # 2. ToDo-Liste Parsen (NEUE LOGIK) - Unverändert
    todo_path = os.path.join(vault_path, TODO_LIST_PATH)
    if os.path.exists(todo_path):
        try:
            with open(todo_path, "r", encoding="utf-8") as infile:
                content = infile.read()
                
            open_tasks = re.findall(r'^- \[ ]\s*(.*)', content, re.MULTILINE)
            
            for task in open_tasks:
                task_cleaned = task.strip().rstrip('.,;:') 
                category = get_task_category(task_cleaned)
                
                stats["open_tasks"][category].append(task_cleaned)

        except IOError as e:
            print(f"Fehler beim Lesen der ToDo-Liste {todo_path}: {e}")
            
    # 3. Skill Struktur Sammeln (V3-Logik) - Unverändert
    skill_dir = os.path.join(vault_path, "03_Skills")
    if os.path.isdir(skill_dir):
        for root, dirs, files in os.walk(skill_dir):
            for f in files:
                if f.endswith(".md"):
                    name = f[:-3]
                    cat = os.path.basename(root)
                    stats["skills"].setdefault(cat, []).append(name)
    
    # 4. Passive Stats sammeln - Unverändert
    # ... (People, Moods, Thoughts Logik bleibt unverändert) ...

    # --- People Stats ---
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

    # --- Mood Stats ---
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

    # --- Thought Activity Stats ---
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

def calculate_xp_v4(stats):
    """ Kalkuliert die Gesamt-XP, inklusive Aktiver und Passiver XP. (Unverändert) """
    
    xp_rules_passive = {
        "tags": {"#produktiv": 5.0, "#gelesen": 3.0, "#trainiert": 8.0, "#erfolgreich": 10.0},
        "thoughts": {"Deep_Thoughts": 15.0, "Insights": 10.0, "Daily": 1.0}
    }
    
    xp_breakdown = {}
    total_xp = 0.0

    # 1. Passive XP (Gesamt)
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

    # 2. Aktive XP (Gesamt) - SUMME aus Zeit-XP und Task-XP
    total_time_xp = sum(stats["daily_activities"]["skill_time_xp_gained"].values())
    total_task_xp = sum(stats["daily_activities"]["skill_task_xp_gained"].values())
    total_active_xp = total_time_xp + total_task_xp
    
    total_xp += total_active_xp 
    xp_breakdown["Gesamt_Aktiv"] = total_active_xp
    xp_breakdown["Gesamt_Aktiv_Zeit"] = total_time_xp
    xp_breakdown["Gesamt_Aktiv_Aufgabe"] = total_task_xp
    
    # Kombinierte XP pro Skill für die Progress Bars
    combined_skill_xp = {}
    for cat in SKILL_CATEGORIES:
        combined_skill_xp[cat] = stats["daily_activities"]["skill_time_xp_gained"].get(cat, 0.0) + \
                                 stats["daily_activities"]["skill_task_xp_gained"].get(cat, 0.0)

    return total_xp, xp_breakdown, combined_skill_xp

def write_outputs_v4(vault_path, stats, total_xp, xp_breakdown, combined_skill_xp):
    """ Schreibt die gesammelten Daten in den V4 JSON Cache. """
    
    cache_dir = os.path.join(vault_path, "08_System")
    os.makedirs(cache_dir, exist_ok=True)
    
    # --- 1. JSON Cache Output (WICHTIG: Dateiname ist V4) ---
    cache = os.path.join(cache_dir, "life_rpg_data_v4.json")
    
    # Füge die Gesamtergebnisse der Top-Ebene hinzu
    stats["total_xp"] = total_xp
    stats["xp_breakdown"] = xp_breakdown
    stats["skill_xp_gained"] = combined_skill_xp # Kombinierte XP für Progress Bars

    # Schreiben des finalen JSONs
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
        print(f"--- Starte Hybrid-Synchronisation V4 für Vault: {path}")
        stats = scan_vault(path)
        
        if stats["latest_date"]:
             print(f"--- Neuestes Journal-Datum erkannt: {stats['latest_date']}")
        else:
             print("--- Kein Journal-Datum erkannt.")
             
        total_xp, breakdown, combined_skill_xp = calculate_xp_v4(stats)
        
        write_outputs_v4(path, stats, total_xp, breakdown, combined_skill_xp)
        print(f"--- Synchronisation V4 abgeschlossen. Gesamte XP: {total_xp:.2f}")
    except Exception as e:
        print(f"Ein kritischer Fehler ist aufgetreten: {e}")
        sys.exit(1)