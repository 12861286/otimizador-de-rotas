import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps

# 1. Configurações de Interface
st.set_page_config(page_title="Router Master Pro", layout="wide")

# 2. Chave de API (Validada no projeto round-plating-331513)
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Roteirizador Shopee: 82+ Paradas Otimizadas")

uploaded_file = st.file_uploader("Arraste sua planilha Shopee (CSV ou XLSX)", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Carregar dados
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    if 'Parada Original' not in df.columns:
        df['Parada Original'] = range(1, len(df) + 1)

    # --- LÓGICA DE OTIMIZAÇÃO POR BLOCOS (Para bater o limite de 25) ---
    locais = df[['Latitude', 'Longitude']].values.tolist()
    df_final = pd.DataFrame()
    polylines_totais = []
    
    tamanho_lote = 25 # Limite da API Directions
    
    st.info(f"Processando {len(df)} paradas... Calculando rota mais rápida pelas ruas.")

    try:
        for i in range(0, len(locais), tamanho_lote):
            # Define o pedaço da lista (ex: 0-25, 25-50...)
            lote = locais[i:i + tamanho_lote]
            if len(lote) < 2: continue
            
            # Chama o Google para otimizar este bloco específico
            res = gmaps.directions(
                origin=lote[0],
                destination=lote[-1],
                waypoints=lote[1:-1],
                optimize_waypoints=True, # Força o percurso mais rápido
                mode="driving"
            )

            if res:
                # 1. Extrai a ordem otimizada
                ordem = res[0]['waypoint_order']
                indices_otimizados = [0] + [idx + 1 for idx in ordem] + [len(lote) - 1]
                
                # 2. Organiza o DataFrame deste bloco
                pedaco_df = df.iloc[i:i + tamanho_lote].iloc[indices_otimizados].copy()
                df_final = pd.concat([df_final, pedaco_df])
                
                # 3. Guarda o desenho das ruas
                caminho = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                polylines_totais.append([(p['lat'], p['lng']) for p in caminho])

        # Resetar contagem final
        df_final = df_final.reset_index(drop=True)
        df_final['Nova_Sequencia'] = range(1, len(df_final) + 1)

        # 3. Exibição no Mapa
        centro = [df_final['Latitude'].mean(), df_final['Longitude'].mean()]
        m = folium.Map(location=centro, zoom_start=13)

        # Desenha TODAS as ruas conectadas
        for linha in polylines_totais:
            folium.PolyLine(linha, color="#007AFF", weight=5, opacity=0.8).add_to(m)

        # Marcadores com números visíveis
        for _, row in df_final.iterrows():
            n_atual = int(row['Nova_Sequencia'])
            n_orig = int(row['Parada Original'])
            
            icon_html = f'''
                <div style="position: relative; width: 30px; height: 30px;">
                    <img src="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png" style="width: 24px;">
                    <b style="position: absolute; top: 2px; left: 0; width: 24px; text-align: center; color: white; font-size: 10px;">{n_atual}</b>
                </div>'''
            
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                tooltip=f"Parada {n_atual} (Original: {n_orig})",
                icon=folium.DivIcon(icon_size=(24, 41), icon_anchor=(12, 41), html=icon_html)
            ).add_to(m)

        folium_static(m, width=1000)

        # 4. Tabela de Navegação
        st.subheader("📋 Lista de Trabalho")
        for _, row in df_final.iterrows():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(f"**{int(row['Nova_Sequencia'])}º** — {row['Destination Address']} (Original: {row['Parada Original']})")
            with col2:
                # Link que abre direto no App do Google Maps
                url = f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}&travelmode=driving"
                st.link_button("Abrir GPS", url)

    except Exception as e:
        st.error(f"Erro ao traçar rota: {e}")
        st.warning("Certifique-se que as APIs Directions e Geocoding estão ativas no projeto 'round-plating-331513'.")
