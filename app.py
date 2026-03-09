import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import numpy as np

# Configuração de página
st.set_page_config(page_title="Router Master Pro", layout="wide")

st.title("🚚 Router Master Pro - Otimização de Percurso")

uploaded_file = st.file_uploader("Suba sua planilha de entregas", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # 1. Carregamento dos Dados
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df = df.dropna(subset=['Latitude', 'Longitude'])
        
        # 2. Lógica de Otimização (Vizinho Mais Próximo)
        # Essa lógica garante que o 10 venha após o 9 se estiverem perto
        def calcular_rota_inteligente(dados):
            df_temp = dados.copy()
            rota_ordenada = []
            # Começa pelo primeiro ponto da planilha ou local atual
            ponto_atual = df_temp.iloc[0]
            rota_ordenada.append(ponto_atual)
            df_temp = df_temp.drop(ponto_atual.name)
            
            while not df_temp.empty:
                # Calcula a distância de onde estou para todos os outros pontos
                lat_atual, lon_atual = rota_ordenada[-1]['Latitude'], rota_ordenada[-1]['Longitude']
                df_temp['distancia'] = np.sqrt(
                    (df_temp['Latitude'] - lat_atual)**2 + 
                    (df_temp['Longitude'] - lon_atual)**2
                )
                
                # Pega o ponto que está REALMENTE mais perto agora
                proximo_ponto = df_temp.loc[df_temp['distancia'].idxmin()]
                rota_ordenada.append(proximo_ponto)
                df_temp = df_temp.drop(proximo_ponto.name)
            
            return pd.DataFrame(rota_ordenada)

        df_otimizado = calcular_rota_inteligente(df)
        st.success(f"✅ {len(df_otimizado)} paradas organizadas por proximidade real!")

        # 3. Criação do Mapa
        centro = [df_otimizado.iloc[0]['Latitude'], df_otimizado.iloc[0]['Longitude']]
        m = folium.Map(location=centro, zoom_start=15)

        # Adiciona os Marcadores com a Nova Sequência
        for i, row in df_otimizado.reset_index().iterrows():
            num = i + 1
            # Cores diferentes para os primeiros e últimos pontos para ajudar na visão geral
            cor = "#007AFF" if num <= 40 else "#34C759"
            
            folium.Marker(
                [row['Latitude'], row['Longitude']],
                icon=folium.DivIcon(html=f'''
                    <div style="width: 35px; height: 35px; background:{cor}; border:2px solid white; 
                    border-radius:50%; display:flex; align-items:center; justify-content:center; 
                    color:white; font-weight:bold; font-size:12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.4);">
                    {num}</div>'''),
                popup=f"Entrega {num}: {row.get('Destination Address', '')}"
            ).add_to(m)

        # Linha da Rota
        pontos_linha = df_otimizado[['Latitude', 'Longitude']].values.tolist()
        folium.PolyLine(pontos_linha, color="#007AFF", weight=4, opacity=0.8).add_to(m)

        folium_static(m, width=1100)

        # 4. Lista de Comandos para o GPS
        st.subheader("📋 Ordem de Entrega")
        for i, row in df_otimizado.reset_index().iterrows():
            with st.expander(f"Parada {i+1} - {row.get('Destination Address', 'Endereço')}"):
                st.link_button("🚗 Abrir Navegação", f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
