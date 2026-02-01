| **Task-Eintrag im Journal**                        | **Skill-Kategorie** | **Basis-XP pro 30 Minuten** |
| -------------------------------------------------- | ------------------- | --------------------------- |
| `- [x] Mit [[Mia]] geredet (1h 10m) #social`       | Sozial              | 2.5                         |
| `- [x] Neuen Blog-Entwurf geschrieben (2h) #study` | Intellektuell       | 3.0                         |
| `- [x] Abendessen gekocht (45m) #task`             | Allgemein           | 0.5                         |

| **Kürzel** | **XP Fixwert** | **Anwendung**                       |
| ---------- | -------------- | ----------------------------------- |
| `(1p)`     | **1.0 XP**     | Sehr kleine Aufgabe / Quick-Win     |
| `(3p)`     | **3.0 XP**     | Standard-Aufgabe                    |
| `(5p)`     | **5.0 XP**     | Wichtige oder komplexe Aufgabe      |
| `(8p)`     | **8.0 XP**     | Großer Meilenstein / Projekt-Etappe |


| **Hashtag**   | **Basis-XP (30 Min)** | **Skill-Bereich** | **Einflussfaktoren / Format**       |
| ------------- | --------------------- | ----------------- | ----------------------------------- |
| `#finance`    | **4.0**               | Finanziell        | Dauer in Klammern, z.B. `(1h 30m)`  |
| `#study`      | **3.0**               | Intellektuell     | Dauer in Klammern, z.B. `(45min)`   |
| `#social`     | **2.5**               | Sozial            | Dauer in Klammern, z.B. `(2h)`      |
| `#workout`    | **2.0**               | Physisch          | Dauer in Klammern, z.B. `(1h 0m)`   |
| `#language`   | **1.8**               | Sprachlich        | Dauer in Klammern, z.B. `(30min)`   |
| `#meditation` | **1.5**               | Spirituell        | Dauer in Klammern, z.B. `(15min)`   |
| `#run`        | **2.0***              | Physisch          | Zusätzliche Metrik: `(5.0km)` nötig |
| `#task`       | **0.5**               | Allgemein         | Standard für kleine Erledigungen    |
| `#project`    | **0.5**               | Allgemein         | Fokus auf Output-Dauer              |
| `#cooking`    | **0.5**               | Allgemein         | Zubereitungszeit                    |

# 2025-11-27

## Geschafft!
- [x] Neue Einnahmequelle gefunden und dokumentiert #finance
- [x] Intensives Krafttraining abgeschlossen #workout
- [x] Mit ... über das Projekt gesprochen #social #projektabschluss
- [x] Mein Italienisch geübt #language


# Ab 2025-12-02

Die neue Logik in V4 sieht vor:

- **Priorität:** Eine erledigte Aufgabe (`- [x]`) wird zuerst auf **V3-Punkte** (`(1p)`, `(3p)`) geprüft. Wenn Punkte gefunden werden, wird die entsprechende XP gutgeschrieben.
    
- **Fallback:** Wenn keine Punkte gefunden werden, wird auf **V1-Dauer** (`(30m)`, `(1h)`) geprüft. Wenn eine Dauer gefunden wird, wird die zeitbasierte XP gutgeschrieben.
    
- Die finale **Gesamt-XP** ist die Summe aller zeitbasierten und punktbasierten XP.
    
- Die JSON-Daten speichern nun beide Metriken (Minuten und Aufgaben-XP) pro Skill getrennt, um sie im Dashboard dual darstellen zu können.