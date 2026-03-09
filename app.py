import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
import json
import io

st.set_page_config(
    page_title="Router Master Pro",
    layout="centered",
    page_icon="🚚",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CSS MOBILE-FIRST
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0f1117; color: #f0f2f6; }

/* Esconde sidebar */
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* Container centralizado mobile */
.block-container { padding: 0 1rem 4rem !important; max-width: 500px !important; }

/* Header */
.app-header {
    background: linear-gradient(135deg, #1a1f2e, #0f1117);
    border-bottom: 1px solid #2d3748;
    padding: 18px 16px 14px;
    text-align: center;
    margin: -1rem -1rem 1.2rem -1rem;
}
.app-header h1 { font-size: 1.35rem; font-weight: 800; color: #fff; margin: 0; }
.app-header p  { font-size: 0.72rem; color: #718096; margin: 4px 0 0; }

/* Cards de métrica lado a lado */
.metric-row { display: flex; gap: 8px; margin: 12px 0; }
.metric-card {
    flex: 1;
    background: #1a1f2e;
    border: 1px solid #2d3748;
    border-radius: 12px;
    padding: 12px 6px;
    text-align: center;
}
.metric-value { font-size: 1.25rem; font-weight: 800; color: #63b3ed; line-height: 1; }
.metric-label { font-size: 0.6rem; color: #718096; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }

/* Botão principal — grande para dedo */
div[data-testid="stButton"] > button {
    width: 100% !important;
    background: linear-gradient(135deg, #38a169, #48bb78) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    padding: 0.95rem !important;
    margin: 8px 0 !important;
    box-shadow: 0 4px 18px rgba(72,187,120,0.3) !important;
}
div[data-testid="stDownloadButton"] > button {
    width: 100% !important;
    background: #1a1f2e !important;
    color: #63b3ed !important;
    border: 1.5px solid #2d3748 !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.8rem !important;
}

/* Upload */
[data-testid="stFileUploader"] {
    border: 2px dashed #2d3748;
    border-radius: 14px;
    padding: 6px;
    background: #1a1f2e;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid #2d3748 !important;
    border-radius: 12px !important;
    background: #1a1f2e !important;
    margin-bottom: 12px !important;
}

/* Section title */
.section-title {
    font-size: 0.78rem; font-weight: 700; color: #a0aec0;
    text-transform: uppercase; letter-spacing: 1px; margin: 18px 0 8px;
}

/* Success box */
.success-box {
    background: #1c3829; border: 1px solid #38a169;
    border-radius: 12px; padding: 11px 14px;
    font-size: 0.88rem; color: #68d391; margin: 10px 0;
}

/* Engine badge */
.engine-badge {
    display: inline-block; background: #1a1f2e;
    border: 1px solid #2d3748; border-radius: 20px;
    padding: 3px 11px; font-size: 0.72rem; color: #a0aec0; margin-bottom: 10px;
}

/* Lista de paradas */
.stop-item {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 0; border-bottom: 1px solid #1a1f2e;
}
.stop-badge {
    width: 30px; height: 30px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 800; font-size: 0.82rem; flex-shrink: 0;
}
.stop-name { font-size: 0.88rem; font-weight: 600; color: #e2e8f0; }
.stop-orig { font-size: 0.72rem; color: #718096; }

/* Estado vazio */
.empty-state {
    text-align: center; padding: 40px 16px; color: #718096;
}
.empty-state .icon { font-size: 3rem; margin-bottom: 10px; }
.empty-state h3 { font-size: 0.95rem; color: #a0aec0; margin: 0 0 6px; }
.empty-state p { font-size: 0.82rem; margin: 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ALGORITMOS
# ─────────────────────────────────────────────
def _haversine_matrix(lats, lons):
    n = len(lats)
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
    return D

def build_osrm_duration_matrix(df, progress_cb=None):
    import urllib.request, socket
    lats = df['Latitude'].values
    lons = df['Longitude'].values
    n = len(lats)
    # Teste de conectividade rápido
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("router.project-osrm.org", 80))
        sock.close()
    except Exception:
        if progress_cb: progress_cb(1, 1)
        return _haversine_matrix(lats, lons), "haversine"

    coords_all = [f"{lons[i]},{lats[i]}" for i in range(n)]
    D = np.full((n, n), 99999.0)
    np.fill_diagonal(D, 0)
    BLOCK = 15
    src_blocks = [list(range(i, min(i+BLOCK, n))) for i in range(0, n, BLOCK)]
    try:
        for bi, src_block in enumerate(src_blocks):
            if progress_cb: progress_cb(bi, len(src_blocks))
            all_idx    = sorted(set(src_block) | set(range(n)))
            idx_map    = {v: k for k, v in enumerate(all_idx)}
            coords_str = ";".join(coords_all[i] for i in all_idx)
            sources    = ";".join(str(idx_map[i]) for i in src_block)
            dests      = ";".join(str(idx_map[i]) for i in range(n))
            url = (f"https://router.project-osrm.org/table/v1/driving/{coords_str}"
                   f"?sources={sources}&destinations={dests}&annotations=duration")
            req = urllib.request.Request(url, headers={"User-Agent": "RouterMasterPro/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode())
            if data.get("code") != "Ok":
                raise ValueError("non-Ok")
            mat = np.array(data["durations"], dtype=float)
            for li, gi in enumerate(src_block):
                D[gi, :] = np.where(np.isnan(mat[li]), 99999, mat[li])
        return D, "osrm"
    except Exception:
        return _haversine_matrix(lats, lons), "haversine"

def route_distance(route, D):
    return sum(D[route[i]][route[i+1]] for i in range(len(route)-1))

def nearest_neighbor(D, start=0):
    n = len(D)
    unvisited = list(range(n))
    route = [start]; unvisited.remove(start)
    while unvisited:
        last = route[-1]
        nearest = min(unvisited, key=lambda x: D[last][x])
        route.append(nearest); unvisited.remove(nearest)
    return route

def two_opt(route, D):
    best = route[:]
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 2, len(best)):
                delta = (- D[best[i-1]][best[i]] - D[best[j-1]][best[j]]
                         + D[best[i-1]][best[j-1]] + D[best[i]][best[j]])
                if delta < -1e-10:
                    best[i:j] = best[i:j][::-1]; improved = True
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
                    best = candidate; improved = True; break
            if improved: break
    return best

def optimize_route_local(df, progress_cb=None):
    D, src = build_osrm_duration_matrix(df, progress_cb=progress_cb)
    n = len(df)
    best_route, best_time = None, float('inf')
    for start in range(min(n, 8)):
        route = nearest_neighbor(D, start=start)
        if start != 0:
            idx0 = route.index(0)
            route = route[idx0:] + route[:idx0]
        route = two_opt(route, D)
        for seg in (1, 2, 3):
            route = or_opt(route, D, seg_len=seg)
        route = two_opt(route, D)
        t = route_distance(route, D)
        if t < best_time:
            best_time = t; best_route = route
    return best_route, best_time, D, src

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
                start_location={"latitude": float(df.iloc[0]['Latitude']),
                                "longitude": float(df.iloc[0]['Longitude'])},
                label="Veiculo_1"
            )]
        )
        request = optimization_v1.OptimizeToursRequest(
            parent=f"projects/{project_id}", model=model)
        response = client.optimize_tours(request=request)
        route_indices = [v.shipment_index for r in response.routes for v in r.visits]
        return route_indices, None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# ROTA PELAS RUAS
# ─────────────────────────────────────────────
def get_road_route(coords_lonlat):
    import urllib.request
    road_coords = []
    chunk_size = 25
    for start in range(0, len(coords_lonlat) - 1, chunk_size - 1):
        chunk = coords_lonlat[start:start + chunk_size]
        if len(chunk) < 2: break
        coords_str = ";".join(f"{lon},{lat}" for lon, lat in chunk)
        url = (f"https://router.project-osrm.org/route/v1/driving/{coords_str}"
               f"?overview=full&geometries=geojson&steps=false")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RouterMasterPro/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            if data.get("code") == "Ok":
                geom = data["routes"][0]["geometry"]["coordinates"]
                segment = [(pt[1], pt[0]) for pt in geom]
                road_coords.extend(segment[1:] if road_coords else segment)
            else:
                road_coords.extend([(lat, lon) for lon, lat in chunk])
        except Exception:
            road_coords.extend([(lat, lon) for lon, lat in chunk])
    return road_coords

# ─────────────────────────────────────────────
# MAPA
# ─────────────────────────────────────────────
def build_map(df, route_order, use_roads=True):
    ordered = df.iloc[route_order].reset_index(drop=True)
    m = folium.Map(location=[ordered['Latitude'].mean(), ordered['Longitude'].mean()],
                   zoom_start=13, tiles='CartoDB dark_matter')

    coords_lonlat = list(zip(ordered['Longitude'], ordered['Latitude']))
    road_path = get_road_route(coords_lonlat) if use_roads else [(lat, lon) for lon, lat in coords_lonlat]
    folium.PolyLine(road_path, color='#63b3ed', weight=4, opacity=0.9).add_to(m)

    for idx, (original_idx, row) in enumerate(ordered.iterrows()):
        ordem_otimizada = idx + 1
        ordem_original  = original_idx + 1
        label = row.get('Nome', f'Parada {ordem_otimizada}')
        if idx == 0:
            cor_topo, cor_base = '#48bb78', '#276749'
        elif idx == len(ordered) - 1:
            cor_topo, cor_base = '#fc8181', '#742a2a'
        else:
            cor_topo, cor_base = '#63b3ed', '#1a365d'
        w = 34
        div_html = f"""<div style="width:{w}px;height:{w}px;border-radius:50%;overflow:hidden;
            border:2px solid rgba(255,255,255,0.3);box-shadow:0 2px 8px rgba(0,0,0,0.6);
            display:flex;flex-direction:column;font-family:Inter,sans-serif;">
          <div style="flex:1;background:{cor_topo};display:flex;align-items:center;
            justify-content:center;color:#fff;font-weight:800;font-size:11px;
            border-bottom:1px solid rgba(255,255,255,0.3);">{ordem_otimizada}</div>
          <div style="flex:1;background:{cor_base};display:flex;align-items:center;
            justify-content:center;color:rgba(255,255,255,0.8);font-size:9px;font-weight:600;">
            {ordem_original}</div></div>"""
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(f"<b>#{ordem_otimizada} — {label}</b><br><small>Original: #{ordem_original}</small>", max_width=200),
            tooltip=f"#{ordem_otimizada} {label}",
            icon=folium.DivIcon(html=div_html, icon_size=(w, w), icon_anchor=(w//2, w//2))
        ).add_to(m)
    return m, ordered

# ─────────────────────────────────────────────
# INTERFACE
# ─────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <h1>🚚 Router Master Pro</h1>
  <p>GMPRO · Roterizador inteligente para entregas</p>
</div>
""", unsafe_allow_html=True)

if "resultado" not in st.session_state:
    st.session_state.resultado = None

# Configurações colapsadas
with st.expander("⚙️ Configurações"):
    engine = st.radio("Motor", ["🧠 Algoritmo Local (gratuito)", "☁️ Google Fleet Routing (API)"])
    use_roads = st.toggle("🛣️ Rota pelas ruas reais", value=True)

    if "Google" in engine:
        project_id = st.text_input("Project ID", placeholder="meu-projeto-123")
        credentials_file = st.file_uploader("JSON Google Cloud", type=['json'])
        credentials_json = credentials_file.read().decode() if credentials_file else None
        if not credentials_json:
            st.warning("⚠️ Sem JSON usará algoritmo local.")
    else:
        project_id = None
        credentials_json = None

    st.markdown("---")
    sample = pd.DataFrame({
        'Nome': ['Depósito', 'Cliente A', 'Cliente B', 'Cliente C'],
        'Latitude': [-19.9245, -19.9312, -19.9180, -19.9400],
        'Longitude': [-43.9352, -43.9401, -43.9280, -43.9500],
    })
    buf = io.BytesIO()
    sample.to_excel(buf, index=False)
    st.download_button("📥 Planilha modelo", data=buf.getvalue(),
                       file_name="modelo_paradas.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Upload
uploaded_file = st.file_uploader("📂 Planilha de paradas (.xlsx ou .csv)",
                                  type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Erro: {e}"); st.stop()

    if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
        st.error("❌ Precisa ter colunas Latitude e Longitude."); st.stop()

    df = df.dropna(subset=['Latitude', 'Longitude']).reset_index(drop=True)
    if len(df) < 2: st.error("❌ Mínimo 2 paradas."); st.stop()
    if len(df) > 100:
        st.warning(f"⚠️ Limitando às primeiras 100 de {len(df)}."); df = df.head(100)

    st.markdown(f"""
<div class="metric-row">
  <div class="metric-card">
    <div class="metric-value">{len(df)}</div>
    <div class="metric-label">Paradas</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">✅</div>
    <div class="metric-label">Pronto</div>
  </div>
</div>""", unsafe_allow_html=True)

    if st.button("🚀  OTIMIZAR ROTA AGORA"):
        use_google = "Google" in engine and credentials_json and project_id
        prog_bar  = st.progress(0)
        prog_text = st.empty()

        def update_progress(bi, total):
            prog_bar.progress(max(1, int((bi / total) * 75)))
            prog_text.markdown(f"🛣️ OSRM: bloco {bi+1}/{total}...")

        prog_text.markdown("⏳ Calculando rota otimizada...")

        if use_google:
            route_order, error = optimize_route_google(df, credentials_json, project_id)
            if error:
                route_order, total_km, D, src = optimize_route_local(df, progress_cb=update_progress)
                used_engine = f"🧠 Local ({'OSRM' if src=='osrm' else 'Haversine'})"
            else:
                _, _, D, _ = optimize_route_local(df, progress_cb=update_progress)
                total_km = route_distance(route_order, D)
                used_engine = "☁️ Google Fleet Routing"
        else:
            route_order, total_km, D, src = optimize_route_local(df, progress_cb=update_progress)
            used_engine = "🧠 OSRM + 2-opt" if src == "osrm" else "🧠 Haversine + 2-opt"

        prog_bar.progress(100); prog_text.empty(); prog_bar.empty()

        _, ordered_df = build_map(df, route_order, use_roads=use_roads)
        ordered_df_display = ordered_df.copy()
        ordered_df_display.insert(0, 'Ordem', range(1, len(ordered_df_display)+1))

        st.session_state.resultado = {
            "route_order": route_order, "total_km": total_km,
            "used_engine": used_engine, "ordered_df": ordered_df_display,
            "df": df, "use_roads": use_roads,
        }

    # Resultado
    if st.session_state.resultado is not None:
        res = st.session_state.resultado
        route_order        = res["route_order"]
        total_km           = res["total_km"]
        used_engine        = res["used_engine"]
        ordered_df_display = res["ordered_df"]
        df_res             = res["df"]
        use_roads_res      = res.get("use_roads", True)

        horas = int(total_km // 3600)
        mins  = int((total_km % 3600) // 60)

        st.markdown(f'<div class="success-box">✅ Rota pronta! {horas}h {mins}min · {len(df_res)} paradas</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="engine-badge">{used_engine}</div>', unsafe_allow_html=True)

        st.markdown(f"""
<div class="metric-row">
  <div class="metric-card">
    <div class="metric-value">{horas}h {mins}m</div>
    <div class="metric-label">Duração total</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{len(df_res)}</div>
    <div class="metric-label">Paradas</div>
  </div>
</div>""", unsafe_allow_html=True)

        # Mapa
        mapa, _ = build_map(df_res, route_order, use_roads=use_roads_res)
        st_folium(mapa, use_container_width=True, height=420, returned_objects=[])

        # Lista de paradas (melhor que tabela no celular)
        st.markdown('<div class="section-title">📋 Ordem das paradas</div>', unsafe_allow_html=True)
        stops_html = ""
        for _, row in ordered_df_display.iterrows():
            ordem = int(row['Ordem'])
            nome  = str(row.get('Nome', f'Parada {ordem}'))
            total_stops = len(ordered_df_display)
            if ordem == 1:
                bg = '#276749'
            elif ordem == total_stops:
                bg = '#742a2a'
            else:
                bg = '#1a365d'
            stops_html += f"""
            <div class="stop-item">
              <div class="stop-badge" style="background:{bg};">{ordem}</div>
              <div>
                <div class="stop-name">{nome}</div>
              </div>
            </div>"""
        st.markdown(stops_html, unsafe_allow_html=True)

        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        buf_out = io.BytesIO()
        ordered_df_display.to_excel(buf_out, index=False)
        st.download_button("📥 Baixar rota (.xlsx)", data=buf_out.getvalue(),
                           file_name="rota_otimizada.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.markdown("""
<div class="empty-state">
  <div class="icon">📂</div>
  <h3>Nenhuma planilha carregada</h3>
  <p>Suba um .xlsx ou .csv com colunas<br><b>Latitude</b> e <b>Longitude</b></p>
</div>""", unsafe_allow_html=True)
