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
    /* Hintergrund */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Flexbox Layout für die Zug-Karte */
    .train-card {
        background: #1d2129;
        border-left: 5px solid #0054a6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Linke Seite (Zeit & Ziel) */
    .train-left {
        display: flex;
        flex-direction: column;
    }
    
    .train-time {
        font-size: 26px;
        font-weight: bold;
        color: #ffffff;
        line-height: 1.1;
    }
    
    .train-dest {
        font-size: 18px;
        color: #e0e0e0;
        margin-top: 4px;
    }
    
    /* Rechte Seite (Gleis, Zugnummer & Status in der ehemals leeren Ecke) */
    .train-right {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
    }
    
    .train-platform {
        background: #f1c40f;
        color: #000;
        padding: 4px 10px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 10px;
    }
    
    .train-name {
        font-size: 14px;
        color: #888;
        margin-bottom: 3px;
    }
    
    .status-ok { color: #2ecc71; font-weight: bold; font-size: 15px; }
    .status-delay { color: #e74c3c; font-weight: bold; font-size: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- BAHNHÖFE (inkl. Verona und Venedig) ---
STATIONS = {
    "Milano Centrale": "S01700",
    "Roma Termini": "S09218",
    "Venedig (S. Lucia)": "S02716",
    "Verona Porta Nuova": "S02430",
    "Firenze S.M.N.": "S06421",
    "Napoli Centrale": "S09721",
    "Torino Porta Nuova": "S00219",
    "Desenzano Del Garda": "S02084"
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

# --- API LOGIK ---
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
        time = train.get('compOrarioPartenza' if "Abfahrten" in mode_name else 'compOrarioArrivo', '--:--')
        location = train.get('destinazione' if "Abfahrten" in mode_name else 'origine', 'Unbekannt')
        train_name = f"{train.get('categoriaDescrizione', '')} {train.get('numeroTreno', '')}".strip()
        delay = train.get('ritardo', 0)
        
        if "Abfahrten" in mode_name:
            p = train.get('binarioEffettivoPartenzaDescrizione') or train.get('binarioProgrammatoPartenzaDescrizione') or train.get('binarioEffettivoPartenzaDesc') or train.get('binarioProgrammatoPartenzaDesc')
        else:
            p = train.get('binarioEffettivoArrivoDescrizione') or train.get('binarioProgrammatoArrivoDescrizione') or train.get('binarioEffettivoArrivoDesc') or train.get('binarioProgrammatoArrivoDesc')
        
        platform = str(p).strip() if p and str(p).strip() != "None" else "-"

        if search_query.lower() not in location.lower() and search_query.lower() not in train_name.lower():
            continue

        status_class = "status-delay" if delay > 0 else "status-ok"
        status_text = f"+{delay} Min" if delay > 0 else "Pünktlich"
        
        # NEUES HTML LAYOUT
        st.markdown(f"""
            <div class="train-card">
                <div class="train-left">
                    <div class="train-time">{time}</div>
                    <div class="train-dest">{location}</div>
                </div>
                <div class="train-right">
                    <div class="train-platform">Gleis {platform}</div>
                    <div class="train-name">{train_name}</div>
                    <div class="{status_class}">{status_text}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("Warten auf Live-Daten...")
