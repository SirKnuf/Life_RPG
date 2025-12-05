#!/usr/bin/env python3
# obsidian_rpg_sync_v5.py
# Ziel: Inkrementelles ETL-Tool für ein Hybrid Life-RPG Overlay mit persistenter XP

import os, json, datetime, re
import sys

# --- KONSTANTEN: Kombinierte Logik ---
SKILL_CATEGORIES = ["Finanziell", "Intellektuell", "Spirituell", "Physisch", "Sozial", "Sprachlich", "Allgemein"]
BASE_XP_UNIT_MINUTES = 30 
XP_POINTS_MAPPING = {"1p": 1.0, "3p": 3.0, "5p": 5.0, "8p": 8.0} 

# V1: Tag-Mapping für zeitbasierte Aktivitäten
ACTION_TAG_MAPPING_V1 = {
    "#social": ("Sozial", 2.5),
    "#language": ("Sprachlich", 1.8),
    "#study": ("Intellektuell", 3.0),
    "#finance": ("Finanziell", 4.0),
    "#meditation": ("Spirituell", 1.5),
    "#workout": ("Physisch", 2.0),
    "#task": ("Allgemein", 0.5), 
    "#project": ("Allgemein", 0.5), 
    "#cooking": ("Allgemein", 0.5), 
}

# Kombiniertes Tag-Mapping für die Kategorisierung
TAG_TO_CATEGORY = {
    "#social": "Sozial",
    "#language": "Sprachlich",
    "#study": "Intellektuell",
    "#finance": "Finanziell",
    "#meditation": "Spirituell",
    "#workout": "Physisch",
    "#task": "Allgemein",
    "#project": "Allgemein", 
    "#cooking": "Allgemein", 
}

# --- PFADE ---
JSON_CACHE_PATH = '08_System/life_rpg_data_v5.json' 
TODO_LIST_PATH = '01_Core/todo_list.md' 
XP_LOG_DIR = '06_RPG/XP_Log'
PLAYER_STATS_PATH = '06_RPG/Player_Stats.md'

# --- HILFSFUNKTIONEN ---
def parse_duration(task_text):
    """ 
    FINAL KORRIGIERT: Parst Dauerangaben (1h 30m), (19min) ODER (19:45min) 
    und gibt die Gesamtdauer in Minuten (als Float) zurück. 
    """
    # 1. Standard (Hh Mm) oder (Mm) format
    match_std = re.search(r'\((?:(?P<h>\d+)\s*h)?\s*(?P<m>\d+)\s*m(?:in)?\)', task_text, re.IGNORECASE)
    if match_std:
        hours = int(match_std.group('h') or 0)
        minutes = int(match_std.group('m'))
        total_minutes = hours * 60 + minutes
        return float(total_minutes), match_std.group(0)
    
    # 2. NEU: M:SS min format (z.B. (19:45min) oder (19:45 min)). 
    # MUSS in einer SEPARATEN Klammer sein, wenn es in Kombination mit KM verwendet wird.
    # WICHTIG: Der Regex wurde auf \s*min abgeändert, um (19:45min) robuster zu erkennen.
    match_mss = re.search(r'\((?P<m_ms>\d+):(?P<s_ms>\d{2})\s*min\)', task_text, re.IGNORECASE)
    if match_mss:
        minutes = int(match_mss.group('m_ms'))
        seconds = int(match_mss.group('s_ms'))
        
        if seconds >= 60: return 0.0, None # Ungültige Zeit
        
        total_minutes = minutes + (seconds / 60.0) 
        return total_minutes, match_mss.group(0)
        
    return 0.0, None 

def parse_task_xp(task_text):
    """ Parst die XP-Punkte (3p) und gibt den XP-Wert zurück. """
    match = re.search(r'\((?P<points>\d+)\s*p\)', task_text, re.IGNORECASE)
    if match:
        key = f"{match.group('points')}p"
        return XP_POINTS_MAPPING.get(key, 0.0), match.group(0)
    return 0.0, None

def parse_kilometers(task_text):
    """ Parst Kilometerangaben wie '(4.5km)' aus dem Aufgabentext. """
    match = re.search(r'\((?P<km>\d+\.?\d*)\s*km\)', task_text, re.IGNORECASE)
    if match:
        return float(match.group('km')), match.group(0)
    return 0.0, None

