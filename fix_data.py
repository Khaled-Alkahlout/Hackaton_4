import csv
import json
import re
from collections import Counter

# De velden zoals ze op een Kies op Maat-pagina staan: "Plaats : ZWOLLE"
VELDEN = ["Docent", "Opleiding", "Plaats", "Onderwijsperiodes", "Niveau",
          "Aantal EC", "Onderwijsvorm", "Voertaal", "Type", "Modulecode"]
ALT = "|".join(re.escape(v) for v in VELDEN)


def veld(tekst, naam):
    """Haalt bijv. 'ZWOLLE' uit '... Plaats : ZWOLLE Onderwijsperiodes : ...'"""
    m = re.search(rf"{re.escape(naam)} : (.*?)(?= (?:{ALT}) : |$)", tekst)
    return m.group(1).strip() if m else ""


def titel_en_rest(tekst):
    """De titel staat 2x achter elkaar na 'Kies op maat - '. Die zoeken we."""
    rest = tekst.removeprefix("Kies op maat - ")
    w = rest.split()
    for n in range(1, min(40, len(w) // 2) + 1):
        if w[:n] == w[n:2 * n]:
            return " ".join(w[:n]), " ".join(w[2 * n:])
    return " ".join(w[:8]), rest  # geen herhaling gevonden: eerste woorden


def korte_beschrijving(rest):
    """Alleen de inhoud, zonder het blok met praktische gegevens onderaan."""
    for stop in ["Aanmelden is", "Ik heb een vraag over deze module", "Docent :"]:
        rest = rest.split(stop)[0]
    return rest.strip()[:1200]


with open("minors.json", encoding="utf-8") as f:
    ruw = json.load(f)

schoon = []
for m in ruw:
    tekst = m["beschrijving"]
    titel, rest = titel_en_rest(tekst)
    instelling = re.search(r"Ik heb een vraag over deze module (.+?) (?:Domein|Docent|Opleiding|Plaats) ", tekst)
    schoon.append({
        "titel": titel,
        "instelling": instelling.group(1) if instelling else "",
        "opleiding": veld(tekst, "Opleiding"),
        "plaats": veld(tekst, "Plaats").title(),
        "periode": m["periode"],
        "ec": veld(tekst, "Aantal EC"),
        "voertaal": veld(tekst, "Voertaal"),
        "onderwijsvorm": veld(tekst, "Onderwijsvorm"),
        "type": veld(tekst, "Type"),
        "beschrijving": korte_beschrijving(rest),
        "url": m["url"],
    })

with open("minors_clean.json", "w", encoding="utf-8") as f:
    json.dump(schoon, f, ensure_ascii=False, indent=2)

with open("minors_clean.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(schoon[0].keys()))
    writer.writeheader()
    writer.writerows(schoon)

# Controle: wat zit er in onze dataset?
print(f"{len(schoon)} minoren opgeschoond\n")
for m in schoon[:5]:
    print("-", m["titel"], "|", m["instelling"], "|", m["plaats"], "|", m["voertaal"], "|", m["ec"], "EC")
print("\nPlaatsen:", Counter(m["plaats"] or "(onbekend)" for m in schoon).most_common(8))
print("Voertaal:", Counter(m["voertaal"] or "(onbekend)" for m in schoon).most_common())
