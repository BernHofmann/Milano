import streamlit as st
import requests
import pandas as pd
import datetime
import urllib.parse

# Seiten-Layout für Handys optimieren
st.set_page_config(page_title="Live Milano Centrale", layout="wide")

st.title("🚉 Milano Centrale Live")

@st.cache_data(ttl=60)
def get_live_departures():
    station_id = "S01700"
    
    # 1. FIX: Server-Zeitzonen & Sprach-Probleme manuell umgehen
    now_utc = datetime.datetime.utcnow()
    # Italien ist in der Sommerzeit UTC+2
    italy_time = now_utc + datetime.timedelta(hours=2) 
    
    days_en = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    day_name = days_en[italy_time.weekday()]
    month_name = months_en[italy_time.month - 1]
    
    # Exaktes Format erzwingen: "Fri May 15 2026 15:30:00 GMT+0200"
    date_str = f"{day_name} {month_name} {italy_time.day:02d} {italy_time.year} {italy_time.hour:02d}:{italy_time.minute:02d}:{italy_time.second:02d} GMT+0200"
    encoded_date = urllib.parse.quote(date_str)
    
    url = f"http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno/partenze/{station_id}/{encoded_date}"
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        departures = []
        for train in data:
            time = train.get('compOrarioPartenza', '--:--')
            dest = train.get('destinazione', 'Unbekannt')
            train_type = train.get('categoriaDescrizione', '')
            train_num = train.get('numeroTreno', '')
            train_name = f"{train_type} {train_num}".strip()
            
            delay = train.get('ritardo', 0)
            if delay and delay > 0:
                delay_str = f"+{delay} Min."
            else:
                delay_str = "Pünktlich"
            
            # 2. FIX: Alle möglichen Felder für Gleise (Binari) abklappern
            platform = train.get('binarioEffettivoPartenzaDesc')
            if not platform:
                platform = train.get('binarioEffettivoPartenza')
            if not platform:
                platform = train.get('binarioProgrammatoPartenzaDesc')
            if not platform:
                platform = train.get('binarioProgrammatoPartenza')
                
            departures.append({
                "Abfahrt": time,
                "Zug": train_name,
                "Richtung": dest,
                "Verspätung": delay_str,
                "Gleis": str(platform).strip() if platform else '--'
            })
            
        return pd.DataFrame(departures), data # Rohdaten für die Fehlersuche mitgeben
    
    except Exception as e:
        return pd.DataFrame(), {"error": str(e)}

# Header und Aktualisierungs-Button
col1, col2 = st.columns([2, 1])
with col1:
    # Anzeige der aktuellen Uhrzeit (lokal auf dem Gerät)
    st.write(f"Zuletzt aktualisiert: **{datetime.datetime.now().strftime('%H:%M:%S')} Uhr**")
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        get_live_departures.clear()
        st.rerun()

# Daten laden
df, raw_data = get_live_departures()

if not df.empty:
    st.dataframe(df, hide_index=True, use_container_width=True)
else:
    st.error("Live-Daten konnten nicht geladen werden.")

# 3. FIX: Unsichtbarer Diagnose-Bereich für dich
st.divider()
with st.expander("🛠️ Diagnose: Rohe API-Daten anzeigen (für Entwickler)"):
    st.write("Wenn die Tabelle leer ist oder Felder fehlen, siehst du hier, was die Bahn-Server *wirklich* geantwortet haben:")
    st.json(raw_data)