def parse_sallyup_time(task_text):
    """ Parst die Zeitangabe für Sally Up (Minuten:Sekunden) aus dem Aufgabentext. """
    # Dies dient nur zur Speicherung der Bestzeit und ist NICHT für die XP-Dauer zuständig
    match = re.search(r'\((?P<m>\d+):(?P<s>\d{2})\s*min\)', task_text, re.IGNORECASE)
    if match:
        minutes = int(match.group('m'))
        seconds = int(match.group('s'))
        return float(f"{minutes}.{seconds:02d}"), (minutes * 60 + seconds)
    return 0.0, 0

def get_task_category(task_text):
    """ Bestimmt die Skill-Kategorie einer Aufgabe anhand der Tags. """
    task_lower = task_text.lower()
    for tag, category in TAG_TO_CATEGORY.items():
        if tag in task_lower:
            return category
    return "Allgemein"

# --- Laden des persistenten Status (unverändert) ---
def load_persistent_state(vault_path):
    cache_path = os.path.join(vault_path, JSON_CACHE_PATH)
    initial_skill_metrics = {cat: 0.0 for cat in SKILL_CATEGORIES}
    state = {
        "cumulative_total_xp": 0.0,
        "cumulative_skill_xp": initial_skill_metrics.copy(),
        "last_processed_date": "1970-01-01", 
        "run_total_km": 0.0,
        "run_total_minutes": 0.0,
    }
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                state["cumulative_total_xp"] = data.get("total_xp", 0.0)
                state["cumulative_skill_xp"] = data.get("skill_xp_gained", initial_skill_metrics.copy())
                state["last_processed_date"] = data.get("last_processed_date", "1970-01-01") 
                state["run_total_km"] = data.get("run_total_km", 0.0)
                state["run_total_minutes"] = data.get("run_total_minutes", 0.0)
        except (IOError, json.JSONDecodeError) as e:
            print(f"WARNUNG: Fehler beim Laden des Cache ({e}). Starte mit 0 XP.")
    for cat in SKILL_CATEGORIES:
        state["cumulative_skill_xp"].setdefault(cat, 0.0)
    return state

