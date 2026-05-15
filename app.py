import streamlit as st
import requests
import pandas as pd
import datetime
import urllib.parse

# Seiten-Layout für Handys optimieren
st.set_page_config(page_title="Live Milano Centrale", layout="wide", initial_sidebar_state="collapsed")

st.title("🚉 Milano Centrale Live")

@st.cache_data(ttl=60)
def get_live_departures():
    # Stations-ID für Milano Centrale
    station_id = "S01700"
    
    # Die API erfordert einen Zeitstempel in einem bestimmten Format
    now = datetime.datetime.now()
    date_str = now.strftime("%a %b %d %Y %H:%M:%S GMT+0200")
    encoded_date = urllib.parse.quote(date_str)
    
    url = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/partenze/{station_id}/{encoded_date}"
    headers = {"User-Agent": "Mozilla/5.0"} # Verhindert, dass die API die Anfrage blockiert
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        departures = []
        for train in data:
            # Daten aus der JSON-Antwort extrahieren
            time = train.get('compOrarioPartenza', '--:--')
            dest = train.get('destinazione', 'Unbekannt')
            train_type = train.get('categoriaDescrizione', '')
            train_num = train.get('numeroTreno', '')
            train_name = f"{train_type} {train_num}"
            
            # Verspätung berechnen
            delay = train.get('ritardo', 0)
            if delay and delay > 0:
                delay_str = f"+{delay} Min."
            else:
                delay_str = "Pünktlich"
            
            # Gleis (Programmierte vs. tatsächliche Abfahrt)
            platform = train.get('binarioEffettivoPartenzaDesc') 
            if not platform:
                platform = train.get('binarioProgrammatoPartenzaDesc', '--')
            
            departures.append({
                "Abfahrt": time,
                "Zug": train_name,
                "Richtung": dest,
                "Verspätung": delay_str,
                "Gleis": platform.strip() if platform else '--'
            })
            
        return pd.DataFrame(departures)
    
    except Exception as e:
        return pd.DataFrame()

# Header und Aktualisierungs-Button
col1, col2 = st.columns([2, 1])
with col1:
    st.write(f"Zuletzt aktualisiert: **{datetime.datetime.now().strftime('%H:%M:%S')} Uhr**")
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        get_live_departures.clear() # Leert den Cache und erzwingt neue Daten
        st.rerun()

# Daten laden und anzeigen
df = get_live_departures()

if not df.empty:
    # Tabelle anzeigen (Index ausblenden für sauberen Look auf dem Handy)
    st.dataframe(df, hide_index=True, use_container_width=True)
else:
    st.error("Live-Daten konnten gerade nicht von der italienischen Bahn geladen werden.")
