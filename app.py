import streamlit as st
import pandas as pd

st.set_page_config(page_title="Otimizador de Rotas Shopee", layout="wide")

st.title("🚚 Meu Otimizador de Entregas")

# Upload do arquivo que você me enviou
uploaded_file = st.file_uploader("Escolha o arquivo Excel/CSV da Shopee", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Lendo os dados
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    st.write(f"Você tem {len(df)} entregas carregadas.")

    # Exibindo os pontos no mapa (usando as colunas Latitude e Longitude do seu arquivo)
    if 'Latitude' in df.columns and 'Longitude' in df.columns:
        st.subheader("Mapa de Entregas")
        map_data = df[['Latitude', 'Longitude']].rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})
        st.map(map_data)
        
        st.subheader("Sequência de Paradas")
        for i, row in df.iterrows():
            endereco = row['Destination Address']
            bairro = row['Bairro']
            # Cria um link direto para o Google Maps em tempo real
            url = f"https://www.google.com/maps/search/?api=1&query={row['Latitude']},{row['Longitude']}"
            
            col1, col2 = st.columns([3, 1])
            col1.write(f"**Parada {row['Sequence']}:** {endereco} - {bairro}")
            col2.write(f"[Ir para Maps]({url})")
            st.divider()