# --- KERN-SCAN FUNKTION (mit Debug-Ausgabe) ---
def scan_vault(vault_path, persistent_state):
    
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
        "latest_date": None,
        "cumulative_total_xp": persistent_state["cumulative_total_xp"],
        "cumulative_skill_xp": persistent_state["cumulative_skill_xp"].copy(),
        "run_total_km": persistent_state["run_total_km"],         
        "run_total_minutes": persistent_state["run_total_minutes"],  
        "sallyup_latest_time": 0.0,                               
    }
    
    start_date_str = persistent_state["last_processed_date"]
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()

    people_dir = os.path.join(vault_path, "02_People")
    known_people = set([f[:-3] for f in os.listdir(people_dir) if f.endswith(".md")] if os.path.isdir(people_dir) else [])
    
    # 1. Journal Parsing (INKREMENTELL)
    journal_dir = os.path.join(vault_path, "07_Journal")
    
    if os.path.isdir(journal_dir):
        
        latest_date_obj = None
        journal_files = sorted([f for f in os.listdir(journal_dir) if f.endswith(".md")])
        
        # A. Neuestes Datum finden
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
            
        
        # B. Dateien verarbeiten
        for f in journal_files:
            try:
                date_str = f[:-3]
                current_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                
                is_latest = date_str == stats["latest_date"]
                should_update_cumulative = current_date > start_date 
                
                if current_date < start_date and not is_latest: 
                    continue 

                if is_latest:
                    stats["latest_daily_stats"] = {
                        "minutes_spent_total": 0.0, "tasks_completed_total": 0, "total_xp_gained_today": 0.0,
                        "time_xp_today": 0.0, "task_xp_today": 0.0
                    }
                    stats["daily_activities"]["skill_minutes_spent"] = initial_skill_metrics.copy()
                    stats["daily_activities"]["skill_task_count"] = initial_skill_metrics.copy()
                    stats["daily_activities"]["skill_task_xp_gained"] = initial_skill_metrics.copy()
                    
                
                # Lokale Variablen für die Verarbeitung der aktuellen Datei
                daily_active_xp = 0.0 
                daily_active_xp_by_skill = initial_skill_metrics.copy()
                daily_minutes_by_skill = initial_skill_metrics.copy()
                daily_task_count = initial_skill_metrics.copy() 

                file_path = os.path.join(journal_dir, f)
                with open(file_path, "r", encoding="utf-8") as infile:
                    content = infile.read()
                        
                completed_tasks = re.findall(r'^\s*- \[x\]\s*(.*)', content, re.MULTILINE)

                for task in completed_tasks:
                    
                    task_xp, _ = parse_task_xp(task)
                    total_minutes, _ = parse_duration(task) 
                    cat = get_task_category(task)
                    
                    xp_to_add = 0.0

                    # --- 1. XP-Berechnung & Aktive Stats ---
                    if task_xp > 0.0:
                        xp_to_add = task_xp
                        if is_latest:
                            stats["latest_daily_stats"]["task_xp_today"] += xp_to_add
                    elif total_minutes > 0.0: 
                        # Logik für Zeit-XP
                        found_v1_tags = {tag: action for tag, action in ACTION_TAG_MAPPING_V1.items() if tag in task.lower()}
                        _, base_xp = ACTION_TAG_MAPPING_V1.get("#task", ("Allgemein", 0.5))
                        if found_v1_tags:
                            _, (_, base_xp) = list(found_v1_tags.items())[0]
                        xp_gained = (total_minutes / BASE_XP_UNIT_MINUTES) * base_xp
                        
                        xp_to_add = xp_gained
                        
                        if is_latest:
                            stats["latest_daily_stats"]["minutes_spent_total"] += total_minutes
                            stats["latest_daily_stats"]["time_xp_today"] += xp_to_add
                            stats["daily_activities"]["skill_minutes_spent"][cat] += total_minutes 
                            
                    # ----------------------------------------------------------------------------------
                    # --- NEUE LOGIK FÜR RUN & SALLYUP METRIKEN ---
                    # ----------------------------------------------------------------------------------
                    
                    # **A. #run Auswertung**
                    if "#run" in task.lower():
                        kilometers, _ = parse_kilometers(task)
                        
                        # DEBUG-AUSGABE: Prüfen, ob die Daten erkannt wurden
                        # BITTE DIESE ZEILE LESEN, WENN SIE DAS SKRIPT AUSFÜHREN!
                        print(f"[DEBUG RUN PARSE] Task: '{task}' | KM: {kilometers} | Min: {total_minutes:.2f} | Update: {should_update_cumulative}")
                        
                        if should_update_cumulative and kilometers > 0.0:
                            stats["run_total_km"] += kilometers
                            stats["run_total_minutes"] += total_minutes 
                        
                    # **B. #sallyup Auswertung**
                    if "#sallyup" in task.lower():
                        time_m_ss, total_seconds = parse_sallyup_time(task) 
                        
                        if is_latest and time_m_ss > 0.0:
                            if time_m_ss > stats["sallyup_latest_time"]:
                                stats["sallyup_latest_time"] = time_m_ss 

                    # ----------------------------------------------------------------------------------
                    # --- ENDE NEUE LOGIK ---
                    # ----------------------------------------------------------------------------------
                            
                    # --- 2. Akkumulation der täglichen Metriken (Lokal) ---
                    if xp_to_add > 0.0:
                        daily_active_xp += xp_to_add
                        daily_active_xp_by_skill[cat] += xp_to_add
                        
                        if is_latest:
                            stats["latest_daily_stats"]["total_xp_gained_today"] += xp_to_add
                            stats["daily_activities"]["skill_task_xp_gained"][cat] += xp_to_add 
                            
                    if is_latest:
                         stats["latest_daily_stats"]["tasks_completed_total"] += 1
                         stats["daily_activities"]["skill_task_count"][cat] += 1
                    
                    # Personen-Interaktionen suchen (Unverändert)
                    person_links = re.findall(r'\[\[(.*?)\]\]', task)
                    for person_name in person_links:
                        if person_name in known_people:
                            stats["daily_activities"]["person_interactions"][person_name] = \
                                stats["daily_activities"]["person_interactions"].get(person_name, 0) + 1
                    
                    
                    # --- 3. KUMULATIVE UPDATES (NUR wenn die Datei NEU ist) ---
                    if should_update_cumulative and xp_to_add > 0.0:
                        stats["cumulative_skill_xp"][cat] += xp_to_add
                        stats["cumulative_total_xp"] += xp_to_add
                        
                # Protokolliere die TÄGLICHEN aktiven XP im XP_Log Ordner (NUR FÜR NEUE TAGE)
                if should_update_cumulative and daily_active_xp > 0.0:
                    write_xp_log(vault_path, date_str, daily_active_xp, daily_active_xp_by_skill, daily_minutes_by_skill)
                    
            except (IOError, ValueError) as e:
                print(f"Fehler beim Lesen oder Parsen der Journal-Datei {f}: {e}")
                continue 
                
    # 2. ToDo-Liste Parsen (Unverändert)
    todo_path = os.path.join(vault_path, TODO_LIST_PATH)
    if os.path.exists(todo_path):
        try:
            with open(todo_path, "r", encoding="utf-8") as infile:
                content = infile.read()
                
            open_tasks = re.findall(r'^\s*- \[ ]\s*(.*)', content, re.MULTILINE)
            
            for task in open_tasks:
                task_cleaned = task.strip().rstrip('.,;:') 
                category = get_task_category(task_cleaned)
                
                stats["open_tasks"][category].append(task_cleaned)

        except IOError as e:
            print(f"Fehler beim Lesen der ToDo-Liste {todo_path}: {e}")
            
    # 3. Passive Stats sammeln (unverändert)
    
    people_dir = os.path.join(vault_path, "02_People")
    if os.path.isdir(people_dir):
        for f in os.listdir(people_dir):
            if f.endswith(".md"):
                person_name = f[:-3]
                stats["people"][person_name] = stats["people"].get(person_name, 1.0) 

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
    else:
        print(f"WARNUNG: Moodlog-Ordner nicht gefunden unter {mood_dir}. Passive Tag-Stats werden 0 sein.")

    thought_dir = os.path.join(vault_path, "05_Thoughts")
    stats["thought_activity"] = {}
    if os.path.isdir(thought_dir):
        for category in ["Daily", "Deep_Thoughts", "Erkenntnisse"]: 
            cat_path = os.path.join(thought_dir, category)
            count = 0
            if os.path.isdir(cat_path):
                count = len([f for f in os.listdir(cat_path) if f.endswith(".md")])
            stats["thought_activity"][category] = count

    return stats


