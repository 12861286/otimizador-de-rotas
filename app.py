import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
import numpy as np

# 1. Configuração de Estilo e Página
st.set_page_config(page_title="Shopee Rota Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .delivery-card { 
        background-color: #ffffff; padding: 12px; border-radius: 10px; 
        border-left: 6px solid #007AFF; margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1); color: #212529;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Teste da Chave API
gmaps = None
if "GOOGLE_MAPS_API_KEY" in st.secrets:
    try:
        gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
        # Teste rápido de conexão
        gmaps.geocode("Brasil")
        st.sidebar.success("✅ Google API: Conectada")
    except Exception as e:
        st.sidebar.error(f"❌ Erro na Chave: {e}")
else:
    st.sidebar.warning("⚠️ Chave API não encontrada nos Secrets")

st.title("🚀 Roteirizador Inteligente Shopee")

# 3. Função de Otimização (Percurso mais curto real)
def otimizar_percurso(df_input):
    """Algoritmo para encontrar a menor distância entre os pontos"""
    df_temp = df_input.copy()
    rota = []
    
    # Começa pelo primeiro ponto da lista
    atual = df_temp.iloc[0]
    rota.append(atual)
    df_temp = df_temp.drop(df_temp.index[0])
    
    while not df_temp.empty:
        # Calcula qual ponto está mais perto do atual (matematicamente)
        distancias = np.sqrt(
            (df_temp['Latitude'] - atual['Latitude'])**2 + 
            (df_temp['Longitude'] - atual['Longitude'])**2
        )
        proximo_idx = distancias.idxmin()
        atual = df_temp.loc[proximo_idx]
        rota.append(atual)
        df_temp = df_temp.drop(proximo_idx)
        
    return pd.DataFrame(rota)

# 4. Upload do Arquivo
uploaded_file = st.file_uploader("Suba sua planilha da Shopee (Excel ou CSV)", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Lendo os dados
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Executa a Otimização
    with st.spinner('Otimizando percurso...'):
        df_rota = otimizar_percurso(df_raw)
        df_rota['Nova_Parada'] = range(1, len(df_rota) + 1)

    # 5. Mapa de Visão Geral
    st.subheader("📍 Mapa do Percurso")
    centro = [df_rota['Latitude'].mean(), df_rota['Longitude'].mean()]
    m = folium.Map(location=centro, zoom_start=14)

    # Desenha a linha da rota (traçado geral)
    pontos_linha = df_rota[['Latitude', 'Longitude']].values.tolist()
    folium.PolyLine(pontos_linha, color="#007AFF", weight=2, opacity=0.5).add_to(m)

    for i, row in df_rota.iterrows():
        n_atual = int(row['Nova_Parada'])
        n_orig = int(row['Stop'])
        
        # Balão Bicolor MINI (30px)
        icon_html = f"""
            <div style="position: relative; width: 30px; height: 40px;">
                <svg viewBox="0 0 384 512" style="width: 30px; height: 40px; position: absolute; z-index: 1;">
                    <defs>
                        <linearGradient id="grad{i}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#6c757d;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{i})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 3px; width: 30px; text-align: center; color: white; font-weight: bold; font-size: 11px; z-index: 2; font-family: Arial;">{n_atual}</div>
                <div style="position: absolute; top: 17px; width: 30px; text-align: center; color: #FFD700; font-weight: bold; font-size: 8px; z-index: 2; font-family: Arial;">{n_orig}</div>
            </div>
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(30, 40), icon_anchor=(15, 40), html=icon_html)
        ).add_to(m)

    folium_static(m, width=700)

    # 6. Lista de Entregas (Cards)
    st.subheader("📋 Ordem de Entrega")
    for i, row in df_rota.iterrows():
        with st.container():
            st.markdown(f"""
                <div class="delivery-card">
                    <b>{int(row['Nova_Parada'])}</b> <small>(Original: {int(row['Stop'])})</small><br>
                    {row['Destination Address']}<br>
                    <small>Bairro: {row['Bairro']}</small>
                </div>
            """, unsafe_allow_html=True)
            
            # LINK DO GPS: O Google Maps cuidará da contramão ao abrir o app
            lat, lon = row['Latitude'], row['Longitude']
            # Link oficial que força o modo de direção
            nav_link = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
            st.link_button(f"🚩 NAVEGAR AGORA", nav_link, use_container_width=True)
            st.write("")
