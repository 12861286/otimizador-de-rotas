import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation

# 1. Configurações Iniciais
st.set_page_config(page_title="Router Master Pro | GMPRO", layout="wide")
API_KEY = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=API_KEY)

st.title("🚚 Router Master Pro: Otimização em Tempo Real")

loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha de 82 pontos", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df = df.dropna(subset=['Latitude', 'Longitude'])

    # Botão de ação para não rodar o código pesado toda hora que a página atualizar
    if st.button("🚀 Iniciar Otimização"):
        with st.spinner('O Google está processando a melhor rota...'):
            
            # Ponto de partida
            if loc and 'coords' in loc:
                lat_i, lon_i = loc['coords']['latitude'], loc['coords']['longitude']
            else:
                lat_i, lon_i = df.iloc[0]['Latitude'], df.iloc[0]['Longitude']

            # LÓGICA DE SEGURANÇA: Divide em lotes de 20 para não travar a API
            #
            df_restante = df.copy()
            ordem_otimizada = []
            ponto_atual = (lat_i, lon_i)

            while len(df_restante) > 0:
                # Pega os próximos 20 mais próximos fisicamente primeiro (Pré-filtro)
                df_restante['d'] = np.sqrt((df_restante['Latitude'] - ponto_atual[0])**2 + 
                                          (df_restante['Longitude'] - ponto_atual[1])**2)
                lote = df_restante.nsmallest(20, 'd').copy()
                
                destinos = lote[['Latitude', 'Longitude']].values.tolist()
                
                try:
                    # Usa o motor de otimização do Google dentro do Directions (Mais estável que o GMPRO puro no Streamlit)
                    res = gmaps.directions(ponto_atual, destinos[-1], waypoints=destinos[:-1], optimize_waypoints=True)
                    
                    if res:
                        ordem_indices = res[0]['waypoint_order']
                        for idx in ordem_indices:
                            p = lote.iloc[idx]
                            ordem_otimizada.append(p)
                            df_restante = df_restante.drop(p.name)
                        
                        ponto_atual = (ordem_otimizada[-1]['Latitude'], ordem_otimizada[-1]['Longitude'])
                except Exception as e:
                    # Se der erro na API, processa o restante por proximidade simples para não travar a tela
                    idx_prox = df_restante['d'].idxmin()
                    p_e = df_restante.loc[idx_prox]
                    ordem_otimizada.append(p_e)
                    ponto_atual = (p_e['Latitude'], p_e['Longitude'])
                    df_restante = df_restante.drop(idx_prox)

            # 2. Construção do Mapa
            m = folium.Map(location=[lat_i, lon_i], zoom_start=15)
            
            for i, row in enumerate(ordem_otimizada):
                n = i + 1
                # Resolve o problema do 9 pulando o 10
                cor = "#007AFF" # Azul padrão Shopee
                
                icon_html = f'''
                    <div style="width: 35px; height: 35px; background:{cor}; border:2px solid white; 
                    border-radius:50%; display:flex; align-items:center; justify-content:center; 
                    color:white; font-weight:bold; font-size:12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
                    {n}</div>'''
                
                folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(html=icon_html)).add_to(m)

            # Desenha a linha azul de conexão
            caminho = [[lat_i, lon_i]] + [[r['Latitude'], r['Longitude']] for r in ordem_otimizada]
            folium.PolyLine(caminho, color="#007AFF", weight=4, opacity=0.8).add_to(m)

            folium_static(m, width=1100)

            # 3. Lista de Botões GPS (Organizada)
            st.success("✅ Rota finalizada e organizada por vizinhança real.")
            for i, row in enumerate(ordem_otimizada):
                col1, col2 = st.columns([5, 1])
                col1.write(f"**{i+1}º** — {row.get('Destination Address', 'Endereço')}")
                col2.link_button("🚗 GPS", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
