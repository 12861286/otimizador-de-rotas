import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from itertools import permutations
import json
import os
import io

st.set_page_config(
    page_title="Router Master Pro | GMPRO",
    layout="wide",
    page_icon="🚚"
)

# ─────────────────────────────────────────────
# CSS customizado
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
.main { background: #0d1117; }
.stApp { background: #0d1117; color: #e6edf3; }
.metric-card {
    background: linear-gradient(135deg, #161b22, #21262d);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
}
.metric-value { font-size: 2rem; font-weight: 700; color: #58a6ff; }
.metric-label { font-size: 0.8rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
.status-ok { color: #3fb950; font-weight: 600; }
.status-warn { color: #d29922; font-weight: 600; }
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #238636, #2ea043);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 700;
    font-size: 1rem;
    padding: 0.6rem 2rem;
    transition: all 0.2s;
}
div[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #2ea043, #3fb950);
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(63,185,80,0.3);
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CABEÇALHO
# ─────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:16px;padding:20px 0 10px;">
  <span style="font-size:2.5rem;">🚚</span>
  <div>
    <h1 style="margin:0;font-size:1.8rem;font-weight:700;color:#e6edf3;">Router Master Pro</h1>
    <p style="margin:0;color:#8b949e;font-size:0.9rem;">Inteligência GMPRO · Otimização de até 100 paradas</p>
  </div>
</div>
<hr style="border-color:#21262d;margin-bottom:24px;">
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ALGORITMO DE OTIMIZAÇÃO (Nearest Neighbor + 2-opt)
# ─────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

def build_distance_matrix(df):
    n = len(df)
    D = np.zeros((n, n))
    lats = df['Latitude'].values
    lons = df['Longitude'].values
    for i in range(n):
        for j in range(i+1, n):
            d = haversine(lats[i], lons[i], lats[j], lons[j])
            D[i][j] = D[j][i] = d
    return D

def nearest_neighbor(D, start=0):
    n = len(D)
    unvisited = list(range(n))
    route = [start]
    unvisited.remove(start)
    while unvisited:
        last = route[-1]
        nearest = min(unvisited, key=lambda x: D[last][x])
        route.append(nearest)
        unvisited.remove(nearest)
    return route

def two_opt(route, D, max_iter=500):
    best = route[:]
    improved = True
    iterations = 0
    while improved and iterations < max_iter:
        improved = False
        iterations += 1
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best)):
                if j - i == 1:
                    continue
                new_route = best[:i] + best[i:j][::-1] + best[j:]
                if route_distance(new_route, D) < route_distance(best, D):
                    best = new_route
                    improved = True
    return best

def route_distance(route, D):
    return sum(D[route[i]][route[i+1]] for i in range(len(route)-1))

def optimize_route_local(df):
    D = build_distance_matrix(df)
    route = nearest_neighbor(D, start=0)
    route = two_opt(route, D)
    total_km = route_distance(route, D)
    return route, total_km, D

# ─────────────────────────────────────────────
# OTIMIZAÇÃO VIA GOOGLE FLEET ROUTING
# ─────────────────────────────────────────────
def optimize_route_google(df, credentials_json, project_id):
    try:
        from google.cloud import optimization_v1
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credentials_json),
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        client = optimization_v1.FleetRoutingClient(credentials=credentials)

        shipments = []
        for i, row in df.iterrows():
            shipments.append(optimization_v1.Shipment(
                deliveries=[optimization_v1.Shipment.Delivery(
                    arrival_location={"latitude": float(row['Latitude']), "longitude": float(row['Longitude'])}
                )],
                label=str(row.get('Nome', f'Parada_{i}'))
            ))

        model = optimization_v1.ShipmentModel(
            shipments=shipments,
            vehicles=[optimization_v1.Vehicle(
                start_location={"latitude": float(df.iloc[0]['Latitude']), "longitude": float(df.iloc[0]['Longitude'])},
                label="Veículo_1"
            )]
        )

        request = optimization_v1.OptimizeToursRequest(
            parent=f"projects/{project_id}",
            model=model
        )
        response = client.optimize_tours(request=request)

        # Extrai ordem das visitas
        route_indices = []
        for route in response.routes:
            for visit in route.visits:
                route_indices.append(visit.shipment_index)

        return route_indices, None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# CONSTRUÇÃO DO MAPA
# ─────────────────────────────────────────────
def build_map(df, route_order):
    ordered = df.iloc[route_order].reset_index(drop=True)
    center_lat = ordered['Latitude'].mean()
    center_lon = ordered['Longitude'].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='CartoDB dark_matter'
    )

    # Linha da rota
    coords = list(zip(ordered['Latitude'], ordered['Longitude']))
    folium.PolyLine(
        coords,
        color='#58a6ff',
        weight=3,
        opacity=0.8,
        dash_array='5 5'
    ).add_to(m)

    # Marcadores
    colors = ['#3fb950' if i == 0 else ('#f85149' if i == len(ordered)-1 else '#58a6ff')
              for i in range(len(ordered))]

    for idx, (_, row) in enumerate(ordered.iterrows()):
        label = row.get('Nome', f'Parada {idx+1}')
        icon_color = 'green' if idx == 0 else ('red' if idx == len(ordered)-1 else 'blue')
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(f"<b>#{idx+1} — {label}</b>", max_width=200),
            tooltip=f"#{idx+1} {label}",
            icon=folium.Icon(color=icon_color, icon='circle', prefix='fa')
        ).add_to(m)

    return m, ordered

# ─────────────────────────────────────────────
# SIDEBAR — CONFIGURAÇÕES
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configurações")
    st.markdown("---")

    engine = st.radio(
        "Motor de Otimização",
        ["🧠 Algoritmo Local (gratuito)", "☁️ Google Fleet Routing (API)"],
        help="O algoritmo local usa Nearest Neighbor + 2-opt e funciona sem internet."
    )

    if "Google" in engine:
        st.markdown("#### Credenciais Google Cloud")
        project_id = st.text_input("Project ID", placeholder="meu-projeto-123")
        credentials_file = st.file_uploader("JSON da Conta de Serviço", type=['json'])
        credentials_json = credentials_file.read().decode() if credentials_file else None

        if not credentials_json:
            st.warning("⚠️ Sem o JSON, usaremos o algoritmo local como fallback.")
    else:
        project_id = None
        credentials_json = None

    st.markdown("---")
    st.markdown("#### Como preparar sua planilha")
    st.markdown("""
A planilha precisa ter pelo menos estas colunas:
- **Latitude** (ex: -19.9245)
- **Longitude** (ex: -43.9352)
- **Nome** *(opcional)* — nome da parada

A primeira linha será o **ponto de partida**.
    """)

    st.markdown("---")
    # Download de planilha modelo
    sample = pd.DataFrame({
        'Nome': ['Depósito', 'Cliente A', 'Cliente B', 'Cliente C'],
        'Latitude': [-19.9245, -19.9312, -19.9180, -19.9400],
        'Longitude': [-43.9352, -43.9401, -43.9280, -43.9500],
        'Endereço': ['Rua Principal 1', 'Rua B 100', 'Av. C 200', 'Rua D 50']
    })
    buf = io.BytesIO()
    sample.to_excel(buf, index=False)
    st.download_button(
        "📥 Baixar planilha modelo",
        data=buf.getvalue(),
        file_name="modelo_paradas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ─────────────────────────────────────────────
# UPLOAD DE ARQUIVO
# ─────────────────────────────────────────────
col_upload, col_info = st.columns([2, 1])

with col_upload:
    uploaded_file = st.file_uploader(
        "📂 Suba sua planilha de paradas (.xlsx ou .csv)",
        type=['csv', 'xlsx'],
        help="Máximo 100 paradas. Precisa ter colunas Latitude e Longitude."
    )

with col_info:
    st.markdown("""
<div class="metric-card" style="margin-top:28px;">
  <div class="metric-label">Capacidade máxima</div>
  <div class="metric-value">100</div>
  <div class="metric-label">paradas por rota</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PROCESSAMENTO
# ─────────────────────────────────────────────
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        st.stop()

    # Validação das colunas
    if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
        st.error("❌ A planilha precisa ter colunas **Latitude** e **Longitude**.")
        st.stop()

    df = df.dropna(subset=['Latitude', 'Longitude']).reset_index(drop=True)

    if len(df) < 2:
        st.error("❌ É necessário pelo menos 2 paradas.")
        st.stop()

    if len(df) > 100:
        st.warning(f"⚠️ {len(df)} paradas detectadas. Limitando às primeiras 100.")
        df = df.head(100)

    # Métricas do upload
    st.markdown("### 📊 Resumo do arquivo")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
<div class="metric-card">
  <div class="metric-value">{len(df)}</div>
  <div class="metric-label">Paradas carregadas</div>
</div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
<div class="metric-card">
  <div class="metric-value">{len(df.columns)}</div>
  <div class="metric-label">Colunas detectadas</div>
</div>""", unsafe_allow_html=True)
    with m3:
        status = "✅ Pronto" if len(df) <= 100 else "⚠️ Limitado"
        st.markdown(f"""
<div class="metric-card">
  <div class="metric-value" style="font-size:1.3rem;">{status}</div>
  <div class="metric-label">Status</div>
</div>""", unsafe_allow_html=True)

    with st.expander("👁️ Visualizar dados carregados"):
        st.dataframe(df, use_container_width=True, height=250)

    st.markdown("---")

    # BOTÃO DE OTIMIZAÇÃO
    if st.button("🚀 Otimizar Rota Agora"):
        use_google = "Google" in engine and credentials_json and project_id

        with st.spinner("⚡ Calculando a rota mais eficiente..."):
            if use_google:
                route_order, error = optimize_route_google(df, credentials_json, project_id)
                if error:
                    st.warning(f"Google API falhou: {error}\n\nUsando algoritmo local como fallback...")
                    route_order, total_km, D = optimize_route_local(df)
                    used_engine = "🧠 Algoritmo Local (fallback)"
                else:
                    D = build_distance_matrix(df)
                    total_km = route_distance(route_order, D)
                    used_engine = "☁️ Google Fleet Routing"
            else:
                route_order, total_km, D = optimize_route_local(df)
                used_engine = "🧠 Algoritmo Local (Nearest Neighbor + 2-opt)"

        st.success(f"✅ Rota otimizada com sucesso! Motor usado: **{used_engine}**")

        # Métricas da rota
        st.markdown("### 🗺️ Resultado da Otimização")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown(f"""
<div class="metric-card">
  <div class="metric-value">{total_km:.1f} km</div>
  <div class="metric-label">Distância total estimada</div>
</div>""", unsafe_allow_html=True)
        with r2:
            avg_speed = 30  # km/h média urbana
            tempo_h = total_km / avg_speed
            horas = int(tempo_h)
            mins = int((tempo_h - horas) * 60)
            st.markdown(f"""
<div class="metric-card">
  <div class="metric-value">{horas}h {mins}min</div>
  <div class="metric-label">Tempo estimado (30 km/h)</div>
</div>""", unsafe_allow_html=True)
        with r3:
            st.markdown(f"""
<div class="metric-card">
  <div class="metric-value">{len(df)}</div>
  <div class="metric-label">Paradas na rota</div>
</div>""", unsafe_allow_html=True)

        # MAPA
        st.markdown("#### 📍 Mapa da Rota Otimizada")
        mapa, ordered_df = build_map(df, route_order)
        st_folium(mapa, use_container_width=True, height=550)

        # TABELA DE ORDEM
        st.markdown("#### 📋 Ordem das Paradas")
        ordered_df_display = ordered_df.copy()
        ordered_df_display.insert(0, 'Ordem', range(1, len(ordered_df_display)+1))
        st.dataframe(ordered_df_display, use_container_width=True, height=300)

        # EXPORT
        buf_out = io.BytesIO()
        ordered_df_display.to_excel(buf_out, index=False)
        st.download_button(
            "📥 Baixar rota otimizada (.xlsx)",
            data=buf_out.getvalue(),
            file_name="rota_otimizada.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    # Estado vazio — instrução visual
    st.markdown("""
<div style="text-align:center;padding:60px 20px;color:#8b949e;">
  <div style="font-size:4rem;margin-bottom:16px;">📂</div>
  <h3 style="color:#e6edf3;">Carregue sua planilha para começar</h3>
  <p>Formatos aceitos: <strong>.xlsx</strong> ou <strong>.csv</strong></p>
  <p>Baixe a planilha modelo na barra lateral ←</p>
</div>
""", unsafe_allow_html=True)
