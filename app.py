import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation

# 1. Setup da API
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Blocos de 5 Paradas")

loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    with st.spinner('Organizando entregas em blocos de 5 para não deixar ninguém para trás...'):
        if loc:
            lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        else:
            lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

        # LÓGICA DE BLOCOS DE 5: Varre os 5 mais próximos e fecha o grupo
        def organizar_por_blocos_de_cinco(df, l_i, o_i):
            df_temp = df.copy()
            rota_final = []
            l_atual, o_atual = l_i, o_i
            
            while not df_temp.empty:
                # Calcula distâncias para todos os pontos restantes
                df_temp['dist'] = np.sqrt((df_temp['Latitude'] - l_atual)**2 + (df_temp['Longitude'] - o_atual)**2)
                
                # PEGA OS 5 MAIS PRÓXIMOS (O Bloco)
                tamanho_bloco = min(5, len(df_temp))
                bloco = df_temp.nsmallest(tamanho_bloco, 'dist').copy()
                
                # Organiza esses 5 entre si para o melhor caminho
                while not bloco.empty:
                    bloco['dist_interna'] = np.sqrt((bloco['Latitude'] - l_atual)**2 + (bloco['Longitude'] - o_atual)**2)
                    proximo_idx = bloco['dist_interna'].idxmin()
                    ponto = bloco.loc[proximo_idx]
                    
                    rota_final.append(ponto)
                    l_atual, o_atual = ponto['Latitude'], ponto['Longitude']
                    
                    # Remove de ambos os dataframes
                    df_temp = df_temp.drop(proximo_idx)
                    bloco = bloco.drop(proximo_idx)
                    
            return pd.DataFrame(rota_final)

        df_otimizado = organizar_por_blocos_de_cinco(df_raw, lat_ini, lon_ini)
        df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

        # 2. Criação do Mapa (Desenha tudo de uma vez)
        m = folium.Map(location=[lat_ini, lon_ini], zoom_start=14)
        pts_completos = [[lat_ini, lon_ini]] + df_otimizado[['Latitude', 'Longitude']].values.tolist()

        # "Costura" as linhas azuis (Google aceita até 25, mas faremos de 20 em 20 para segurança)
        for i in range(0, len(pts_completos)-1, 20):
            fim = min(i + 20, len(pts_completos))
            try:
                res = gmaps.directions(pts_completos[i], pts_completos[fim-1], 
                                     waypoints=pts_completos[i+1:fim-1], mode="driving")
                if res:
                    poly = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                    folium.PolyLine([(p['lat'], p['lng']) for p in poly], color="#007AFF", weight=6).add_to(m)
            except:
                pass

        # 3. Renderiza todos os balões com números grandes
        for i, row in df_otimizado.iterrows():
            n_n = int(row['Nova_Seq'])
            icon_html = f'''
                <div style="width: 42px; height: 52px;">
                    <svg viewBox="0 0 384 512">
                        <path fill="#007AFF" d="M172 501C26 291 0 269 0 192 0 85 85 0 192 0s192 85 192 192c0 77-26 99-172 309-9 13-29 13-39 0z"/>
                        <text x="50%" y="35%" text-anchor="middle" fill="white" font-family="Arial" font-weight="bold" font-size="120">{n_n}</text>
                    </svg>
                </div>'''
            folium.Marker([row['Latitude'], row['Longitude']], icon=folium.DivIcon(icon_size=(42, 52), icon_anchor=(21, 52), html=icon_html)).add_to(m)

    folium_static(m, width=1100)

    # Lista de Botões para Navegação
    st.subheader("📋 Sequência de Entregas (Blocos de 5)")
    for _, row in df_otimizado.iterrows():
        with st.expander(f"Parada {int(row['Nova_Seq'])} — {row['Destination Address']}"):
            st.link_button("🚀 Ir para o Maps", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
