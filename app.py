import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import numpy as np

st.set_page_config(page_title="Shopee Pro - Carlos", layout="wide")

# Estilo da Interface
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .delivery-card { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 12px; 
        border-left: 8px solid #007AFF; 
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #212529;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚚 Roteirizador Inteligente Shopee")

uploaded_file = st.file_uploader("Suba sua planilha aqui", type=['csv', 'xlsx'])

def otimizar_rota(df_input):
    """Algoritmo de Vizinho Mais Próximo para evitar saltos longos"""
    df_temp = df_input.copy()
    rota_otimizada = []
    
    # Começa pelo primeiro ponto da planilha
    atual = df_temp.iloc[0]
    rota_otimizada.append(atual)
    df_temp = df_temp.drop(df_temp.index[0])
    
    while not df_temp.empty:
        # Calcula a distância de onde estou para todos os outros pontos restantes
        distancias = np.sqrt(
            (df_temp['Latitude'] - atual['Latitude'])**2 + 
            (df_temp['Longitude'] - atual['Longitude'])**2
        )
        proximo_idx = distancias.idxmin()
        atual = df_temp.loc[proximo_idx]
        rota_otimizada.append(atual)
        df_temp = df_temp.drop(proximo_idx)
        
    return pd.DataFrame(rota_otimizada)

if uploaded_file is not None:
    df_original = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # AQUI ACONTECE A MÁGICA DA OTIMIZAÇÃO REAL
    df_otimizado = otimizar_rota(df_original)
    df_otimizado['Nova_Parada'] = range(1, len(df_otimizado) + 1)

    st.subheader("📍 Mapa de Rota Corrigido")
    centro_lat, centro_lon = df_otimizado['Latitude'].mean(), df_otimizado['Longitude'].mean()
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=14)

    # Desenha a linha da rota para você ver o caminho
    pontos_linha = df_otimizado[['Latitude', 'Longitude']].values.tolist()
    folium.PolyLine(pontos_linha, color="#007AFF", weight=2, opacity=0.5).add_to(m)

    for i, row in df_otimizado.iterrows():
        n_atual = int(row['Nova_Parada'])
        n_orig = int(row['Stop'])
        
        icon_html = f"""
            <div style="position: relative; width: 40px; height: 50px;">
                <svg viewBox="0 0 384 512" style="width: 40px; height: 50px; position: absolute; top: 0; left: 0; z-index: 1;">
                    <defs>
                        <linearGradient id="grad{i}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#6c757d;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{i})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 4px; width: 40px; text-align: center; color: white; font-weight: bold; font-size: 14px; z-index: 2;">{n_atual}</div>
                <div style="position: absolute; top: 22px; width: 40px; text-align: center; color: #FFD700; font-weight: bold; font-size: 9px; z-index: 2;">{n_orig}</div>
            </div>
        """
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(40, 50), icon_anchor=(20, 50), html=icon_html)
        ).add_to(m)

    folium_static(m, width=700)

    st.subheader("📋 Sequência de Entregas Otimizada")
    for i, row in df_otimizado.iterrows():
        with st.container():
            st.markdown(f"""
            <div class="delivery-card">
                <b style="font-size: 1.2em; color: #007AFF;">PARADA {int(row['Nova_Parada'])}</b> 
                <span style="color: #888;">(Original: {int(row['Stop'])})</span><br>
                <b>Endereço:</b> {row['Destination Address']}<br>
                <b>Bairro:</b> {row['Bairro']}
            </div>
            """, unsafe_allow_html=True)
            link = f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}&travelmode=driving"
            st.link_button(f"🚩 INICIAR GPS - PARADA {int(row['Nova_Parada'])}", link, use_container_width=True)
