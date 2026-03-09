import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np

st.set_page_config(page_title="Router Master Pro | Vizinhança", layout="wide")

# Sua chave que já está ativa e funcionando
API_KEY = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"
gmaps = googlemaps.Client(key=API_KEY)

st.title("🚚 Router Master Pro - Otimização por Bairros")

uploaded_file = st.file_uploader("Suba sua planilha de 84 paradas", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df = df.dropna(subset=['Latitude', 'Longitude'])

    if st.button("🚀 Gerar Rota Otimizada Agora"):
        with st.spinner('Agrupando pontos próximos para evitar voltas inúteis...'):
            
            # 1. ORDENAÇÃO POR VIZINHANÇA (Lógica de Cluster)
            # Isso garante que o ponto 10 não fique longe do 9 e 11
            def ordenar_por_proximidade(dados):
                restante = dados.copy()
                ordenado = []
                ponto_atual = restante.iloc[0]
                ordenado.append(ponto_atual)
                restante = restante.drop(ponto_atual.name)
                
                while len(restante) > 0:
                    # Cálculo de distância simples para agrupar vizinhos rapidamente
                    restante['d'] = np.sqrt(
                        (restante['Latitude'] - ponto_atual['Latitude'])**2 + 
                        (restante['Longitude'] - ponto_atual['Longitude'])**2
                    )
                    proximo = restante.loc[restante['d'].idxmin()]
                    ordenado.append(proximo)
                    restante = restante.drop(proximo.name)
                    ponto_atual = proximo
                return pd.DataFrame(ordenado)

            df_otimizado = ordenar_por_proximidade(df)

            # 2. DESENHO DO MAPA
            m = folium.Map(location=[df_otimizado.iloc[0]['Latitude'], df_otimizado.iloc[0]['Longitude']], zoom_start=14)
            
            # Adiciona os balões com os números certos
            for i, row in df_otimizado.reset_index().iterrows():
                num = i + 1
                folium.Marker(
                    [row['Latitude'], row['Longitude']],
                    icon=folium.DivIcon(html=f'''
                        <div style="width: 32px; height: 32px; background:#1A73E8; border:2px solid white; 
                        border-radius:50%; display:flex; align-items:center; justify-content:center; 
                        color:white; font-weight:bold; font-size:12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
                        {num}</div>''')
                ).add_to(m)

            # Linha azul de navegação
            folium.PolyLine(df_otimizado[['Latitude', 'Longitude']].values.tolist(), color="#1A73E8", weight=4).add_to(m)
            
            folium_static(m, width=1100)
            st.success(f"✅ {len(df_otimizado)} paradas organizadas com sucesso!")

            # LISTA PARA O GPS
            for i, row in df_otimizado.reset_index().iterrows():
                with st.expander(f"Parada {i+1} - {row.get('Destination Address', 'Ver Endereço')}"):
                    st.link_button("🚗 Abrir no Google Maps", f"google.navigation:q={row['Latitude']},{row['Longitude']}")
