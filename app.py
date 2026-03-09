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

st.title("🚚 Roteirizador Shopee: Otimização Total (82+ Paradas)")

uploaded_file = st.file_uploader("Suba sua planilha Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    if 'Parada Original' not in df.columns:
        df['Parada Original'] = range(1, len(df) + 1)

    # --- LÓGICA DE OTIMIZAÇÃO POR BLOCOS CONECTADOS ---
    locais = df[['Latitude', 'Longitude']].values.tolist()
    df_final_otimizado = pd.DataFrame()
    polylines_totais = []
    
    # O segredo é usar um tamanho menor (23) para dar margem de segurança ao Google
    tamanho_lote = 23 
    
    progress_bar = st.progress(0)
    st.info(f"Calculando a rota mais rápida para {len(locais)} endereços...")

    try:
        for i in range(0, len(locais), tamanho_lote):
            # Define o lote atual
            fim_indice = min(i + tamanho_lote, len(locais))
            lote = locais[i:fim_indice]
            
            if len(lote) < 2:
                continue

            # Chamada otimizada para o bloco
            res = gmaps.directions(
                origin=lote[0],
                destination=lote[-1],
                waypoints=lote[1:-1],
                optimize_waypoints=True,
                mode="driving"
            )

            if res:
                # Extrai a ordem e organiza os dados
                ordem = res[0]['waypoint_order']
                indices_otimizados = [0] + [idx + 1 for idx in ordem] + [len(lote) - 1]
                
                pedaco_df = df.iloc[i:fim_indice].iloc[indices_otimizados].copy()
                df_final_otimizado = pd.concat([df_final_otimizado, pedaco_df])
                
                # Guarda o traçado das ruas
                caminho = googlemaps.convert.decode_polyline(res[0]['overview_polyline']['points'])
                polylines_totais.append([(p['lat'], p['lng']) for p in caminho])
            
            progress_bar.progress(min(fim_indice / len(locais), 1.0))

        # Ajustes Finais da Tabela
        df_final_otimizado = df_final_otimizado.drop_duplicates(subset=['Latitude', 'Longitude']).reset_index(drop=True)
        df_final_otimizado['Nova_Sequencia'] = range(1, len(df_final_otimizado) + 1)

        # 3. Exibição no Mapa
        centro = [df_final_otimizado['Latitude'].mean(), df_final_otimizado['Longitude'].mean()]
        m = folium.Map(location=centro, zoom_start=13)

        # Desenha as linhas das ruas
        for linha in polylines_totais:
            folium.PolyLine(linha, color="#007AFF", weight=5, opacity=0.8).add_to(m)

        # Marcadores com Números Reais
        for _, row in df_final_otimizado.iterrows():
            seq = int(row['Nova_Sequencia'])
            orig = int(row['Parada Original'])
            
            # Balão azul com número branco centralizado
            icon_html = f'''
                <div style="position: relative; width: 30px; height: 30px;">
                    <img src="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png" style="width: 25px;">
                    <span style="position: absolute; top: 2px; left: 0; width: 25px; text-align: center; color: white; font-weight: bold; font-size: 10px; font-family: Arial;">{seq}</span>
                </div>'''
            
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                tooltip=f"Entrega {seq} (Original: {orig})",
                icon=folium.DivIcon(icon_size=(25, 41), icon_anchor=(12, 41), html=icon_html)
            ).add_to(m)

        folium_static(m, width=1000)

        # 4. Painel de Controle de Entregas
        st.subheader("📋 Roteiro de Entrega")
        for _, row in df_final_otimizado.iterrows():
            c1, c2 = st.columns([5, 1])
            c1.write(f"**{int(row['Nova_Sequencia'])}º** — {row['Destination Address']} (Planilha: {int(row['Parada Original'])})")
            link = f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}&travelmode=driving"
            c2.link_button("🚗 GPS", link)

    except Exception as e:
        st.error(f"Erro Crítico: {e}")
        st.info("Dica: Verifique se o projeto 'round-plating-331513' tem faturamento ativo.")
