import csv
import json
import re
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE = "https://www.kiesopmaat.nl/modules/"
MAX_PAGINAS = 4     # lijstpagina's
MAX_MINOREN = 60    # klein en beleefd houden
WACHT = 1.5         # seconden pauze per pagina


def module_links(html):
    """Alle links naar losse modulepagina's op een lijstpagina."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        url = urljoin(BASE, a["href"]).split("#")[0].split("?")[0]
        pad = urlparse(url).path
        if ("kiesopmaat.nl" in url and pad.startswith("/modules/")
                and pad.strip("/") != "modules" and url not in links):
            links.append(url)
    return links


def volgende_pagina(html, huidige_url):
    """Zoekt de link naar de volgende lijstpagina."""
    soup = BeautifulSoup(html, "html.parser")
    a = soup.find("a", rel="next")
    if not a:
        for kandidaat in soup.find_all("a", href=True):
            if kandidaat.get_text(strip=True) in (">", "›", "»", "Volgende", "volgende"):
                a = kandidaat
                break
    return urljoin(huidige_url, a["href"]) if a else None


def lees_detail(html, url):
    """Haalt de gegevens uit één modulepagina. Niet gevonden = leeg laten."""
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    titel = h1.get_text(" ", strip=True) if h1 else ""
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    tekst = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    ec = re.search(r"(\d+[,.]\d)\s*EC", tekst)
    periode = re.search(r"\d{1,2} \w+ \d{4} t/m \d{1,2} \w+ \d{4}", tekst)
    return {
        "titel": titel,
        "ec": ec.group(1) if ec else "",
        "periode": periode.group(0) if periode else "",
        "beschrijving": tekst[:2000],
        "url": url,
    }


def ga_naar(page, url):
    """Ga naar een pagina en vang SSO-doorverwijzingen netjes op."""
    try:
        page.goto(url, wait_until="domcontentloaded")
    except Exception:
        pass  # doorverwijzing tijdens het laden: niet erg, we wachten hieronder
    try:
        page.wait_for_url("**kiesopmaat.nl/**", timeout=60000)
        page.wait_for_load_state("domcontentloaded")
    except Exception:
        pass
    time.sleep(WACHT)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    ga_naar(page, BASE)

    # Wacht tot de gebruiker ingelogd is én op de modulelijst staat
    while True:
        input("\n>>> Log in en open in het venster de MODULELIJST. Zie je minoren? Druk dan op Enter... ")
        print("Huidige pagina:", page.url)
        if "kiesopmaat.nl" in page.url and "surfconext" not in page.url and module_links(page.content()):
            break
        print("Nog geen modulelijst gevonden. Wacht tot de pagina klaar is en probeer opnieuw.")

    # 1. Links verzamelen (we beginnen op de pagina waar jij nu staat)
    alle_links = []
    for n in range(1, MAX_PAGINAS + 1):
        html = page.content()
        nieuw = [l for l in module_links(html) if l not in alle_links]
        print(f"Pagina {n}: {len(nieuw)} nieuwe modules  ({page.url})")
        alle_links += nieuw
        volgende = volgende_pagina(html, page.url)
        if not nieuw or not volgende:
            break
        ga_naar(page, volgende)

    # 2. Elke module uitlezen
    minoren = []
    for url in alle_links[:MAX_MINOREN]:
        try:
            ga_naar(page, url)
            m = lees_detail(page.content(), url)
            if m["titel"]:
                minoren.append(m)
                print("OK  ", m["titel"][:60], "|", m["periode"])
        except Exception as e:
            print("FOUT", url, e)

    browser.close()

# 3. Opslaan: JSON voor de AI, CSV om te controleren
with open("minors.json", "w", encoding="utf-8") as f:
    json.dump(minoren, f, ensure_ascii=False, indent=2)

with open("minors.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["titel", "ec", "periode", "beschrijving", "url"])
    writer.writeheader()
    writer.writerows(minoren)

print(f"\nKlaar: {len(minoren)} minoren opgeslagen in minors.json en minors.csv")
