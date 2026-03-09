import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps

# 1. Configurações de Estilo
st.set_page_config(page_title="Shopee Rota Real", layout="wide")

# 2. Conexão com Google Maps (Sua chave validada)
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Roteirizador Shopee com Ruas Reais")

uploaded_file = st.file_uploader("Suba sua planilha", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Organização da Rota
    df_rota = df.sort_values(by=['Bairro', 'Destination Address']).reset_index(drop=True)
    df_rota['Nova_Parada'] = range(1, len(df_rota) + 1)

    # Criar Mapa
    centro = [df_rota['Latitude'].mean(), df_rota['Longitude'].mean()]
    m = folium.Map(location=centro, zoom_start=14)

    # --- LÓGICA DE ROTA POR RUAS ---
    try:
        # Pegamos as coordenadas de todas as paradas
        waypoints = [[row['Latitude'], row['Longitude']] for i, row in df_rota.iterrows()]
        
        # O Google Directions tem um limite de pontos por requisição, 
        # então traçamos o caminho entre cada parada consecutiva
        for i in range(len(waypoints) - 1):
            origem = waypoints[i]
            destino = waypoints[i+1]
            
            # Chama o Google para achar o caminho real pelas ruas
            direcoes = gmaps.directions(origem, destino, mode="driving")
            
            if direcoes:
                # Decodifica os pontos da rua que o Google retorna
                pontos_rua = googlemaps.convert.decode_polyline(direcoes[0]['overview_polyline']['points'])
                rota_real = [[p['lat'], p['lng']] for p in pontos_rua]
                
                # Desenha a linha azul seguindo a rua no mapa
                folium.PolyLine(rota_real, color="#007AFF", weight=5, opacity=0.7).add_to(m)
    except Exception as e:
        st.error(f"Erro ao traçar rota pelas ruas: {e}")

    # --- MARCADORES COM OS DOIS NÚMEROS ---
    for i, row in df_rota.iterrows():
        n_nova = int(row['Nova_Parada'])
        n_orig = int(row.get('Parada Original', n_nova)) # Pega a coluna da parada original se existir
        
        icon_html = f"""
            <div style="position: relative; width: 35px; height: 45px;">
                <svg viewBox="0 0 384 512" style="width: 35px; height: 45px; position: absolute;">
                    <defs>
                        <linearGradient id="grad{i}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#6c757d;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{i})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 3px; width: 35px; text-align: center; color: white; font-weight: bold; font-size: 10px;">{n_nova}</div>
                <div style="position: absolute; top: 16px; width: 35px; text-align: center; color: #f8f9fa; font-weight: bold; font-size: 10px;">{n_orig}</div>
            </div>
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(35, 45), icon_anchor=(17, 45), html=icon_html)
        ).add_to(m)

    folium_static(m, width=800)

    # Lista de Botões
    for i, row in df_rota.iterrows():
        st.write(f"**{int(row['Nova_Parada'])}** - {row['Destination Address']}")
        gps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}&travelmode=driving"
        st.link_button(f"🚩 IR PARA PARADA", gps_url, use_container_width=True)
