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
# MATRIZ DE TEMPO REAL VIA OSRM TABLE API
# (respeita mão das ruas, sentido de tráfego)
# ─────────────────────────────────────────────
def build_osrm_duration_matrix(df, progress_cb=None):
    """
    Usa OSRM Table API em blocos de 25 pontos para não travar.
    Monta a matriz n×n completa combinando os blocos.
    Fallback para haversine se OSRM falhar.
    """
    import urllib.request

    lats = df['Latitude'].values
    lons = df['Longitude'].values
    n = len(lats)
    coords_all = [(lons[i], lats[i]) for i in range(n)]

    # Tenta OSRM com todos os pontos de uma vez (funciona bem até ~50 pontos)
    def osrm_request(src_indices, dst_indices):
        all_idx = sorted(set(src_indices) | set(dst_indices))
        idx_map = {v: k for k, v in enumerate(all_idx)}
        coords_str = ";".join(f"{coords_all[i][0]},{coords_all[i][1]}" for i in all_idx)
        sources = ";".join(str(idx_map[i]) for i in src_indices)
        dests   = ";".join(str(idx_map[i]) for i in dst_indices)
        url = (
            f"https://router.project-osrm.org/table/v1/driving/{coords_str}"
            f"?sources={sources}&destinations={dests}&annotations=duration"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "RouterMasterPro/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") == "Ok":
            return np.array(data["durations"], dtype=float)
        return None

    D = np.full((n, n), 99999.0)
    np.fill_diagonal(D, 0)

    BLOCK = 20  # blocos de 20 para garantir resposta rápida
    src_blocks = [list(range(i, min(i+BLOCK, n))) for i in range(0, n, BLOCK)]
    total_blocks = len(src_blocks)

    osrm_ok = False
    try:
        for bi, src_block in enumerate(src_blocks):
            if progress_cb:
                progress_cb(bi, total_blocks)
            mat = osrm_request(src_block, list(range(n)))
            if mat is not None:
                for local_i, global_i in enumerate(src_block):
                    row = mat[local_i]
                    row = np.where(np.isnan(row), 99999, row)
                    D[global_i, :] = row
                osrm_ok = True
            else:
                raise Exception("OSRM returned non-Ok")
    except Exception:
        osrm_ok = False

    if osrm_ok:
        return D, "osrm"

    # Fallback haversine (30 km/h)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            R = 6371000
            phi1, phi2 = np.radians(lats[i]), np.radians(lats[j])
            dphi = np.radians(lats[j] - lats[i])
            dlam = np.radians(lons[j] - lons[i])
            a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlam/2)**2
            dist_m = 2 * R * np.arcsin(np.sqrt(a))
            D[i][j] = D[j][i] = dist_m / 8.33
    return D, "haversine"

def route_distance(route, D):
    return sum(D[route[i]][route[i+1]] for i in range(len(route)-1))

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

def two_opt(route, D):
    best = route[:]
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 2, len(best)):
                delta = (
                    - D[best[i-1]][best[i]]   - D[best[j-1]][best[j]]
                    + D[best[i-1]][best[j-1]] + D[best[i]][best[j]]
                )
                if delta < -1e-10:
                    best[i:j] = best[i:j][::-1]
                    improved = True
    return best

def or_opt(route, D, seg_len=1):
    best = route[:]
    improved = True
    while improved:
        improved = False
        n = len(best)
        for i in range(1, n - seg_len):
            seg = best[i:i+seg_len]
            rest = best[:i] + best[i+seg_len:]
            base = route_distance(best, D)
            for j in range(1, len(rest)):
                candidate = rest[:j] + seg + rest[j:]
                if route_distance(candidate, D) < base - 1e-10:
                    best = candidate
                    improved = True
                    break
            if improved:
                break
    return best

