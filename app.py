import streamlit as st
import requests
import pandas as pd
import datetime
import urllib.parse

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="TrainBoard Italia", layout="wide")

# --- MODERNES DESIGN (CSS) ---
st.markdown("""
    <style>
    /* Hintergrund und Schriftart */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Zug-Karte Design */
    .train-card {
        background: #1d2129;
        border-left: 5px solid #0054a6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    
    .train-time {
        font-size: 24px;
        font-weight: bold;
        color: #ffffff;
    }
    
    .train-platform {
        background: #f1c40f;
        color: #000;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: bold;
        float: right;
    }
    
    .train-dest {
        font-size: 18px;
        color: #e0e0e0;
        margin-top: 5px;
    }
    
    .train-info {
        font-size: 14px;
        color: #888;
    }
    
    .status-ok { color: #2ecc71; font-weight: bold; }
    .status-delay { color: #e74c3c; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

STATIONS = {
    "Milano Centrale": "S01700",
    "Roma Termini": "S09218",
    "Venezia S. Lucia": "S02716",
    "Firenze S.M.N.": "S06421",
    "Napoli Centrale": "S09721",
    "Torino Porta Nuova": "S00219"
}

# --- HEADER ---
st.title("🚉 TrainBoard")

# --- EINSTELLUNGEN ---
with st.expander("⚙️ Einstellungen & Filter"):
    col1, col2 = st.columns(2)
    with col1:
        selected_station_name = st.selectbox("Bahnhof:", list(STATIONS.keys()))
        station_id = STATIONS[selected_station_name]
    with col2:
        mode_name = st.radio("Modus:", ["Abfahrten", "Ankünfte"], horizontal=True)
    search_query = st.text_input("🔍 Suchen (Zug oder Ziel)...")

# --- API LOGIK (Unverändert stabil) ---
@st.cache_data(ttl=30)
def get_live_data(station_id, mode_name):
    api_mode = "partenze" if "Abfahrten" in mode_name else "arrivi"
    now_utc = datetime.datetime.utcnow()
    italy_time = now_utc + datetime.timedelta(hours=2) 
    
    days_en = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    date_str = f"{days_en[italy_time.weekday()]} {months_en[italy_time.month - 1]} {italy_time.day:02d} {italy_time.year} {italy_time.hour:02d}:{italy_time.minute:02d}:{italy_time.second:02d} GMT+0200"
    encoded_date = urllib.parse.quote(date_str)
    
    url = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/{api_mode}/{station_id}/{encoded_date}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        return data
    except:
        return []

# --- REFRESH BUTTON ---
if st.button("🔄 Aktualisieren", use_container_width=True):
    get_live_data.clear()
    st.rerun()

# --- DATEN ANZEIGEN ---
raw_data = get_live_data(station_id, mode_name)

if raw_data:
    for train in raw_data:
        # Daten extrahieren
        time = train.get('compOrarioPartenza' if "Abfahrten" in mode_name else 'compOrarioArrivo', '--:--')
        location = train.get('destinazione' if "Abfahrten" in mode_name else 'origine', 'Unbekannt')
        train_name = f"{train.get('categoriaDescrizione', '')} {train.get('numeroTreno', '')}".strip()
        delay = train.get('ritardo', 0)
        
        # Gleis Logik
        if "Abfahrten" in mode_name:
            p = train.get('binarioEffettivoPartenzaDescrizione') or train.get('binarioProgrammatoPartenzaDescrizione')
        else:
            p = train.get('binarioEffettivoArrivoDescrizione') or train.get('binarioProgrammatoArrivoDescrizione')
        platform = str(p).strip() if p else "-"

        # Filterprüfung
        if search_query.lower() not in location.lower() and search_query.lower() not in train_name.lower():
            continue

        # MODERNES KARTEN-TEMPLATE (HTML)
        status_class = "status-delay" if delay > 0 else "status-ok"
        status_text = f"+{delay} Min" if delay > 0 else "Pünktlich"
        
        st.markdown(f"""
            <div class="train-card">
                <span class="train-platform">Gleis {platform}</span>
                <div class="train-time">{time}</div>
                <div class="train-dest">{location}</div>
                <div class="train-info">
                    {train_name} • <span class="{status_class}">{status_text}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("Warten auf Live-Daten...")

# --- DIAGNOSE (Dezenter am Ende) ---
with st.expander("🛠️ Rohdaten"):
    st.json(raw_data)
