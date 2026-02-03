#!/usr/bin/env python3
# obsidian_rpg_sync_v5.py

import os, json, datetime, re, sys

# --- KONSTANTEN & PFADE ---
RULES_PATH = '01_Core/XP_Calculation.md'
TODO_LIST_PATH = '01_Core/todo_list.md'
JSON_CACHE_PATH = '08_System/life_rpg_data_v5.json' 
HTML_DASHBOARD_PATH = 'rpg_dashboard_v5.html'
START_MARKER = '// <START_JSON_INJECTION>'
END_MARKER = '// <END_JSON_INJECTION>'
JSON_INDENT_SPACES = 4
JOURNAL_DIR_NAME = '07_Journal'
BASE_XP_UNIT_MINUTES = 30 
XP_POINTS_MAPPING = {"1p": 1.0, "3p": 3.0, "5p": 5.0, "8p": 8.0}

# --- 1. REGELN LADEN ---
def load_rpg_rules(vault_path):
    rules_file = os.path.join(vault_path, RULES_PATH)
    rules = {}
    categories = set(["Allgemein", "Finanziell", "Intellektuell", "Spirituell", "Physisch", "Sozial", "Sprachlich"])
    if os.path.exists(rules_file):
        with open(rules_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith('|') and not any(x in line for x in [':---', 'Basis_XP']):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 3:
                        tag, cat = parts[0].lower(), parts[1]
                        try: xp = float(parts[2])
                        except: xp = 0.5
                        rules[tag] = {"category": cat, "base_xp": xp}
                        categories.add(cat)
    return rules, list(categories)

# --- 2. PARSE-FUNKTIONEN (Robust) ---
def parse_duration(task_text):
    match_std = re.search(r'\((?:(?P<h>\d+)\s*h)?\s*(?P<m>\d+)\s*m(?:in)?\)', task_text, re.IGNORECASE)
    if match_std:
        return float(int(match_std.group('h') or 0) * 60 + int(match_std.group('m')))
    match_mss = re.search(r'\((?P<m_ms>\d+):(?P<s_ms>\d{2})\s*min\)', task_text, re.IGNORECASE)
    if match_mss:
        return int(match_mss.group('m_ms')) + (int(match_mss.group('s_ms')) / 60.0)
    return 0.0

def parse_kilometers(task_text):
    match = re.search(r'\((?P<km>\d+\.?\d*)\s*km\)', task_text, re.IGNORECASE)
    return float(match.group('km')) if match else 0.0

def parse_sallyup_time(task_text):
    # Erkennt (3:40 min) oder (3:40min)
    match = re.search(r'\((?P<m>\d+):(?P<s>\d{2})\s*min\)', task_text, re.IGNORECASE)
    if match:
        # Rückgabe als Float für den Vergleich (z.B. 3.66 Minuten)
        return int(match.group('m')) + (int(match.group('s')) / 60.0)
    return 0.0

def get_task_category(task_text, tag_rules):
    for tag, rule in tag_rules.items():
        if tag in task_text.lower():
            return rule["category"]
    return "Allgemein"

# --- 3. KERN-SCAN (Full Scan Modus) ---
def scan_vault(vault_path):
    TAG_RULES, SKILL_CATEGORIES = load_rpg_rules(vault_path)
    
    # Variablen für den Full-Scan (Reset bei jedem Start)
    total_xp = 0.0
    skill_xp = {cat: 0.0 for cat in SKILL_CATEGORIES}
    run_total_km = 0.0
    run_total_min = 0.0
    sallyup_best_min = 0.0
    
    stats = {
        "open_tasks": {cat: [] for cat in SKILL_CATEGORIES},
        "latest_daily_stats": {
            "total_xp_today": 0.0, "tasks_today": 0, 
            "minutes_today": 0.0, "daily_breakdown": {cat: 0.0 for cat in SKILL_CATEGORIES}
        },
        "latest_date": None
    }

    journal_dir = os.path.join(vault_path, JOURNAL_DIR_NAME)
    all_files = []
    for root, _, filenames in os.walk(journal_dir):
        for f in filenames:
            if f.endswith(".md") and re.match(r'\d{4}-\d{2}-\d{2}', f):
                all_files.append((f[:-3], os.path.join(root, f)))
    all_files.sort()

    if all_files:
        stats["latest_date"] = all_files[-1][0]
        
        for d_str, f_path in all_files:
            is_latest = (d_str == stats["latest_date"])
            with open(f_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Abgeschlossene Tasks einlesen
            completed_tasks = re.findall(r'^\s*- \[x\]\s*(.*)', content, re.MULTILINE)
            
            for task in completed_tasks:
                xp_match = re.search(r'\((?P<p>\d+)p\)', task)
                xp_val = XP_POINTS_MAPPING.get(f"{xp_match.group('p')}p", 0.0) if xp_match else 0.0
                dur = parse_duration(task)
                cat = get_task_category(task, TAG_RULES)

                # Zeitbasierte XP
                if xp_val == 0.0 and dur > 0:
                    for tag, rule in TAG_RULES.items():
                        if tag in task.lower():
                            xp_val = (dur / BASE_XP_UNIT_MINUTES) * rule["base_xp"]
                            break
                
                # Kumulative Metriken
                total_xp += xp_val
                if cat in skill_xp: skill_xp[cat] += xp_val
                
                if "#run" in task.lower():
                    run_total_km += parse_kilometers(task)
                    run_total_min += dur
                
                
                if "#sallyup" in task.lower():
                    s_time = parse_sallyup_time(task)
                    if s_time:
                        if s_time > sallyup_best_min:
                            sallyup_best_min = s_time
                            print(f"[DEBUG] Neuer All-Time Rekord gefunden: {s_time} Min")
                
                # Heutige Statistik
                if is_latest:
                    stats["latest_daily_stats"]["tasks_today"] += 1
                    stats["latest_daily_stats"]["total_xp_today"] += xp_val
                    stats["latest_daily_stats"]["minutes_today"] += dur
                    stats["latest_daily_stats"]["daily_breakdown"][cat] += xp_val
                    stats["latest_daily_stats"].setdefault("completed_today", []).append(task)

    # ToDo-Liste (Offene Quests)
    todo_file = os.path.join(vault_path, TODO_LIST_PATH)
    if os.path.exists(todo_file):
        with open(todo_file, "r", encoding="utf-8") as f:
            for t in re.findall(r'^\s*- \[ \]\s*(.*)', f.read(), re.MULTILINE):
                cat = get_task_category(t, TAG_RULES)
                stats["open_tasks"].setdefault(cat, []).append(t.strip())

    # Finales JSON
    output = {
        "total_xp": round(total_xp, 2),
        "skill_xp_gained": {k: round(v, 2) for k, v in skill_xp.items()},
        "run_metrics": {
            "total_km": round(run_total_km, 2),
            "total_minutes": round(run_total_min, 1)
        },
        "sallyup_best_time": sallyup_best_min,
        "last_processed_date": stats["latest_date"],
        "open_tasks": stats["open_tasks"],
        "latest_daily_stats": stats["latest_daily_stats"]
    }
    
    with open(os.path.join(vault_path, JSON_CACHE_PATH), "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    update_dashboard_html(vault_path, output)
    
    print(f"--- Full Sync v5 ---")
    print(f"Heute erledigt: {stats['latest_daily_stats']['tasks_today']} Aufgaben")
    print(f"Laufen Gesamt: {output['run_metrics']['total_km']} km")
    print(f"SallyUp Bestzeit: {output['sallyup_best_time']} min")

def update_dashboard_html(vault_path, data):
    html_full_path = os.path.join(vault_path, HTML_DASHBOARD_PATH)
    if not os.path.exists(html_full_path):
        print(f"[WARN] Dashboard-HTML nicht gefunden: {html_full_path}")
        return

    try:
        with open(html_full_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        json_string = json.dumps(data, indent=JSON_INDENT_SPACES, ensure_ascii=False)
        new_data_block = f"{START_MARKER}\n    const MOCK_DATA = {json_string};\n{END_MARKER}"

        start_index = html_content.index(START_MARKER)
        end_index = html_content.index(END_MARKER) + len(END_MARKER)

        new_html_content = html_content[:start_index].rstrip() + "\n" + new_data_block + html_content[end_index:]

        with open(html_full_path, "w", encoding="utf-8") as f:
            f.write(new_html_content)

        print("[DEBUG] Dashboard-HTML mit aktuellen JSON-Daten aktualisiert.")
    except ValueError:
        print(f"[WARN] Marker für JSON-Injektion in {HTML_DASHBOARD_PATH} nicht gefunden.")
    except Exception as e:
        print(f"[WARN] Dashboard-Update fehlgeschlagen: {e}")

if __name__ == "__main__":
    scan_vault(sys.argv[1] if len(sys.argv) > 1 else ".")
