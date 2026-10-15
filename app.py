import io
import json

import streamlit as st
from streamlit_mic_recorder import speech_to_text
from gtts import gTTS
from google import genai
from google.genai import types

from matcher import zoek, MINOREN

MODEL = "gemini-3.5-flash"   # reserve: "gemini-3.1-flash-lite"

# Prompt 1 (gesprek) - hoort in het Prompt Charter
SYSTEM_PROMPT = """Je bent een Nederlandstalige AI-agent die HBO-studenten helpt een minor te kiezen.
Regels:
- Vertel eerlijk dat je een AI bent als daarnaar gevraagd wordt.
- Stel steeds precies één korte vraag tegelijk.
- Verzamel in deze volgorde: 1) opleiding en studiejaar, 2) interesses en onderwerpen,
  3) vaardigheden die de student wil ontwikkelen, 4) praktische voorkeuren (periode, taal, locatie),
  5) wat de student na de studie wil doen.
- Sla vragen over die al beantwoord zijn.
- Noem GEEN namen van minoren en verzin geen minoren of opleidingen.
- Als je alle informatie hebt: vat de antwoorden in 2 zinnen samen en eindig je bericht met precies: [ZOEKEN]
- Vraag niet naar geslacht, afkomst, leeftijd of andere persoonlijke kenmerken die niet relevant zijn.
- Als de student twijfelt of iets niet weet: zeg dat eerlijk en noem de studieadviseur.
- Antwoord kort (max. 3 zinnen), in gewone spreektaal, zonder opsommingstekens of sterretjes,
  want je antwoord wordt hardop voorgelezen."""

# Prompt 2 (uitleg bij gevonden minoren) - hoort ook in het Prompt Charter
UITLEG_PROMPT = """Profiel van de student (letterlijk uit het gesprek):
{profiel}

Gevonden minoren uit onze eigen dataset (JSON):
{minoren}

Leg in het Nederlands per minor in maximaal 2 zinnen uit waarom deze past bij de student.
Gebruik ALLEEN informatie uit de JSON. Noem de titels precies zoals ze in de JSON staan.
Noem geen andere minoren. Zeg niets over velden die leeg zijn.
Sluit af met: Bekijk de bronlinks en overleg bij twijfel met je studieadviseur.
Gebruik geen opsommingstekens of sterretjes, want de tekst wordt voorgelezen."""

st.set_page_config(page_title="Minor-agent", page_icon="🎓")
st.title("🎓 Minor-agent")
st.info(
    "Je praat met een AI-agent, niet met een mens. "
    "We slaan je gesprek niet op. "
    "Twijfel je over je keuze? Neem contact op met je studieadviseur."
)
st.caption(
    f"Dataset: {len(MINOREN)} minoren, door ons team verzameld van kiesopmaat.nl op 15-10-2026. "
    "Dit is een selectie, niet het volledige aanbod."
)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant",
         "content": "Hoi! Ik ben een AI-agent die je helpt een passende minor te vinden. "
                    "Welke opleiding doe je en in welk jaar zit je?"}
    ]


@st.cache_resource
def get_client():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def vraag_gemini(messages):
    """Stuurt het gesprek naar Gemini en geeft het volgende antwoord terug."""
    contents = []
    for m in messages[1:]:
        rol = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": rol, "parts": [{"text": m["content"]}]})
    response = get_client().models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.4),
    )
    return response.text


def uitleg_gemini(resultaten, profiel):
    """Laat Gemini ALLEEN de door Python gevonden minoren uitleggen."""
    compact = [
        {k: r[k] for k in ["titel", "instelling", "plaats", "voertaal", "ec", "periode", "redenen"]}
        | {"beschrijving": r["beschrijving"][:500]}
        for r in resultaten
    ]
    prompt = UITLEG_PROMPT.format(profiel=profiel, minoren=json.dumps(compact, ensure_ascii=False))
    response = get_client().models.generate_content(
        model=MODEL, contents=prompt, config=types.GenerateContentConfig(temperature=0.2)
    )
    return response.text


