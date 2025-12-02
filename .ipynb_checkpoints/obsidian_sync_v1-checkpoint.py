#!/usr/bin/env python3
# obsidian_sync_v1.py
import os, json, datetime

def scan_vault(vault_path):
    stats = {"skills":{}, "people":{}, "mood_tags":{}}

    # skills
    skill_dir = os.path.join(vault_path, "03_Skills")
    for root, dirs, files in os.walk(skill_dir):
        for f in files:
            if f.endswith(".md"):
                name = f[:-3]
                cat = os.path.basename(root)
                stats["skills"].setdefault(cat, []).append(name)

    # people
    people_dir = os.path.join(vault_path, "02_People")
    if os.path.isdir(people_dir):
        for f in os.listdir(people_dir):
            if f.endswith(".md"):
                name = f[:-3]
                with open(os.path.join(people_dir,f), "r", encoding="utf-8") as infile:
                    content = infile.read()
                if "nähe:" in content.lower():
                    try:
                        val = float(content.lower().split("nähe:")[1].splitlines()[0].strip())
                    except:
                        val = 0
                else:
                    val = 0
                stats["people"][name] = val

    # emotions
    mood_dir = os.path.join(vault_path, "04_Emotions/Moodlog")
    for f in os.listdir(mood_dir):
        if f.endswith(".md"):
            with open(os.path.join(mood_dir,f),"r",encoding="utf-8") as infile:
                content = infile.read()
            for word in content.split():
                if word.startswith("#"):
                    stats["mood_tags"][word] = stats["mood_tags"].get(word,0)+1

    return stats

def write_outputs(vault_path, stats):
    rpg_dir = os.path.join(vault_path, "06_RPG")
    os.makedirs(rpg_dir, exist_ok=True)

    # skill levels
    with open(os.path.join(rpg_dir, "Skill_Levels.md"),"w",encoding="utf-8") as f:
        f.write("# Skill Levels\n")
        for cat, items in stats["skills"].items():
            f.write(f"## {cat}\n")
            for s in items:
                f.write(f"- {s}: Level TBD\n")

    # relationships
    with open(os.path.join(rpg_dir, "Relationships_Stats.md"),"w",encoding="utf-8") as f:
        f.write("# Relationship Stats\n")
        for p,v in stats["people"].items():
            f.write(f"- {p}: Nähe {v}\n")

    # emotions
    with open(os.path.join(rpg_dir, "Emotion_Stats.md"),"w",encoding="utf-8") as f:
        f.write("# Emotion Tags\n")
        for tag,cnt in stats["mood_tags"].items():
            f.write(f"- {tag}: {cnt}\n")

    # XP Log (placeholder)
    xp_dir = os.path.join(rpg_dir, "XP_Log")
    os.makedirs(xp_dir, exist_ok=True)
    today = datetime.date.today().isoformat()
    with open(os.path.join(xp_dir, today + ".md"),"w",encoding="utf-8") as f:
        f.write(f"# XP Log {today}\nPlaceholder XP entry.")

    # cache
    cache = os.path.join(vault_path, "08_System/life_rpg_data.json")
    with open(cache,"w",encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

if __name__=="__main__":
    import sys
    if len(sys.argv)<2:
        print("Usage: python obsidian_sync_v1.py /path/to/Life_RPG")
        exit()
    path = sys.argv[1]
    s = scan_vault(path)
    write_outputs(path, s)
    print("Sync complete.")
