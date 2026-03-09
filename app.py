import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation # Biblioteca para pegar seu GPS real

# 1. Configurações Iniciais
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Iniciando de Onde Você Está")

# Captura sua localização atual via Navegador
loc_atual = get_geolocation()

uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    if 'Parada Original' not in df_raw.columns:
        df_raw['Parada Original'] = range(1, len(df_raw) + 1)

    # Verifica se o GPS foi capturado
    if loc_atual:
        minha_lat = loc_atual['coords']['latitude']
        minha_lon = loc_atual['coords']['longitude']
        st.success(f"📍 Sua localização detectada: {minha_lat:.5f}, {minha_lon:.5f}")
    else:
        st.warning("⚠️ GPS não detectado. Usando o primeiro endereço da planilha como início.")
        minha_lat, minha_lon = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

    # --- ALGORITMO DE VIZINHO MAIS PRÓXIMO PARTINDO DE VOCÊ ---
    def gerar_rota_inteligente(df, start_lat, start_lon):
        df_temp = df.copy()
        rota_ordenada = []
        
        # Ponto de partida é onde você está agora
        lat_agora, lon_agora = start_lat, start_lon
        
        while not df_temp.empty:
            # Calcula distância euclidiana simples para encontrar o vizinho mais próximo
            distancias = np.sqrt(
                (df_temp['Latitude'] - lat_agora)**2 + 
                (df_temp['Longitude'] - lon_agora)**2
            )
            idx_proximo = distancias.idxmin()
            ponto_atual = df_temp.loc[idx_proximo]
            
            rota_ordenada.append(ponto_atual)
            # Atualiza a posição para o próximo cálculo
            lat_agora, lon_agora = ponto_atual['Latitude'], ponto_atual['Longitude']
            df_temp = df_temp.drop(idx_proximo)
            
        return pd.DataFrame(rota_ordenada)

    with st.spinner('Calculando a melhor sequência a partir da sua posição...'):
        df_otimizado = gerar_rota_inteligente(df_raw, minha_lat, minha_lon)
        df_otimizado['Nova_Sequencia'] = range(1, len(df_otimizado) + 1)

    # --- MAPA E TRAÇADO REAL ---
    m = folium.Map(location=[minha_lat, minha_lon], zoom_start=13)

    # Marcador de "Você está aqui"
    folium.Marker([minha_lat, minha_lon], tooltip="VOCÊ", icon=folium.Icon(color='red', icon='user')).add_to(m)

    # Traçado das ruas em blocos (para não travar a API)
    locais = [[minha_lat, minha_lon]] + df_otimizado[['Latitude', 'Longitude']].values.tolist()
    for i in range(0, len(locais)-1, 20):
        fim = min(i + 20, len(locais))
        res = gmaps.directions(locais[i], locais[fim-1], waypoints=locais[i+1:fim-1], mode="driving")
        if res:
            caminho = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
            folium.PolyLine([(p['lat'], p['lng']) for p in caminho], color="#007AFF", weight=5).add_to(m)

    # --- BALÕES BICOLORES COM NÚMEROS VISÍVEIS ---
    for i, row in df_otimizado.iterrows():
        seq, orig = int(row['Nova_Sequencia']), int(row['Parada Original'])
        
        icon_html = f'''
            <div style="position: relative; width: 42px; height: 52px;">
                <svg viewBox="0 0 384 512" style="width: 42px; height: 52px; position: absolute; z-index: 1;">
                    <defs>
                        <linearGradient id="grad{seq}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#343a40;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{seq})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 5px; width: 42px; text-align: center; color: white; font-weight: bold; font-size: 13px; z-index: 10; pointer-events: none;">{seq}</div>
                <div style="position: absolute; top: 20px; width: 42px; text-align: center; color: #00FF00; font-weight: bold; font-size: 10px; z-index: 10; pointer-events: none;">{orig}</div>
            </div>'''
        folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)).add_to(m)

    folium_static(m, width=1100)

    # --- LISTA DE NAVEGAÇÃO ---
    st.subheader("📋 Ordem de Entrega")
    for _, row in df_otimizado.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{int(row['Nova_Sequencia'])}º** — {row['Destination Address']} (Original: {int(row['Parada Original'])})")
        # Link do GPS
        c2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