def optimize_route_local(df, progress_cb=None):
    D, matrix_source = build_osrm_duration_matrix(df, progress_cb=progress_cb)
    n = len(df)

    best_route = None
    best_time  = float('inf')

    # Multi-start com até 8 pontos de partida diferentes
    for start in range(min(n, 8)):
        route = nearest_neighbor(D, start=start)
        # Garante que depósito (índice 0) sempre seja o início
        if start != 0:
            idx0 = route.index(0)
            route = route[idx0:] + route[:idx0]
        route = two_opt(route, D)
        for seg in (1, 2, 3):
            route = or_opt(route, D, seg_len=seg)
        route = two_opt(route, D)
        t = route_distance(route, D)
        if t < best_time:
            best_time  = t
            best_route = route

    return best_route, best_time, D, matrix_source

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
# ROTA PELAS RUAS REAIS (OSRM — gratuito, sem API key)
# ─────────────────────────────────────────────
def get_road_route(coords_lonlat):
    import urllib.request
    road_coords = []
    chunk_size = 25
    for start in range(0, len(coords_lonlat) - 1, chunk_size - 1):
        chunk = coords_lonlat[start:start + chunk_size]
        if len(chunk) < 2:
            break
        coords_str = ";".join(f"{lon},{lat}" for lon, lat in chunk)
        url = (
            f"https://router.project-osrm.org/route/v1/driving/{coords_str}"
            f"?overview=full&geometries=geojson&steps=false"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RouterMasterPro/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data.get("code") == "Ok":
                geom = data["routes"][0]["geometry"]["coordinates"]
                segment = [(pt[1], pt[0]) for pt in geom]
                if road_coords:
                    road_coords.extend(segment[1:])
                else:
                    road_coords.extend(segment)
            else:
                road_coords.extend([(lat, lon) for lon, lat in chunk])
        except Exception:
            road_coords.extend([(lat, lon) for lon, lat in chunk])
    return road_coords


# ─────────────────────────────────────────────
# CONSTRUÇÃO DO MAPA
# ─────────────────────────────────────────────
def build_map(df, route_order, use_roads=True):
    ordered = df.iloc[route_order].reset_index(drop=True)
    center_lat = ordered['Latitude'].mean()
    center_lon = ordered['Longitude'].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='CartoDB dark_matter'
    )

    # ── Traçado da rota ──────────────────────────────────────────────────
    coords_lonlat = list(zip(ordered['Longitude'], ordered['Latitude']))
    if use_roads:
        road_path = get_road_route(coords_lonlat)
    else:
        road_path = [(lat, lon) for lon, lat in coords_lonlat]

    folium.PolyLine(
        road_path,
        color='#58a6ff',
        weight=4,
        opacity=0.85,
    ).add_to(m)

    # ── Marcadores bicolor: topo = ordem otimizada, base = ordem original ──
    for idx, (original_idx, row) in enumerate(ordered.iterrows()):
        ordem_otimizada = idx + 1
        ordem_original  = original_idx + 1
        label = row.get('Nome', f'Parada {ordem_otimizada}')

        if idx == 0:
            cor_topo, cor_base = '#3fb950', '#1a6b2a'
        elif idx == len(ordered) - 1:
            cor_topo, cor_base = '#f85149', '#8b1a1a'
        else:
            cor_topo, cor_base = '#58a6ff', '#1a3a6b'

        w = 34
        div_html = f"""
        <div style="
            width:{w}px; height:{w}px;
            border-radius:50%;
            overflow:hidden;
            border:2.5px solid rgba(255,255,255,0.25);
            box-shadow:0 2px 8px rgba(0,0,0,0.6);
            display:flex; flex-direction:column;
            font-family:'Space Grotesk',Arial,sans-serif;
        ">
          <div style="
            flex:1; background:{cor_topo};
            display:flex; align-items:center; justify-content:center;
            color:#fff; font-weight:800; font-size:11px;
            border-bottom:1px solid rgba(255,255,255,0.3);
            line-height:1;
          ">{ordem_otimizada}</div>
          <div style="
            flex:1; background:{cor_base};
            display:flex; align-items:center; justify-content:center;
            color:rgba(255,255,255,0.8); font-weight:600; font-size:9px;
            line-height:1;
          ">{ordem_original}</div>
        </div>
        """

        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(
                f"<b style='font-size:13px'>#{ordem_otimizada} — {label}</b><br>"
                f"<span style='color:#888;font-size:11px'>Posição original: #{ordem_original}</span>",
                max_width=230
            ),
            tooltip=f"#{ordem_otimizada} {label} (orig #{ordem_original})",
            icon=folium.DivIcon(
                html=div_html,
                icon_size=(w, w),
                icon_anchor=(w // 2, w // 2),
            )
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
    use_roads = st.toggle(
        "🛣️ Traçar rota pelas ruas reais",
        value=True,
        help="Usa o OSRM (gratuito, sem API key). Desative se estiver lento."
    )

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

    # ── Inicializa session_state ──────────────────────────────────────────
    if "resultado" not in st.session_state:
        st.session_state.resultado = None

    # BOTÃO DE OTIMIZAÇÃO
    if st.button("🚀 Otimizar Rota Agora"):
        use_google = "Google" in engine and credentials_json and project_id

        prog_bar  = st.progress(0)
        prog_text = st.empty()

        def update_progress(bi, total):
            pct = max(1, int((bi / total) * 75))
            prog_bar.progress(pct)
            prog_text.markdown(f"🛣️ Consultando OSRM: bloco {bi+1} de {total}...")

        prog_text.markdown("🛣️ Consultando tempos reais de deslocamento via OSRM...")

        if use_google:
            route_order, error = optimize_route_google(df, credentials_json, project_id)
            if error:
                st.warning(f"Google API falhou: {error} — usando algoritmo local...")
                route_order, total_km, D, src = optimize_route_local(df, progress_cb=update_progress)
                used_engine = f"🧠 Fallback ({'OSRM' if src=='osrm' else 'Haversine'})"
            else:
                _, _, D, _ = optimize_route_local(df, progress_cb=update_progress)
                total_km = route_distance(route_order, D)
                used_engine = "☁️ Google Fleet Routing"
        else:
            route_order, total_km, D, src = optimize_route_local(df, progress_cb=update_progress)
            used_engine = "🧠 OSRM + 2-opt + Or-opt" if src == "osrm" else "🧠 Algoritmo Local (Haversine)"

        prog_bar.progress(90)
        prog_text.markdown("🧠 Finalizando otimização da rota...")
        prog_bar.progress(100)
        prog_text.empty()
        prog_bar.empty()
        # Salva resultado no session_state para sobreviver a re-renders
        _, ordered_df = build_map(df, route_order, use_roads=use_roads)
        ordered_df_display = ordered_df.copy()
        ordered_df_display.insert(0, 'Ordem', range(1, len(ordered_df_display)+1))

        st.session_state.resultado = {
            "route_order": route_order,
            "total_km": total_km,
            "used_engine": used_engine,
            "ordered_df": ordered_df_display,
            "df": df,
            "use_roads": use_roads,
        }

    # ── Exibe resultado persistido ────────────────────────────────────────
    if st.session_state.resultado is not None:
        res = st.session_state.resultado
        route_order  = res["route_order"]
        total_km     = res["total_km"]
        used_engine  = res["used_engine"]
        ordered_df_display = res["ordered_df"]
        df_res       = res["df"]
        use_roads_res = res.get("use_roads", True)

        st.success(f"✅ Rota otimizada! Motor: **{used_engine}**")

        # Métricas da rota
        st.markdown("### 🗺️ Resultado da Otimização")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown(f"""
<div class="metric-card">
  <div class="metric-value">{int(total_km//3600)}h {int((total_km%3600)//60)}min</div>
  <div class="metric-label">Duração total da rota</div>
</div>""", unsafe_allow_html=True)
        with r2:
            # total_km aqui é na verdade segundos de duração real
            horas = int(total_km // 3600)
            mins  = int((total_km % 3600) // 60)
            st.markdown(f"""
<div class="metric-card">
  <div class="metric-value">{horas}h {mins}min</div>
  <div class="metric-label">Tempo estimado (ruas reais)</div>
</div>""", unsafe_allow_html=True)
        with r3:
            st.markdown(f"""
<div class="metric-card">
  <div class="metric-value">{len(df_res)}</div>
  <div class="metric-label">Paradas na rota</div>
</div>""", unsafe_allow_html=True)

        # MAPA — recriado a cada render mas com dados do session_state
        st.markdown("#### 📍 Mapa da Rota Otimizada")
        mapa, _ = build_map(df_res, route_order, use_roads=use_roads_res)
        st_folium(mapa, use_container_width=True, height=550, returned_objects=[])

        # TABELA DE ORDEM
        st.markdown("#### 📋 Ordem das Paradas")
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
