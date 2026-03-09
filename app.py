import streamlit as st
import googlemaps

# Sua chave
api_key = "AIzaSyD5AiteGn7kOWmdLT3qgF5d1ODaxMxVMAM"

st.title("Teste de Sincronização")

try:
    gmaps = googlemaps.Client(key=api_key)
    # Teste real de geolocalização
    gmaps.geocode("Brasil")
    st.success("✅ AGORA SIM! O nome do projeto e as APIs estão combinando.")
    st.info("Pode subir sua planilha que o mapa vai carregar agora.")
except Exception as e:
    st.error(f"❌ O Google ainda diz: {e}")