def spreek_uit(tekst):
    mp3 = io.BytesIO()
    gTTS(tekst, lang="nl").write_to_fp(mp3)
    st.audio(mp3.getvalue(), format="audio/mp3", autoplay=True)


def toon_minoren(resultaten, info=None):
    """Toont de gevonden minoren met de gegevens uit de dataset en de bronlink."""
    for r in resultaten:
        with st.container(border=True):
            st.markdown(f"**{r['titel']}**")
            details = [r["instelling"], r["plaats"], r["voertaal"],
                       f"{r['ec']} EC" if r["ec"] else "", r["periode"]]
            st.caption(" · ".join(d for d in details if d))
            st.write(f"Waarom: {'; '.join(r['redenen'])} (matchscore {r['score']})")
            st.markdown(f"🔗 [Bekijk op Kies op Maat]({r['url']})")
    if info:
        with st.expander("🔍 Hoe is dit bepaald?"):
            st.json(info)


def zoek_en_adviseer():
    """Zoekt in de dataset en voegt het advies toe aan het gesprek."""
    profiel = " ".join(m["content"] for m in st.session_state.messages if m["role"] == "user")
    resultaten, info = zoek(profiel)

    if not resultaten:
        tekst = (f"Ik heb in onze dataset van {len(MINOREN)} minoren geen minor gevonden die goed genoeg "
                 "bij je past. Dat betekent niet dat er geen passende minor bestaat, want onze dataset is beperkt. "
                 "Bespreek je wensen met je studieadviseur, of kijk zelf op kiesopmaat.nl.")
    else:
        try:
            tekst = uitleg_gemini(resultaten, profiel)
        except Exception:
            # Vangnet zonder AI: de uitleg komt dan direct uit de matchgegevens
            tekst = ("Op basis van onze dataset passen deze minoren het best: "
                     + ". ".join(f"{r['titel']} ({', '.join(r['redenen'])})" for r in resultaten)
                     + ". Bekijk de bronlinks en overleg bij twijfel met je studieadviseur.")

    bericht = {"role": "assistant", "content": tekst, "minoren": resultaten, "info": info}
    st.session_state.messages.append(bericht)
    with st.chat_message("assistant"):
        st.write(tekst)
        toon_minoren(resultaten, info)
        spreek_uit(tekst)


# --- Het gesprek tot nu toe tonen ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if "minoren" in m:
            toon_minoren(m["minoren"], m.get("info"))

# --- Invoer: spraak of tekst ---
kol1, kol2 = st.columns([1, 1])
with kol1:
    gesproken = speech_to_text(language="nl", start_prompt="🎤 Inspreken",
                               stop_prompt="⏹️ Stop", just_once=True, key="stt")
with kol2:
    knop_zoeken = st.button("🔎 Zoek nu minoren")
getypt = st.chat_input("Of typ je antwoord hier...")
invoer = gesproken or getypt

zoeken = knop_zoeken
if invoer:
    st.session_state.messages.append({"role": "user", "content": invoer})
    with st.chat_message("user"):
        st.write(invoer)

    try:
        antwoord = vraag_gemini(st.session_state.messages)
    except Exception as e:
        st.error(f"Technische fout: {e}")
        antwoord = ("Sorry, de AI-dienst is nu niet bereikbaar. "
                    "Je kunt op 'Zoek nu minoren' klikken of contact opnemen met je studieadviseur.")

    if "[ZOEKEN]" in antwoord:
        antwoord = antwoord.replace("[ZOEKEN]", "").strip()
        zoeken = True

    st.session_state.messages.append({"role": "assistant", "content": antwoord})
    with st.chat_message("assistant"):
        st.write(antwoord)
        if not zoeken:          # anders praten twee stemmen tegelijk
            spreek_uit(antwoord)

if zoeken:
    zoek_en_adviseer()