def calculate_xp_v5(stats):
    """ Kalkuliert die Passive XP und die XP-Breakdown. (unverändert) """
    xp_rules_passive = {
        "tags": {"#produktiv": 5.0, "#gelesen": 3.0, "#trainiert": 8.0, "#erfolgreich": 10.0},
        "thoughts": {"Daily": 1.0, "Deep_Thoughts": 15.0, "Erkenntnisse": 10.0}
    }
    xp_breakdown = {}
    total_xp = stats["cumulative_total_xp"] 
    tag_xp = 0.0
    for tag, count in stats["mood_tags"].items():
        if tag in xp_rules_passive["tags"]:
            tag_xp += count * xp_rules_passive["tags"][tag]
    thought_xp = 0.0
    for cat, count in stats["thought_activity"].items():
        if cat in xp_rules_passive["thoughts"]:
            thought_xp += count * xp_rules_passive["thoughts"][cat]

    xp_breakdown["Gesamt_Tags"] = tag_xp
    xp_breakdown["Gesamt_Thoughts"] = thought_xp
    xp_breakdown["Gesamt_Aktiv"] = total_xp 
    xp_breakdown["Gesamt_Aktiv_Zeit"] = stats["latest_daily_stats"]["time_xp_today"] 
    xp_breakdown["Gesamt_Aktiv_Aufgabe"] = stats["latest_daily_stats"]["task_xp_today"] 
    
    combined_skill_xp = stats["cumulative_skill_xp"] 
    return total_xp, xp_breakdown, combined_skill_xp

def calculate_level_data(xp):
    """ Berechnet Level, basierend auf der Gesamt-XP. (unverändert) """
    def get_xp_required(level):
        if level <= 1: return 100
        return 100 * (1.5 ** (level - 1))

    current_level = 1
    xp_at_start_of_current_level = 0
    xp_required_for_next_level = get_xp_required(1)

    while xp >= xp_at_start_of_current_level + xp_required_for_next_level:
        xp_at_start_of_current_level += xp_required_for_next_level
        current_level += 1
        xp_required_for_next_level = get_xp_required(current_level)
    
    return {
        "level": current_level,
        "xp_since_last_level": xp - xp_at_start_of_current_level,
        "xp_required": xp_required_for_next_level
    }

