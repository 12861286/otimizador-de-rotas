import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps

# Configurações de Estilo
st.set_page_config(page_title="Shopee Pro - Rota Inteligente", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .delivery-card { 
        background-color: #ffffff; padding: 15px; border-radius: 12px; 
        border-left: 8px solid #007AFF; margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); color: #212529;
    }
    </style>
    """, unsafe_allow_html=True)

# Inicializa Google Maps
try:
    gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
except:
    st.error("Erro na Chave API. Verifique os Secrets.")

st.title("🚚 Otimizador de Percurso Real")

uploaded_file = st.file_uploader("Suba sua planilha da Shopee", type=['csv', 'xlsx'])

def calcular_melhor_rota(df):
    """ Tenta organizar os pontos para o menor percurso real """
    # Para economizar créditos da API e ser rápido, vamos agrupar por proximidade
    # e usar a ordem lógica de ruas (Bairro -> Rua -> Número)
    # O Google Maps corrigirá a contramão ao clicar no botão de navegar
    df_otimizado = df.sort_values(by=['Bairro', 'Destination Address']).reset_index(drop=True)
    return df_otimizado

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Otimização
    df_rota = calcular_melhor_rota(df)
    df_rota['Nova_Parada'] = range(1, len(df_rota) + 1)

    st.subheader("🗺️ Mapa do Percurso (Caminho sugerido)")
    
    centro = [df_rota['Latitude'].mean(), df_rota['Longitude'].mean()]
    m = folium.Map(location=centro, zoom_start=14)

    # Desenha a linha do percurso
    pontos = df_rota[['Latitude', 'Longitude']].values.tolist()
    folium.PolyLine(pontos, color="#007AFF", weight=3, opacity=0.7).add_to(m)

    for i, row in df_rota.iterrows():
        n_atual = int(row['Nova_Parada'])
        n_orig = int(row['Stop'])
        
        # Balão Bicolor (Azul em cima, Cinza em baixo)
        icon_html = f"""
            <div style="position: relative; width: 40px; height: 50px;">
                <svg viewBox="0 0 384 512" style="width: 40px; height: 50px; position: absolute; z-index: 1;">
                    <defs>
                        <linearGradient id="grad{i}" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="50%" style="stop-color:#007AFF;stop-opacity:1" />
                            <stop offset="50%" style="stop-color:#6c757d;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad{i})" d="M172.268 501.67C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                </svg>
                <div style="position: absolute; top: 4px; width: 40px; text-align: center; color: white; font-weight: bold; font-size: 13px; z-index: 2;">{n_atual}</div>
                <div style="position: absolute; top: 22px; width: 40px; text-align: center; color: #FFD700; font-weight: bold; font-size: 9px; z-index: 2;">{n_orig}</div>
            </div>
        """
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            icon=folium.DivIcon(icon_size=(40, 50), icon_anchor=(20, 50), html=icon_html)
        ).add_to(m)

    folium_static(m, width=700)

    st.subheader("📋 Lista de Paradas")
    for i, row in df_rota.iterrows():
        with st.container():
            st.markdown(f"""
                <div class="delivery-card">
                    <b>PARADA {int(row['Nova_Parada'])}</b> <small>(Original: {int(row['Stop'])})</small><br>
                    {row['Destination Address']}<br>
                    <small>{row['Bairro']}</small>
                </div>
            """, unsafe_allow_html=True)
            
            # O SEGREDO: Usar a URL de navegação oficial para respeitar as ruas
            lat, lon = row['Latitude'], row['Longitude']
            # google.navigation:q=lat,lon abre o APP do Maps em modo navegação real
            nav_url = f"google.navigation:q={lat},{lon}&mode=d"
            
            # Se estiver no PC, o link abaixo abre o navegador
            web_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
            
            st.link_button(f"🚀 INICIAR GPS - PARADA {int(row['Nova_Parada'])}", web_url, use_container_width=True)
