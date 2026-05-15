import streamlit as st
import requests
import pandas as pd
import datetime
import urllib.parse

# --- SEITEN-KONFIGURATION ---
st.set_page_config(page_title="TrainBoard Italia Pro", layout="wide")

# --- MODERNES DESIGN (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    
    /* Hauptkarte */
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
    
    .status-ok { color: #2ecc71; font-weight: bold; font-size: 14px; }
    .status-delay { color: #e74c3c; font-weight: bold; font-size: 14px; }
    
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
        height: 12px; width: 12px; background-color: #0054a6;
        border-radius: 50%; position: absolute; left: -7px; top: 12px;
    }
    
    .stop-time { min-width: 60px; font-size: 14px; color: #ffffff; font-weight: bold; margin-left: 15px; }
    .stop-station { font-size: 14px; color: #bdc3c7; flex-grow: 1; }
    .stop-delay { font-size: 12px; color: #e74c3c; margin-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

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

st.title("🚉 TrainBoard Pro")

# --- EINSTELLUNGEN ---
with st.expander("⚙️ Bahnhof & Filter"):
    col1, col2 = st.columns(2)
    with col1:
        selected_station_name = st.selectbox("Bahnhof:", list(STATIONS.keys()))
        station_id = STATIONS[selected_station_name]
    with col2:
        mode_name = st.radio("Modus:", ["Abfahrten", "Ankünfte"], horizontal=True)
    search_query = st.text_input("🔍 Zug oder Stadt suchen...")

# --- API: HAUPTLISTE ---
@st.cache_data(ttl=30)
def get_live_data(station_id, mode_name):
    api_mode = "partenze" if "Abfahrten" in mode_name else "arrivi"
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    date_str = now.strftime("%a %b %d %Y %H:%M:%S GMT+0200")
    url = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/{api_mode}/{station_id}/{urllib.parse.quote(date_str)}"
    try:
        return requests.get(url, timeout=10).json()
    except:
        return []

# --- API: STRECKENVERLAUF ---
def get_route_data(origin_id, train_num):
    # Die API braucht den Startbahnhof und die Zugnummer
    url = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/andamentoTreno/{origin_id}/{train_num}"
    try:
        return requests.get(url, timeout=10).json()
    except:
        return None

if st.button("🔄 Aktualisieren", use_container_width=True):
    get_live_data.clear()
    st.rerun()

raw_data = get_live_data(station_id, mode_name)

if raw_data:
    for train in raw_data:
        # Basisdaten
        time = train.get('compOrarioPartenza' if "Abfahrten" in mode_name else 'compOrarioArrivo', '--:--')
        location = train.get('destinazione' if "Abfahrten" in mode_name else 'origine', 'Unbekannt')
        train_num = str(train.get('numeroTreno', ''))
        train_name = f"{train.get('categoriaDescrizione', '')} {train_num}".strip()
        origin_id = train.get('codOrigine', 'S01700')
        delay = train.get('ritardo', 0)
        
        # Gleis
        p = train.get('binarioEffettivoPartenzaDescrizione') or train.get('binarioProgrammatoPartenzaDescrizione') or train.get('binarioEffettivoPartenzaDesc')
        platform = str(p).strip() if p and str(p).strip() != "None" else "-"

        if search_query.lower() not in location.lower() and search_query.lower() not in train_name.lower():
            continue

        # Design-Elemente
        icon = "🚄" if "FR" in train_name else "🚅" if "IC" in train_name or "EC" in train_name else "🚆"
        status_class = "status-delay" if delay > 0 else "status-ok"
        status_text = f"+{delay} Min" if delay > 0 else "Pünktlich"
        
        # 1. Die Karte anzeigen
        st.markdown(f"""
            <div class="train-card">
                <div class="train-left">
                    <div class="train-time">{time}</div>
                    <div class="train-dest">{location}</div>
                    <div class="train-extra">{icon} {train_name}</div>
                </div>
                <div class="train-right">
                    <div class="train-platform">Gleis {platform}</div>
                    <div class="{status_class}">{status_text}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 2. Der "Klickbare" Bereich (Expander)
        with st.expander("🛤️ Streckenverlauf & Zwischenstopps"):
            with st.spinner("Lade Haltestellen..."):
                route = get_route_data(origin_id, train_num)
                if route and 'fermate' in route:
                    st.markdown('<div class="route-container">', unsafe_allow_html=True)
                    for stop in route['fermate']:
                        stop_name = stop.get('stazione', 'Unbekannt')
                        # Zeit (Ankunft oder Abfahrt je nach Verfügbarkeit)
                        s_time = stop.get('compOrarioArrivo') or stop.get('compOrarioPartenza') or "--:--"
                        s_delay = stop.get('ritardo', 0)
                        s_delay_text = f" (+{s_delay})" if s_delay > 0 else ""
                        
                        st.markdown(f"""
                            <div class="stop-row">
                                <div class="stop-dot"></div>
                                <div class="stop-time">{s_time}</div>
                                <div class="stop-station">{stop_name} <span class="stop-delay">{s_delay_text}</span></div>
                            </div>
                        """, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.warning("Streckenverlauf derzeit nicht verfügbar.")
else:
    st.info("Suche nach Zügen...")