def write_xp_log(vault_path, date_str, daily_xp, daily_xp_by_skill, daily_minutes_by_skill):
    """ Schreibt einen Markdown-Log der neu verdienten XP für den Tag. (unverändert) """
    log_dir = os.path.join(vault_path, XP_LOG_DIR)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{date_str}.md")
    
    content = f"# XP-Log: {date_str}\n\n"
    content += f"## Gesamte aktive XP: {daily_xp:.2f}\n\n"
    content += "### XP pro Skill\n"
    
    sorted_skills = sorted(daily_xp_by_skill.items(), key=lambda item: item[1], reverse=True)
    for skill, xp in sorted_skills:
        if xp > 0.0:
            minutes = daily_minutes_by_skill.get(skill, 0)
            content += f"- **{skill}**: {xp:.2f} XP ({minutes} Minuten)\n"
            
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"--- XP-Log für {date_str} geschrieben: {daily_xp:.2f} XP")
    except IOError as e:
        print(f"Fehler beim Schreiben des XP-Logs: {e}")

def write_player_stats(vault_path, total_xp, level_data):
    """ Aktualisiert die Player_Stats.md mit den neuen Gesamtwerten. (unverändert) """
    stats_path = os.path.join(vault_path, PLAYER_STATS_PATH)
    
    content = f"# Spieler-Status (Kumulativ)\n\n"
    content += f"## Level & XP\n"
    content += f"- **Aktuelles Level**: {level_data['level']}\n"
    content += f"- **Gesamte XP**: {total_xp:.2f}\n"
    content += f"- **XP bis Level {level_data['level'] + 1}**: {level_data['xp_since_last_level']:.2f} / {level_data['xp_required']:.2f}\n"
    
    try:
        with open(stats_path, "w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        print(f"Fehler beim Schreiben von Player_Stats.md: {e}")

def write_outputs_v5(vault_path, stats, total_xp, xp_breakdown, combined_skill_xp):
    """ Schreibt die gesammelten Daten in den V5 JSON Cache und Player_Stats.md. (unverändert) """
    
    cache_dir = os.path.join(vault_path, "08_System")
    os.makedirs(cache_dir, exist_ok=True)
    cache = os.path.join(cache_dir, os.path.basename(JSON_CACHE_PATH))
    
    stats["total_xp"] = total_xp
    stats["xp_breakdown"] = xp_breakdown
    stats["skill_xp_gained"] = combined_skill_xp 
    
    stats["run_total_km"] = stats.get("run_total_km", 0.0)
    stats["run_total_minutes"] = stats.get("run_total_minutes", 0.0) 
    stats["sallyup_latest_time"] = stats.get("sallyup_latest_time", 0.0)
    
    level_data = calculate_level_data(total_xp)
    stats["level_data"] = level_data

    if stats["latest_date"]:
        stats["last_processed_date"] = stats["latest_date"]

    with open(cache, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    write_player_stats(vault_path, total_xp, level_data)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Fehler: Der Pfad zum Vault fehlt.")
        sys.exit(1)
        
    path = sys.argv[1]
    
    if not os.path.isdir(path):
        print(f"Fehler: Der Pfad '{path}' ist kein gültiges Verzeichnis.")
        sys.exit(1)
        
    try:
        print(f"--- Starte Hybrid-Synchronisation V5 für Vault: {path}")
        
        persistent_state = load_persistent_state(path)
        print(f"--- Letzter verarbeiteter Tag: {persistent_state['last_processed_date']}")

        stats = scan_vault(path, persistent_state)
        
        if stats["latest_date"]:
             print(f"--- Neuestes Journal-Datum erkannt: {stats['latest_date']}")
        else:
             print("--- Kein Journal-Datum erkannt.")
             
        total_xp, breakdown, combined_skill_xp = calculate_xp_v5(stats)
        
        write_outputs_v5(path, stats, total_xp, breakdown, combined_skill_xp)
        print(f"--- Synchronisation V5 abgeschlossen. Kumulierte XP: {total_xp:.2f}")
    except Exception as e:
        print(f"Ein kritischer Fehler ist aufgetreten: {e}")
        sys.exit(1)