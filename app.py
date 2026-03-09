import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps

# 1. Configurações de Interface
st.set_page_config(page_title="Router Master Pro", layout="wide")

# 2. Chave de API (Projeto round-plating-331513)
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Roteirizador Shopee: Otimização Total")

uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    if 'Parada Original' not in df.columns:
        df['Parada Original'] = range(1, len(df) + 1)

    # --- LÓGICA DE OTIMIZAÇÃO POR BLOCOS (Limite de 23 para segurança) ---
    locais = df[['Latitude', 'Longitude']].values.tolist()
    df_final_otimizado = pd.DataFrame()
    polylines_totais = []
    tamanho_lote = 23 

    try:
        for i in range(0, len(locais), tamanho_lote):
            fim_indice = min(i + tamanho_lote, len(locais))
            lote = locais[i:fim_indice]
            
            if len(lote) < 2: continue

            res = gmaps.directions(
                origin=lote[0],
                destination=lote[-1],
                waypoints=lote[1:-1],
                optimize_waypoints=True,
                mode="driving"
            )

            if res:
                ordem = res[0]['waypoint_order']
                indices_otimizados = [0] + [idx + 1 for idx in ordem] + [len(lote) - 1]
                pedaco_df = df.iloc[i:fim_indice].iloc[indices_otimizados].copy()
                df_final_otimizado = pd.concat([df_final_otimizado, pedaco_df])
                
                caminho = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                polylines_totais.append([(p['lat'], p['lng']) for p in caminho])

        df_final_otimizado = df_final_otimizado.drop_duplicates(subset=['Latitude', 'Longitude']).reset_index(drop=True)
        df_final_otimizado['Nova_Sequencia'] = range(1, len(df_final_otimizado) + 1)

        # 3. Mapa com Balões Bicolores e Números
        centro = [df_final_otimizado['Latitude'].mean(), df_final_otimizado['Longitude'].mean()]
        m = folium.Map(location=centro, zoom_start=13)

        for linha in polylines_totais:
            folium.PolyLine(linha, color="#007AFF", weight=5, opacity=0.8).add_to(m)

        for i, row in df_final_otimizado.iterrows():
            seq = int(row['Nova_Sequencia'])
            orig = int(row['Parada Original'])
            
            # Balão Bicolor com os dois números
            icon_html = f'''
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
                    <div style="position: absolute; top: 3px; width: 35px; text-align: center; color: white; font-weight: bold; font-size: 10px; font-family: Arial;">{seq}</div>
                    <div style="position: absolute; top: 16px; width: 35px; text-align: center; color: #f8f9fa; font-weight: bold; font-size: 10px; font-family: Arial;">{orig}</div>
                </div>'''
            
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                icon=folium.DivIcon(icon_size=(35, 45), icon_anchor=(17, 45), html=icon_html)
            ).add_to(m)

        folium_static(m, width=1000)

        # 4. Lista de Trabalho
        st.subheader("📋 Roteiro de Entrega")
        for _, row in df_final_otimizado.iterrows():
            c1, c2 = st.columns([5, 1])
            c1.write(f"**{int(row['Nova_Sequencia'])}º** — {row['Destination Address']} (Original: {int(row['Parada Original'])})")
            link = f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}&travelmode=driving"
            c2.link_button("🚗 GPS", link)

    except Exception as e:
        st.error(f"Erro: {e}")
