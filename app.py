import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps

# 1. Configurações Iniciais
st.set_page_config(page_title="Router Master Pro", layout="wide")

# 2. Conexão com sua Chave Validada no projeto round-plating-331513
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=api_key)

st.title("🚚 Roteirizador Inteligente: Percurso Mais Rápido")

uploaded_file = st.file_uploader("Suba sua planilha da Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Criar coluna de parada original caso não exista para exibir no balão
    if 'Parada Original' not in df.columns:
        df['Parada Original'] = range(1, len(df) + 1)

    # 3. Lógica de Otimização (O percurso mais rápido)
    # Pegamos as coordenadas (Lat, Lon)
    locais = df[['Latitude', 'Longitude']].values.tolist()
    origem = locais[0]
    destino = locais[-1]
    intermediarios = locais[1:-1]

    try:
        # Chamada com optimize_waypoints=True para o Google decidir a melhor ordem
        resultado_rota = gmaps.directions(
            origin=origem,
            destination=destino,
            waypoints=intermediarios,
            optimize_waypoints=True,
            mode="driving"
        )

        # Ordem otimizada que o Google retornou
        ordem_otimizada = resultado_rota[0]['waypoint_order']
        # Reorganizar o DataFrame com base na inteligência do Google
        # [Origem] + [Caminho Otimizado] + [Destino]
        indices_finais = [0] + [i + 1 for i in ordem_otimizada] + [len(df) - 1]
        df_otimizado = df.iloc[indices_finais].copy()
        df_otimizado['Nova_Sequencia'] = range(1, len(df_otimizado) + 1)

        # 4. Criação do Mapa
        centro = [df_otimizado['Latitude'].mean(), df_otimizado['Longitude'].mean()]
        m = folium.Map(location=centro, zoom_start=14)

        # Desenhar a linha real das ruas
        linha_ruas = googlemaps.convert.decode_polyline(resultado_rota[0]['overview_polyline']['points'])
        folium.PolyLine([[p['lat'], p['lng']] for p in linha_ruas], color="#007AFF", weight=5).add_to(m)

        # 5. Marcadores com Números Visíveis
        for _, row in df_otimizado.iterrows():
            n_atual = int(row['Nova_Sequencia'])
            n_orig = int(row['Parada Original'])
            
            # HTML customizado para o número aparecer por cima do balão
            icon_html = f"""
                <div style="position: relative; width: 30px; height: 30px;">
                    <img src="https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png" style="width: 25px;">
                    <b style="position: absolute; top: 2px; left: 0; width: 25px; text-align: center; color: white; font-size: 12px; font-family: sans-serif;">{n_atual}</b>
                </div>
            """
            
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=f"Original: {n_orig} | Atual: {n_atual}",
                icon=folium.DivIcon(icon_size=(25, 41), icon_anchor=(12, 41), html=icon_html)
            ).add_to(m)

        folium_static(m, width=900)

        # 6. Lista de Navegação GPS
        st.subheader("📋 Ordem de Entrega Otimizada")
        for _, row in df_otimizado.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{row['Nova_Sequencia']}º** (Original: {row['Parada Original']}) - {row['Destination Address']}")
            with col2:
                url = f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}"
                st.link_button("Abrir GPS", url)

    except Exception as e:
        st.error(f"Erro no Google Cloud: {e}")
        st.info("Verifique se o faturamento (Billing) está ativo no console.")
