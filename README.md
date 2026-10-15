# 🎓 Minor-agent — Nederlandstalige spraakagent voor minorkeuze

Proof of Concept gebouwd tijdens **Hackathon 4: Spraakagent** (15 oktober 2026).

Minor-agent is een spraakgestuurde AI-agent die HBO-studenten helpt een passende minor te vinden. De student praat (of typt) in het Nederlands, de agent stelt vervolgvragen over opleiding, interesses, vaardigheden en voorkeuren, en geeft daarna persoonlijke aanbevelingen, met uitleg en een bronlink naar [Kies op Maat](https://www.kiesopmaat.nl/modules/).

> **Kernprincipe:** de AI praat en legt uit, maar **kiest nooit zelf** welke minoren worden aanbevolen. Dat doet onze eigen Python-code op een dataset die wij zelf hebben verzameld. Zo kan de agent geen minoren verzinnen en is elke aanbeveling te controleren.

---

## Functionaliteiten

- 🎤 **Spraak naar tekst** in het Nederlands, met een tekstveld als fallback
- 💬 **Gesprek met vervolgvragen** (één vraag tegelijk) via Gemini
- 🔎 **Zoeken en matchen** in een zelf verzamelde dataset van 60 echte minoren, zonder AI
- 🧾 **Uitleg per minor**, gebaseerd op de gegevens uit de dataset
- 🔗 **Bronlink** naar Kies op Maat bij elke aanbeveling
- 🔊 **Tekst naar spraak**: de agent spreekt zijn antwoord hardop uit
- 🙋 **Menselijk vangnet**: geen goede match → eerlijk melden en doorverwijzen naar de studieadviseur
- 🔍 **Transparantie**: uitklapvak "Hoe is dit bepaald?" met trefwoorden en scores

---

## Architectuur

```
Student ──► Browser (Streamlit)
              │  🎤 spraak ──► Google Web Speech (spraak → tekst)
              ▼
           app.py ──► Gemini API: gesprek + vervolgvragen ──► [ZOEKEN]
              │
              ▼
          matcher.py ──► minors_clean.json   (eigen Python, geen AI)
              │
              ▼
           app.py ──► Gemini API: uitleg van ALLEEN de gevonden minoren
              │
              ▼
          gTTS (tekst → spraak) + kaartjes met bronlink ──► Student

Vooraf (eenmalig):
kiesopmaat.nl ──► scraper.py (Playwright, student logt zelf in)
              ──► minors.json ──► fix_data.py ──► minors_clean.json
```

| Laag | Onderdeel | Techniek |
|---|---|---|
| Client | Browser, microfoon, speaker | Chrome / Edge |
| Applicatie | Interface + gesprekslogica | Python, Streamlit (`app.py`) |
| Applicatie | Zoeken en scoren | Python (`matcher.py`) |
| Data | Dataset met 60 minoren | JSON / CSV (geen database) |
| Extern | Spraak naar tekst | `streamlit-mic-recorder` (Google Web Speech) |
| Extern | Taalmodel | Gemini API (`google-genai`) |
| Extern | Tekst naar spraak | `gTTS` |
| Data-pipeline | Scrapen en opschonen | Playwright, BeautifulSoup, regex |

---

## Projectstructuur

```
Hackathon 4/
├── app.py               # Streamlit-app: interface, gesprek, spraak, advies
├── matcher.py           # Zoekt en scoort minoren in de dataset (geen AI)
├── scraper.py           # Haalt minoren op van Kies op Maat (met inlog)
├── fix_data.py          # Schoont de ruwe data op tot losse velden
├── minors.json / .csv   # Ruwe gescrapete data
├── minors_clean.json    # Schone dataset die de app gebruikt
├── minors_clean.csv     # Zelfde data, om te controleren in Excel
├── .streamlit/
│   └── secrets.toml     # API-sleutel (NIET in Git!)
└── .gitignore
```

---

## Installatie

**Vereisten:** Anaconda of Miniconda, Chrome of Edge, en een internetverbinding.

```bash
# 1. Eigen omgeving maken en activeren
conda create -n minoragent python=3.11 -y
conda activate minoragent

# 2. Pakketten installeren
pip install streamlit streamlit-mic-recorder gTTS google-genai requests beautifulsoup4 playwright

# 3. Browser voor de scraper downloaden (alleen nodig om opnieuw te scrapen)
playwright install chromium
```

### API-sleutel instellen

1. Maak een gratis sleutel aan via [Google AI Studio](https://aistudio.google.com/apikey). Gebruik een persoonlijk Google-account.
2. Maak het bestand `.streamlit/secrets.toml`:
   ```toml
   GEMINI_API_KEY = "jouw-sleutel-hier"
   ```
3. Controleer dat `.streamlit/secrets.toml` in `.gitignore` staat. **Zet de sleutel nooit in de code of op GitHub.**

---

## Gebruik

### App starten
```bash
streamlit run app.py
```
De app opent op `http://localhost:8501`. Klik op **🎤 Inspreken** of typ in het tekstveld. Na het gesprek zoekt de agent automatisch. Je kunt ook op **🔎 Zoek nu minoren** klikken.

> Let op: start de app met `streamlit run`, niet met `python app.py`.

### Matcher los testen
```bash
python matcher.py
```
Dit toont de gebruikte trefwoorden en de gevonden minoren met hun score, voor een testprofiel.

### Dataset opnieuw opbouwen (optioneel)
```bash
python scraper.py     # opent een browser: log zelf in, open de modulelijst, druk op Enter
python fix_data.py    # maakt minors_clean.json en minors_clean.csv
```

---

## Hoe werkt het matchen?

`matcher.py` gebruikt een eenvoudig, controleerbaar scoremodel:

1. **Trefwoorden**: woorden uit wat de student zei, zonder stopwoorden en zonder woorden korter dan 4 letters.
2. **Verwante woorden**: een kleine, zelf gemaakte lijst. Noemt de student "data", dan telt ook "analyse" mee.
3. **Score per minor:**
   - trefwoord in de **titel**: +3 punten
   - trefwoord in de **beschrijving**: +1 punt
   - gewenste **plaats**: +2 punten
   - voorkeur **Engels** en voertaal Engels: +2 punten
4. **Drempel**: alleen minoren met **minimaal 3 punten**. Geen enkele minor boven de drempel? Dan verwijst de agent naar de studieadviseur.
5. **Top 3** wordt getoond en door Gemini uitgelegd, waarbij Gemini alleen de gegevens uit de dataset mag gebruiken.

**Voorbeeld:** "Designing Data Narratives" scoort **5**: `data` in de titel (3) en `data` + `analyse` in de beschrijving (2).

---

## Ethiek en privacy

| Eis | Hoe verwerkt |
|---|---|
| Transparantie | Melding in de app: "Je praat met een AI-agent"; uitklapvak "Hoe is dit bepaald?" |
| Privacy | Gesprekken worden niet opgeslagen; de API-sleutel staat in `secrets.toml` |
| Geen verzinsels | Alleen minoren uit de dataset; Gemini krijgt alleen de gevonden minoren |
| Bias | Alleen inhoudelijke voorkeuren tellen mee; de agent vraagt niet naar geslacht, afkomst of leeftijd |
| Menselijk vangnet | Geen goede match → eerlijk melden en verwijzen naar de studieadviseur |
| Bronvermelding | Elke aanbeveling heeft een link naar de pagina op Kies op Maat |
| Scraping | robots.txt gecontroleerd; maximaal 60 minoren; pauze per pagina; student logt zelf in |

⚠️ **Let op:** spraak en tekst worden naar diensten van Google gestuurd (spraakherkenning, Gemini en gTTS). Dat melden we in de presentatie.

---

## Gebruik van AI (verantwoording)

| AI-tool | Waarvoor |
|---|---|
| **Gemini** (in de app) | Gesprek voeren en uitleg schrijven bij gevonden minoren |
| **Claude** (tijdens het bouwen) | Begeleiding, codevoorstellen, architectuurplaatjes |

- De volledige prompts staan in `app.py` (`SYSTEM_PROMPT` en `UITLEG_PROMPT`).
- Alle code is door ons team zelf gedraaid en getest. Fouten zijn gevonden en opgelost: de 401-fout, de SSO-login, de titels die als "Kies op maat" binnenkwamen en de afgekapte velden.
- De dataset is **niet** door AI gemaakt, maar gescrapet van Kies op Maat.

---

## Beperkingen

- De dataset bevat **60 minoren**, een selectie en niet het volledige aanbod van Kies op Maat.
- Bij sommige minoren ontbreken velden zoals plaats en voertaal, omdat de tekst bij het scrapen werd afgekapt.
- Het matchen werkt op **woorden, niet op betekenis**. "Mensen helpen" vindt niet automatisch "zorg".
- De gewichten (3/1/2) en de drempel (3) zijn zelf gekozen en niet wetenschappelijk getest.
- Kies op Maat vereist inloggen, dus de data wordt niet automatisch bijgewerkt.
- De reactiesnelheid hangt af van externe diensten en het netwerk.

*HBO-opleiding · Hackathon 4 · oktober 2026*
