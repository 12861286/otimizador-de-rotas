import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Configuração para Tema Claro
st.set_page_config(page_title="Roteirizador Shopee Claro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; color: #31333F; }
    .delivery-card { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        border-left: 5px solid #ff4b4b; 
        margin-bottom: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        color: #31333F;
    }
    .number-badge {
        background-color: #ff4b4b;
        color: white;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("☀️ Otimizador de Rota Shopee (Modo Claro)")

uploaded_file = st.file_uploader("Subir arquivo da Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Criando a Nova Otimização (Ordenando por Latitude/Longitude para agrupar)
    # No futuro podemos usar a API do Google para otimização exata
    df_otimizado = df.sort_values(by=['Latitude', 'Longitude']).reset_index(drop=True)
    df_otimizado['Nova_Parada'] = df_otimizado.index + 1

    st.subheader("🗺️ Mapa com Paradas Numeradas")
    st.caption("Balão: [Nº Original] -> [Nº Otimizado]")

    centro_lat = df['Latitude'].mean()
    centro_lon = df['Longitude'].mean()
    
    # Mapa em estilo claro
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=14)

    for i, row in df_otimizado.iterrows():
        # Texto do balão: Número original da planilha e novo número
        label = f"{int(row['Stop'])} → {int(row['Nova_Parada'])}"
        
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=f"Endereço: {row['Destination Address']}",
            icon=folium.DivIcon(html=f"""
                <div style="
                    background-color: white; 
                    color: #ff4b4b; 
                    border-radius: 50%; 
                    width: 35px; 
                    height: 35px; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    font-weight: bold;
                    border: 3px solid #ff4b4b;
                    font-size: 10px;
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
                ">{label}</div>""")
        ).add_to(m)

    folium_static(m, width=700)

    st.subheader("📦 Lista de Entregas Otimizada")
    
    for i, row in df_otimizado.iterrows():
        with st.container():
            st.markdown(f"""
            <div class="delivery-card">
                <span class="number-badge">Nova Parada: {int(row['Nova_Parada'])}</span>
                <span style="color: gray; font-size: 0.8em;"> (Original: {int(row['Stop'])})</span><br>
                <b style="font-size: 16px;">{row['Destination Address']}</b><br>
                <span>Bairro: {row['Bairro']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['Latitude']},{row['Longitude']}"
            st.link_button(f"🚗 Abrir GPS para Parada {int(row['Nova_Parada'])}", maps_url, use_container_width=True)
