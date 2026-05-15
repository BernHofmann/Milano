import streamlit as st
import requests
import pandas as pd
import datetime
import urllib.parse

# Seiten-Layout optimieren
st.set_page_config(page_title="TrainBoard Italia", layout="wide")

STATIONS = {
    "Milano Centrale": "S01700",
    "Roma Termini": "S09218",
    "Venezia S. Lucia": "S02716",
    "Firenze S.M.N.": "S06421",
    "Napoli Centrale": "S09721",
    "Torino Porta Nuova": "S00219"
}

st.title("🇮🇹 Live TrainBoard")

# Auswahl-Menüs
col1, col2 = st.columns(2)
with col1:
    selected_station_name = st.selectbox("Bahnhof:", list(STATIONS.keys()))
    station_id = STATIONS[selected_station_name]
with col2:
    mode_name = st.radio("Modus:", ["Abfahrten 🛫", "Ankünfte 🛬"], horizontal=True)

@st.cache_data(ttl=30) # Schnellerer Cache für aktuellere Gleis-Infos
def get_live_data(station_id, mode_name):
    api_mode = "partenze" if "Abfahrten" in mode_name else "arrivi"
    
    # Zeitzonen-Management
    now_utc = datetime.datetime.utcnow()
    italy_time = now_utc + datetime.timedelta(hours=2) 
    
    days_en = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    date_str = f"{days_en[italy_time.weekday()]} {months_en[italy_time.month - 1]} {italy_time.day:02d} {italy_time.year} {italy_time.hour:02d}:{italy_time.minute:02d}:{italy_time.second:02d} GMT+0200"
    encoded_date = urllib.parse.quote(date_str)
    
    url = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/{api_mode}/{station_id}/{encoded_date}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        board_data = []
        for train in data:
            # Zeit & Ziel
            time = train.get('compOrarioPartenza' if "Abfahrten" in mode_name else 'compOrarioArrivo', '--:--')
            location = train.get('destinazione' if "Abfahrten" in mode_name else 'origine', 'Unbekannt')
            
            # Zug-Info
            train_name = f"{train.get('categoriaDescrizione', '')} {train.get('numeroTreno', '')}".strip()
            
            # Verspätung
            delay = train.get('ritardo', 0)
            delay_str = f"🔴 +{delay} Min" if delay > 0 else "🟢 OK"
            
            # GLEIS-LOGIK (Verbessert)
            # Wir prüfen nacheinander alle möglichen Felder, die die API für Gleise nutzt
            if "Abfahrten" in mode_name:
                p = train.get('binarioEffettivoPartenzaDesc') or train.get('binarioProgrammatoPartenzaDesc') or \
                    train.get('binarioEffettivoPartenza') or train.get('binarioProgrammatoPartenza')
            else:
                p = train.get('binarioEffettivoArrivoDesc') or train.get('binarioProgrammatoArrivoDesc') or \
                    train.get('binarioEffettivoArrivo') or train.get('binarioProgrammatoArrivo')
            
            platform = str(p).strip() if p else "-"

            # WICHTIG: Die Reihenfolge hier bestimmt die Spalten in der App!
            # Gleis steht jetzt an 2. Stelle für bessere Sichtbarkeit auf dem iPhone
            board_data.append({
                "Zeit": time,
                "Gleis": platform,
                "Richtung" if "Abfahrten" in mode_name else "Von": location,
                "Zug": train_name,
                "Status": delay_str
            })
            
        return pd.DataFrame(board_data), data
    except:
        return pd.DataFrame(), {"error": "API Fehler"}

# UI für Update
if st.button("🔄 Aktualisieren", use_container_width=True):
    get_live_data.clear()
    st.rerun()

# Daten laden
df, raw = get_live_data(station_id, mode_name)

if not df.empty:
    # Suchfilter
    search = st.text_input("🔍 Filter (z.B. Ziel oder Zugnummer):")
    if search:
        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        df = df[mask]
    
    # Anzeige der Tabelle
    st.dataframe(df, hide_index=True, use_container_width=True)
else:
    st.warning("Keine Daten gefunden. Versuche es in ein paar Sekunden erneut.")
