| **Task-Eintrag im Journal**                        | **Skill-Kategorie** | **Basis-XP pro 30 Minuten** |
| -------------------------------------------------- | ------------------- | --------------------------- |
| `- [x] Mit [[Mia]] geredet (1h 10m) #social`       | Sozial              | 2.5                         |
| `- [x] Neuen Blog-Entwurf geschrieben (2h) #study` | Intellektuell       | 3.0                         |
| `- [x] Abendessen gekocht (45m) #task`             | Allgemein           | 0.5                         |
# 2025-11-27

## Geschafft!
- [x] Neue Einnahmequelle gefunden und dokumentiert #finance
- [x] Intensives Krafttraining abgeschlossen #workout
- [x] Mit [[Mia]] über das Projekt gesprochen #social #projektabschluss
- [x] Mein Italienisch geübt #language


# Ab 2025-12-02

Die neue Logik in V4 sieht vor:

- **Priorität:** Eine erledigte Aufgabe (`- [x]`) wird zuerst auf **V3-Punkte** (`(1p)`, `(3p)`) geprüft. Wenn Punkte gefunden werden, wird die entsprechende XP gutgeschrieben.
    
- **Fallback:** Wenn keine Punkte gefunden werden, wird auf **V1-Dauer** (`(30m)`, `(1h)`) geprüft. Wenn eine Dauer gefunden wird, wird die zeitbasierte XP gutgeschrieben.
    
- Die finale **Gesamt-XP** ist die Summe aller zeitbasierten und punktbasierten XP.
    
- Die JSON-Daten speichern nun beide Metriken (Minuten und Aufgaben-XP) pro Skill getrennt, um sie im Dashboard dual darstellen zu können.