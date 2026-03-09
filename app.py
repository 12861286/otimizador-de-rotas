import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np
from streamlit_js_eval import get_geolocation

# Setup
st.set_page_config(page_title="Router Master Pro", layout="wide")
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Router Master Pro: Micro-Rotas Reais")

loc = get_geolocation()
uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    with st.spinner('Ajustando sequência para evitar contramão e pulos...'):
        if loc:
            lat_ini, lon_ini = loc['coords']['latitude'], loc['coords']['longitude']
        else:
            lat_ini, lon_ini = df_raw.iloc[0]['Latitude'], df_raw.iloc[0]['Longitude']

        # LÓGICA DE MICRO-ROTAS: Organiza grupos de 5 consultando o Maps
        def organizar_com_transito_real(df, l_i, o_i):
            df_temp = df.copy()
            rota_final = []
            l_atual, o_atual = l_i, o_i
            
            while not df_temp.empty:
                # 1. Pega os 5 mais próximos por distância simples (Candidatos)
                df_temp['dist'] = np.sqrt((df_temp['Latitude'] - l_atual)**2 + (df_temp['Longitude'] - o_atual)**2)
                tamanho_bloco = min(5, len(df_temp))
                bloco = df_temp.nsmallest(tamanho_bloco, 'dist').copy()
                
                # 2. Pergunta ao Google a melhor ordem para esses 5
                destinos = bloco[['Latitude', 'Longitude']].values.tolist()
                try:
                    # Otimiza a ordem dentro do pequeno bloco
                    res = gmaps.directions((l_atual, o_atual), destinos[-1], waypoints=destinos[:-1], optimize_waypoints=True, mode="driving")
                    ordem_indices = res[0]['waypoint_order']
                    
                    # Adiciona na rota final seguindo a ordem do Google
                    for idx in ordem_indices:
                        ponto_escolhido = bloco.iloc[idx]
                        rota_final.append(ponto_escolhido)
                        df_temp = df_temp.drop(ponto_escolhido.name)
                    
                    # Atualiza posição para o último do bloco
                    ultimo_ponto = bloco.iloc[-1]
                    l_atual, o_atual = ultimo_ponto['Latitude'], ultimo_ponto['Longitude']
                except:
                    # Se falhar, usa proximidade simples para não travar
                    p_idx = df_temp['dist'].idxmin()
                    p_e = df_temp.loc[p_idx]
                    rota_final.append(p_e)
                    l_atual, o_atual = p_e['Latitude'], p_e['Longitude']
                    df_temp = df_temp.drop(p_idx)
                    
            return pd.DataFrame(rota_final)

        df_otimizado = organizar_com_transito_real(df_raw, lat_ini, lon_ini)
        df_otimizado['Nova_Seq'] = range(1, len(df_otimizado) + 1)

        # MAPA
        m = folium.Map(location=[lat_ini, lon_ini], zoom_start=15)
        pts_c = [[lat_ini, lon_ini]] + df_otimizado[['Latitude', 'Longitude']].values.tolist()

        # Desenha a linha azul em blocos de 20 para o Google não reclamar
        for i in range(0, len(pts_c)-1, 20):
            fim = min(i + 20, len(pts_c))
            try:
                res = gmaps.directions(pts_c[i], pts_c[fim-1], waypoints=pts_c[i+1:fim-1], mode="driving")
                if res:
                    poly = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                    folium.PolyLine([(p['lat'], p['lng']) for p in poly], color="#007AFF", weight=6).add_to(m)
            except: pass

        # BALÕES
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

    # Botões de Navegação
    for _, row in df_otimizado.iterrows():
        with st.expander(f"{int(row['Nova_Seq'])}º — {row['Destination Address']}"):
            st.link_button("🚗 Abrir Navegação Real", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
