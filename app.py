import streamlit as st
import requests
import pandas as pd
import datetime
import urllib.parse

# Seiten-Layout für Handys optimieren
st.set_page_config(page_title="TrainBoard Italia", layout="wide")

# Wörterbuch mit den wichtigsten italienischen Bahnhöfen und ihren IDs
STATIONS = {
    "Milano Centrale": "S01700",
    "Roma Termini": "S09218",
    "Venezia S. Lucia": "S02716",
    "Firenze S.M.N.": "S06421",
    "Napoli Centrale": "S09721",
    "Torino Porta Nuova": "S00219"
}

st.title("🇮🇹 TrainBoard Italia")

# --- UI-Elemente für die Auswahl ---
col1, col2 = st.columns(2)
with col1:
    selected_station_name = st.selectbox("Bahnhof wählen:", list(STATIONS.keys()))
    station_id = STATIONS[selected_station_name]
with col2:
    mode_name = st.radio("Anzeige:", ["Abfahrten 🛫", "Ankünfte 🛬"], horizontal=True)

@st.cache_data(ttl=60)
def get_live_data(station_id, mode_name):
    # API-Modus basierend auf der Auswahl ändern
    api_mode = "partenze" if "Abfahrten" in mode_name else "arrivi"
    
    # Zeitzonen-Fix
    now_utc = datetime.datetime.utcnow()
    italy_time = now_utc + datetime.timedelta(hours=2) 
    
    days_en = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    day_name = days_en[italy_time.weekday()]
    month_name = months_en[italy_time.month - 1]
    
    date_str = f"{day_name} {month_name} {italy_time.day:02d} {italy_time.year} {italy_time.hour:02d}:{italy_time.minute:02d}:{italy_time.second:02d} GMT+0200"
    encoded_date = urllib.parse.quote(date_str)
    
    url = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/{api_mode}/{station_id}/{encoded_date}"
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        board_data = []
        for train in data:
            # Zeiten und Orte abhängig vom Modus (Ankunft vs. Abfahrt)
            if "Abfahrten" in mode_name:
                time = train.get('compOrarioPartenza', '--:--')
                location = train.get('destinazione', 'Unbekannt')
            else:
                time = train.get('compOrarioArrivo', '--:--')
                location = train.get('origine', 'Unbekannt')
                
            train_type = train.get('categoriaDescrizione', '')
            train_num = train.get('numeroTreno', '')
            train_name = f"{train_type} {train_num}".strip()
            
            # Verspätung mit farbigen Icons aufwerten
            delay = train.get('ritardo', 0)
            if delay and delay > 0:
                delay_str = f"🔴 +{delay} Min"
            else:
                delay_str = "🟢 Pünktlich"
            
            # Gleise abfragen (wieder abhängig vom Modus)
            if "Abfahrten" in mode_name:
                platform = train.get('binarioEffettivoPartenzaDesc') or train.get('binarioEffettivoPartenza') or train.get('binarioProgrammatoPartenzaDesc') or train.get('binarioProgrammatoPartenza')
            else:
                platform = train.get('binarioEffettivoArrivoDesc') or train.get('binarioEffettivoArrivo') or train.get('binarioProgrammatoArrivoDesc') or train.get('binarioProgrammatoArrivo')
                
            board_data.append({
                "Zeit": time,
                "Richtung" if "Abfahrten" in mode_name else "Von": location,
                "Zug": train_name,
                "Verspätung": delay_str,
                "Gleis": str(platform).strip() if platform else '--'
            })
            
        return pd.DataFrame(board_data), data
    
    except Exception as e:
        return pd.DataFrame(), {"error": str(e)}

# Header und Aktualisierungs-Button
col3, col4 = st.columns([2, 1])
with col3:
    st.write(f"Zuletzt aktualisiert: **{datetime.datetime.now().strftime('%H:%M:%S')} Uhr**")
with col4:
    if st.button("🔄 Refresh", use_container_width=True):
        get_live_data.clear()
        st.rerun()

# --- NEU: Suchen/Filtern Funktion ---
search_query = st.text_input("🔍 Züge oder Städte suchen (z.B. 'Frecciarossa' oder 'Roma'):", "")

# Daten laden
df, raw_data = get_live_data(station_id, mode_name)

if not df.empty:
    # Falls ein Suchbegriff eingegeben wurde, die Tabelle danach filtern
    if search_query:
        # Wandelt alles in Strings um und sucht nach Übereinstimmungen (Groß-/Kleinschreibung wird ignoriert)
        mask = df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        df = df[mask]

    if not df.empty:
        # Tabelle anzeigen
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info(f"Keine Züge für '{search_query}' in den nächsten Minuten gefunden.")
else:
    st.error("Live-Daten konnten nicht geladen werden.")

# Diagnose-Bereich
st.divider()
with st.expander("🛠️ Diagnose: Rohe API-Daten"):
    st.json(raw_data)
