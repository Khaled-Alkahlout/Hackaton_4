"""Zoekt passende minoren in onze eigen dataset (minors_clean.json).

Werkwijze (controleerbaar, geen AI):
1. Haal trefwoorden uit wat de student heeft gezegd.
2. Tel hoeveel trefwoorden in de titel (x3) en beschrijving (x1) van elke minor staan.
3. Bonuspunten voor gewenste plaats en voertaal Engels.
4. Alleen minoren boven een minimumscore tellen mee; anders: eerlijk 'geen match'.
"""
import json
import re

with open("minors_clean.json", encoding="utf-8") as f:
    MINOREN = json.load(f)

# Woorden die overal voorkomen en dus niets zeggen over interesse
STOPWOORDEN = {
    "aan", "alle", "alles", "ander", "andere", "beetje", "best", "daar", "dacht",
    "deze", "dingen", "doen", "door", "echt", "eigenlijk", "gaan", "goed", "graag",
    "hebben", "heel", "hier", "interesse", "interessant", "jaar", "jouw", "keer",
    "kunnen", "later", "leren", "leuk", "maar", "maken", "meer", "mijn", "minor",
    "minoren", "misschien", "moet", "niet", "nog", "omdat", "ook", "opleiding",
    "over", "studeren", "student", "studie", "tweede", "derde", "vanaf", "veel",
    "voor", "vind", "weet", "werken", "wil", "willen", "word", "worden", "zou",
    "zijn", "zoals", "iets", "eerste", "vierde", "denk", "lijkt", "beter",
    "verbeteren", "volg", "volgen", "naar", "welke", "wat", "met", "het", "een",
}

# Kleine, zelf gemaakte lijst met verwante woorden (uitbreidbaar en uitlegbaar)
VERWANT = {
    "data": ["data", "analyse", "analytics", "dashboard", "statistiek", "kunstmatige"],
    "ai": ["ai", "kunstmatige", "machine", "algoritme", "data"],
    "programmeren": ["programmeren", "software", "code", "applicatie", "ict"],
    "zorg": ["zorg", "gezondheid", "welzijn", "verpleeg"],
    "duurzaam": ["duurzaam", "duurzaamheid", "klimaat", "energie", "circulair"],
    "duurzaamheid": ["duurzaam", "duurzaamheid", "klimaat", "energie", "circulair"],
    "ondernemen": ["ondernemen", "ondernemend", "ondernemerschap", "startup", "innovatie"],
    "onderwijs": ["onderwijs", "leraar", "docent", "didactiek"],
    "creatief": ["creatief", "creativiteit", "design", "ontwerp", "media"],
    "psychologie": ["psychologie", "gedrag", "coaching"],
}

PLAATSEN = sorted({m["plaats"].lower() for m in MINOREN if m.get("plaats")})


def trefwoorden(tekst):
    """Haalt betekenisvolle woorden uit het gesprek en voegt verwante woorden toe."""
    woorden = re.findall(r"[a-zà-ÿ]+", tekst.lower())
    basis = {w for w in woorden if len(w) >= 4 and w not in STOPWOORDEN}
    for sleutel, extra in VERWANT.items():
        if sleutel in woorden:
            basis |= set(extra)
    return basis


def bevat(woord, tekst):
    """True als het woord als (begin van een) los woord in de tekst staat."""
    return re.search(rf"\b{re.escape(woord)}", tekst) is not None


def zoek(gesprekstekst, top=3, minimum=3):
    """Geeft (resultaten, info) terug. Resultaten komen ALLEEN uit MINOREN."""
    woorden = trefwoorden(gesprekstekst)
    tekst_l = gesprekstekst.lower()
    plaats = next((p for p in PLAATSEN if p in tekst_l), None)
    wil_engels = "engels" in tekst_l

    resultaten = []
    for m in MINOREN:
        titel = m["titel"].lower()
        besch = m["beschrijving"].lower()
        in_titel = {w for w in woorden if bevat(w, titel)}
        in_besch = {w for w in woorden if bevat(w, besch)}
        score = 3 * len(in_titel) + len(in_besch)

        redenen = []
        gevonden = in_titel | in_besch
        if gevonden:
            redenen.append("komt overeen met: " + ", ".join(sorted(gevonden)))
        if plaats and m.get("plaats", "").lower() == plaats:
            score += 2
            redenen.append(f"locatie {m['plaats']}")
        if wil_engels and "engels" in m.get("voertaal", "").lower():
            score += 2
            redenen.append("voertaal Engels")

        if score >= minimum:
            resultaten.append({**m, "score": score, "redenen": redenen})

    resultaten.sort(key=lambda r: r["score"], reverse=True)
    info = {
        "aantal minoren in dataset": len(MINOREN),
        "gebruikte trefwoorden": sorted(woorden),
        "gewenste plaats": plaats,
        "voorkeur Engels": wil_engels,
        "minimumscore": minimum,
    }
    return resultaten[:top], info
