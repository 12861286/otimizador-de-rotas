import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import requests
import json

# Configurações de página
st.set_page_config(page_title="Router Master Pro | GMPRO", layout="wide")

# Sua Chave de API (Deve ter GMPRO ativa)
API_KEY = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"

st.title("🚚 Router Master Pro: Otimização GMPRO")

uploaded_file = st.file_uploader("Suba sua planilha de 84 paradas", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df = df.dropna(subset=['Latitude', 'Longitude'])

    if st.button("🚀 Calcular Rota de Alta Performance"):
        with st.spinner('Aguarde... O Google está analisando todas as ruas e mãos de direção...'):
            
            # 1. Prepara os dados para o formato que a GMPRO entende
            shipments = []
            for i, row in df.iterrows():
                shipments.append({
                    "deliveries": [{
                        "arrivalLocation": {
                            "latitude": row['Latitude'], 
                            "longitude": row['Longitude']
                        }
                    }],
                    "label": f"Entrega_{i}"
                })

            # Montagem do modelo de otimização
            payload = {
                "model": {
                    "shipments": shipments,
                    "vehicles": [{
                        "startLocation": {
                            "latitude": df.iloc[0]['Latitude'], 
                            "longitude": df.iloc[0]['Longitude']
                        },
                        "label": "Veiculo_Carlos",
                        "costPerKm": 1.0
                    }]
                }
            }

            # 2. Chamada para o Endpoint da GMPRO
            # Nota: Substitua 'SEU_ID_DO_PROJETO' pelo ID real do seu projeto Google Cloud
            url = f"https://routeoptimization.googleapis.com/v1/projects/SEU_ID_DO_PROJETO:optimizeTours?key={API_KEY}"
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                resultado = response.json()
                # Aqui o Google retorna a 'visitOrder' (ordem de visita ideal)
                # Vamos reconstruir o DF na ordem certa
                viagem = resultado['routes'][0]['visits']
                indices_otimizados = [int(v['shipmentLabel'].split('_')[1]) for v in viagem]
                df_final = df.iloc[indices_otimizados].reset_index(drop=True)
                
                st.success("✅ Rota otimizada com a inteligência máxima do Google!")

                # 3. Desenha o Mapa
                centro = [df_final.iloc[0]['Latitude'], df_final.iloc[0]['Longitude']]
                m = folium.Map(location=centro, zoom_start=14)

                for i, row in df_final.iterrows():
                    num = i + 1
                    folium.Marker(
                        [row['Latitude'], row['Longitude']],
                        icon=folium.DivIcon(html=f'''
                            <div style="width: 32px; height: 32px; background:#1A73E8; border:2px solid white; 
                            border-radius:50%; display:flex; align-items:center; justify-content:center; 
                            color:white; font-weight:bold; font-size:12px;">{num}</div>''')
                    ).add_to(m)

                # Linha da rota
                folium.PolyLine(df_final[['Latitude', 'Longitude']].values.tolist(), color="#1A73E8", weight=4).add_to(m)
                folium_static(m, width=1100)

                # Lista de Botões para GPS
                for i, row in df_final.iterrows():
                    st.link_button(f"🚩 Parada {i+1}: {row.get('Destination Address', 'Endereço')}", 
                                  f"google.navigation:q={row['Latitude']},{row['Longitude']}")
            else:
                st.error(f"Erro na API GMPRO: {response.text}")
