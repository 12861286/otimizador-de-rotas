import streamlit as st
import pandas as pd

# Título e Configuração Visual (Modo Escuro e Largo)
st.set_page_config(page_title="Shopee Route Master", layout="wide")

# Estilo Futurista via CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #00ffcc; }
    .stButton>button { width: 100%; background-color: #00ffcc; color: black; border-radius: 10px; font-weight: bold; }
    .delivery-card { border: 1px solid #00ffcc; padding: 15px; border-radius: 15px; margin-bottom: 10px; background-color: #161b22; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Shopee Route Master")
st.write("---")

# Pega a chave dos Secrets que você salvou
try:
    google_key = st.secrets["GOOGLE_MAPS_API_KEY"]
except:
    st.error("Chave API não encontrada nos Secrets!")

uploaded_file = st.file_uploader("📂 Arraste o arquivo da Shopee aqui", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Lendo os dados do seu arquivo
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Resumo no topo
    total_entregas = len(df)
    st.metric(label="Pacotes para Entregar", value=total_entregas)

    # Mapa Interativo
    st.subheader("🗺️ Mapa de Calor da Rota")
    map_df = df[['Latitude', 'Longitude']].rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
    st.map(map_df)

    # Lista de Entregas Otimizada
    st.subheader("📋 Sequência de Entregas")
    
    for i, row in df.iterrows():
        # Criando o "Card" de entrega
        with st.container():
            st.markdown(f"""
            <div class="delivery-card">
                <span style="font-size: 20px;"><b>Parada {row['Stop']}</b></span><br>
                <b>Endereço:</b> {row['Destination Address']}<br>
                <b>Bairro:</b> {row['Bairro']}<br>
                <b>Pacote:</b> {row['SPX TN']}
            </div>
            """, unsafe_allow_html=True)
            
            # Botão de navegação em tempo real
            # Esse link abre o app do Google Maps direto na rota
            lat, lon = row['Latitude'], row['Longitude']
            maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
            
            st.link_button(f"🚀 Iniciar Navegação para Parada {row['Stop']}", maps_url)
            st.write("") # Espaço entre entregas
