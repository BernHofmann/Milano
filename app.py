import streamlit as st
import requests
import pandas as pd
import datetime
import urllib.parse
import time # NEU: Für die Auto-Refresh Timeline

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="TrainBoard Italia Pro", layout="wide")

# --- MODERNES DESIGN (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    
    .train-card {
        background: #1d2129;
        border-left: 5px solid #0054a6;
        border-radius: 10px 10px 0 0;
        padding: 15px;
        margin-top: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .train-time { font-size: 26px; font-weight: bold; color: #ffffff; line-height: 1.1; }
    .train-dest { font-size: 18px; color: #e0e0e0; margin-top: 4px; font-weight: bold; }
    .train-extra { font-size: 13px; color: #a0a0a0; margin-top: 4px; }
    .train-right { display: flex; flex-direction: column; align-items: flex-end; min-width: 110px; }
    .train-platform { background: #f1c40f; color: #000; padding: 4px 10px; border-radius: 5px; font-weight: bold; font-size: 14px; margin-bottom: 8px; }
    
    .status-ok { color: #2ecc71; font-weight: bold; font-size: 14px; margin-bottom: 4px; }
    .status-delay { color: #e74c3c; font-weight: bold; font-size: 14px; margin-bottom: 4px; }
    .train-state { font-size: 12px; font-style: italic; color: #bdc3c7; }
    
    /* Streckenverlauf Design */
    .route-container {
        background: #161b22;
        padding: 15px;
        border-radius: 0 0 10px 10px;
        margin-bottom: 20px;
        border: 1px solid #30363d;
        border-top: none;
    }
    
    .stop-row {
        display: flex;
        padding: 8px 0;
        border-left: 2px solid #30363d;
        margin-left: 10px;
        position: relative;
    }
    
    .stop-dot {
        height: 12px; width: 12px;
        border-radius: 50%; position: absolute; left: -7px; top: 12px;
        border: 2px solid #161b22;
    }
    
    .stop-time { min-width: 50px; font-size: 14px; color: #ffffff; font-weight: bold; margin-left: 15px; }
    .stop-station { font-size: 14px; color: #e0e0e0; flex-grow: 1; margin-left: 10px;}
    .stop-delay { font-size: 12px; color: #e74c3c; font-weight: bold; }
    
    .streamlit-expanderHeader {
        background-color: #1d2129 !important;
        border-radius: 0 0 10px 10px !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BAHNHÖFE ---
STATIONS = {
    "Milano Centrale": "S01700",
    "Roma Termini": "S09218",
    "Venedig (S. Lucia)": "S02716",
    "Verona Porta Nuova": "S02430",
    "Firenze S.M.N.": "S06421",
    "Napoli Centrale": "S09721",
    "Torino Porta Nuova": "S00219",
    "Desenzano Del Garda": "S02084",
    "Malpensa Flughafen (T1)": "S01146",
    "Malpensa Flughafen (T2)": "S01147"
}

st.title("🚉 TrainBoard Pro")

# --- EINSTELLUNGEN ---
with st.expander("⚙️ Einstellungen & Filter"):
    col1, col2 = st.columns(2)
    with col1:
        selected_station_name = st.selectbox("Bahnhof:", list(STATIONS.keys()))
        station_id = STATIONS[selected_station_name]
    with col2:
        mode_name = st.radio("Modus:", ["Abfahrten", "Ankünfte"], horizontal=True)
    search_query = st.text_input("🔍 Suchen (Zug oder Ziel)...")

# --- API LOGIK: HAUPTLISTE ---
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
        return response.json()
    except:
        return []

# --- API LOGIK: STRECKENVERLAUF ---
@st.cache_data(ttl=30)
def get_route_data(origin_id, train_num, timestamp):
    url = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/andamentoTreno/{origin_id}/{train_num}/{timestamp}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

# --- AUTO REFRESH TIMELINE (Platzhalter oben) ---
refresh_placeholder = st.empty()

# --- DATEN ANZEIGEN ---
raw_data = get_live_data(station_id, mode_name)

if raw_data:
    for train in raw_data:
        # WICHTIG: 'time' wurde in 'time_val' umbenannt, damit das 'time' Modul für den Refresh-Timer nicht überschrieben wird!
        time_val = train.get('compOrarioPartenza' if "Abfahrten" in mode_name else 'compOrarioArrivo', '--:--')
        location = train.get('destinazione' if "Abfahrten" in mode_name else 'origine', 'Unbekannt')
        train_num = str(train.get('numeroTreno', ''))
        train_name = f"{train.get('categoriaDescrizione', '')} {train_num}".strip()
        origin_id = train.get('codOrigine', 'S01700')
        delay = train.get('ritardo', 0)
        
        train_timestamp = train.get('dataPartenzaTreno') or train.get('millisDataPartenza')
        
        if "Abfahrten" in mode_name:
            p = train.get('binarioEffettivoPartenzaDescrizione') or train.get('binarioProgrammatoPartenzaDescrizione') or train.get('binarioEffettivoPartenzaDesc') or train.get('binarioProgrammatoPartenzaDesc')
        else:
            p = train.get('binarioEffettivoArrivoDescrizione') or train.get('binarioProgrammatoArrivoDescrizione') or train.get('binarioEffettivoArrivoDesc') or train.get('binarioProgrammatoArrivoDesc')
        
        platform = str(p).strip() if p and str(p).strip() != "None" else "-"

        if search_query.lower() not in location.lower() and search_query.lower() not in train_name.lower():
            continue

        if "FR" in train_name or "Italo" in train_name:
            icon = "🚄"
        elif "EC" in train_name or "IC" in train_name or "EN" in train_name:
            icon = "🚅"
        else:
            icon = "🚆"

        orientamento = train.get('compOrientamento', [])
        orientation_text = ""
        if orientamento and isinstance(orientamento, list) and len(orientamento) > 2 and orientamento[2] != "--":
            orientation_text = f" | ℹ️ {orientamento[2]}"

        in_stazione = train.get('inStazione', False)
        non_partito = train.get('nonPartito', True)
        
        train_state_text = ""
        if "Abfahrten" in mode_name:
            if in_stazione:
                train_state_text = "🚉 Am Bahnsteig"
            elif not non_partito:
                train_state_text = "🚄 Unterwegs"
        else:
            if train.get('arrivato', False):
                train_state_text = "🛬 Angekommen"
            elif in_stazione:
                train_state_text = "🚉 Am Bahnsteig"
            elif not non_partito:
                train_state_text = "🚄 Unterwegs"

        status_class = "status-delay" if delay > 0 else "status-ok"
        status_text = f"+{delay} Min" if delay > 0 else "Pünktlich"
        
        st.markdown(f"""
            <div class="train-card">
                <div class="train-left">
                    <div class="train-time">{time_val}</div>
                    <div class="train-dest">{location}</div>
                    <div class="train-extra">{icon} {train_name}{orientation_text}</div>
                </div>
                <div class="train-right">
                    <div class="train-platform">Gleis {platform}</div>
                    <div class="{status_class}">{status_text}</div>
                    <div class="train-state">{train_state_text}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("🛤️ Streckenverlauf & Zwischenstopps"):
            if not train_timestamp:
                st.warning("Zeitstempel fehlt. Die Bahn blockiert aktuell die Abfrage für diesen Zug.")
            else:
                with st.spinner("Lade Haltestellen..."):
                    route = get_route_data(origin_id, train_num, train_timestamp)
                    
                    if route and 'fermate' in route:
                        st.markdown('<div class="route-container">', unsafe_allow_html=True)
                        for stop in route['fermate']:
                            stop_name = stop.get('stazione', 'Unbekannt')
                            
                            t_expected = stop.get('programmata')
                            
                            if t_expected:
                                dt_utc = datetime.datetime.utcfromtimestamp(t_expected / 1000)
                                dt_italy = dt_utc + datetime.timedelta(hours=2) 
                                s_time = dt_italy.strftime('%H:%M')
                            else:
                                s_time = stop.get('compOrarioArrivo') or stop.get('compOrarioPartenza') or "--:--"
                                
                            s_delay = stop.get('ritardoArrivo') or stop.get('ritardoPartenza') or 0
                            
                            is_done = stop.get('arrivoReale') or stop.get('partenzaReale') or stop.get('effettiva')
                            dot_color = "#2ecc71" if is_done else "#30363d"
                            
                            s_delay_text = f" <span class='stop-delay'>(+{s_delay})</span>" if s_delay > 0 else ""
                            
                            st.markdown(f"""
                                <div class="stop-row">
                                    <div class="stop-dot" style="background-color: {dot_color};"></div>
                                    <div class="stop-time">{s_time}</div>
                                    <div class="stop-station">{stop_name}{s_delay_text}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.warning("Streckenverlauf derzeit nicht verfügbar.")
else:
    st.info("Warten auf Live-Daten...")

# --- AUTO REFRESH LOGIK GANZ AM ENDE ---
# Diese Schleife läuft 5 Sekunden, aktualisiert oben den Balken und startet die App dann neu
for step in range(100):
    time.sleep(0.30) # 100 Schritte * 0.05 Sekunden = 5 Sekunden Wartezeit
    seconds_left = 5 - (step // 20)
    refresh_placeholder.progress(step + 1, text=f"🔄 Auto-Refresh in {seconds_left} Sekunden...")

get_live_data.clear()
get_route_data.clear()
st.rerun()
