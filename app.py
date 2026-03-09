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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0f1117; color: #f0f2f6; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 0 1rem 4rem !important; max-width: 500px !important; }
.app-header {
    background: #1a1f2e; border-bottom: 1px solid #2d3748;
    padding: 18px 16px 14px; text-align: center;
    margin: -1rem -1rem 1.2rem -1rem;
}
.app-header h1 { font-size: 1.35rem; font-weight: 800; color: #fff; margin: 0; }
.app-header p  { font-size: 0.72rem; color: #718096; margin: 4px 0 0; }
.metric-row { display: flex; gap: 8px; margin: 12px 0; }
.metric-card {
    flex: 1; background: #1a1f2e; border: 1px solid #2d3748;
    border-radius: 12px; padding: 12px 6px; text-align: center;
}
.metric-value { font-size: 1.25rem; font-weight: 800; color: #63b3ed; line-height: 1; }
.metric-label { font-size: 0.6rem; color: #718096; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
div[data-testid="stButton"] > button {
    width: 100% !important; background: linear-gradient(135deg,#38a169,#48bb78) !important;
    color: white !important; border: none !important; border-radius: 14px !important;
    font-weight: 700 !important; font-size: 1.05rem !important; padding: 0.95rem !important;
    margin: 8px 0 !important; box-shadow: 0 4px 18px rgba(72,187,120,0.3) !important;
}
div[data-testid="stDownloadButton"] > button {
    width: 100% !important; background: #1a1f2e !important; color: #63b3ed !important;
    border: 1.5px solid #2d3748 !important; border-radius: 12px !important;
    font-weight: 600 !important; font-size: 0.9rem !important; padding: 0.8rem !important;
}
.success-box {
    background: #1c3829; border: 1px solid #38a169; border-radius: 12px;
    padding: 11px 14px; font-size: 0.88rem; color: #68d391; margin: 10px 0;
}
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
.section-title {
    font-size: 0.78rem; font-weight: 700; color: #a0aec0;
    text-transform: uppercase; letter-spacing: 1px; margin: 18px 0 8px;
}
</style>
""", unsafe_allow_html=True)

# ── ALGORITMOS ────────────────────────────────────────────────────────────────

def haversine_matrix(lats, lons):
    n = len(lats)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            R = 6371000
            p1, p2 = np.radians(lats[i]), np.radians(lats[j])
            dp = np.radians(lats[j]-lats[i])
            dl = np.radians(lons[j]-lons[i])
            a  = np.sin(dp/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
            D[i][j] = D[j][i] = 2*6371000*np.arcsin(np.sqrt(a)) / 8.33
    return D

def nearest_neighbor(D):
    n = len(D)
    unvisited = list(range(1, n))
    route = [0]
    while unvisited:
        last = route[-1]
        nxt  = min(unvisited, key=lambda x: D[last][x])
        route.append(nxt)
        unvisited.remove(nxt)
    return route

def two_opt_fast(route, D, time_limit=15):
    """2-opt com limite de tempo em segundos."""
    import time
    best = route[:]
    n    = len(best)
    deadline = time.time() + time_limit
    improved = True
    while improved and time.time() < deadline:
        improved = False
        for i in range(1, n-2):
            if time.time() > deadline:
                break
            for j in range(i+2, n):
                d = (- D[best[i-1]][best[i]] - D[best[j-1]][best[j]]
                     + D[best[i-1]][best[j-1]] + D[best[i]][best[j]])
                if d < -1e-10:
                    best[i:j] = best[i:j][::-1]
                    improved = True
    return best

def route_total(route, D):
    return sum(D[route[i]][route[i+1]] for i in range(len(route)-1))

def optimize(df):
    lats = df['Latitude'].values
    lons = df['Longitude'].values
    D    = haversine_matrix(lats, lons)
    route = nearest_neighbor(D)
    route = two_opt_fast(route, D, time_limit=20)
    return route, route_total(route, D), D

# ── MAPA ──────────────────────────────────────────────────────────────────────

def get_road_path(coords_lonlat):
    import urllib.request, socket
    try:
        s = socket.socket(); s.settimeout(2)
        s.connect(("router.project-osrm.org", 80)); s.close()
    except:
        return [(lat, lon) for lon, lat in coords_lonlat]

    road = []
    chunk = 20
    for start in range(0, len(coords_lonlat)-1, chunk-1):
        seg = coords_lonlat[start:start+chunk]
        if len(seg) < 2: break
        cs  = ";".join(f"{lo},{la}" for lo, la in seg)
        url = f"https://router.project-osrm.org/route/v1/driving/{cs}?overview=full&geometries=geojson"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RMP/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            if data.get("code") == "Ok":
                pts = [(p[1], p[0]) for p in data["routes"][0]["geometry"]["coordinates"]]
                road.extend(pts[1:] if road else pts)
            else:
                road.extend([(la, lo) for lo, la in seg])
        except:
            road.extend([(la, lo) for lo, la in seg])
    return road

def build_map(df, route_order):
    ordered = df.iloc[route_order].reset_index(drop=True)
    m = folium.Map(
        location=[ordered['Latitude'].mean(), ordered['Longitude'].mean()],
        zoom_start=13, tiles='CartoDB dark_matter'
    )
    path = get_road_path(list(zip(ordered['Longitude'], ordered['Latitude'])))
    folium.PolyLine(path, color='#63b3ed', weight=4, opacity=0.9).add_to(m)

    for idx, (orig_idx, row) in enumerate(ordered.iterrows()):
        num  = idx + 1
        orig = orig_idx + 1
        label = str(row.get('Nome', f'Parada {num}'))
        if idx == 0:             ct, cb = '#48bb78','#276749'
        elif idx==len(ordered)-1: ct, cb = '#fc8181','#742a2a'
        else:                     ct, cb = '#63b3ed','#1a365d'
        w = 34
        html = f"""<div style="width:{w}px;height:{w}px;border-radius:50%;overflow:hidden;
            border:2px solid rgba(255,255,255,0.3);box-shadow:0 2px 8px rgba(0,0,0,.6);
            display:flex;flex-direction:column;">
          <div style="flex:1;background:{ct};display:flex;align-items:center;justify-content:center;
            color:#fff;font-weight:800;font-size:11px;border-bottom:1px solid rgba(255,255,255,.3);">{num}</div>
          <div style="flex:1;background:{cb};display:flex;align-items:center;justify-content:center;
            color:rgba(255,255,255,.8);font-size:9px;font-weight:600;">{orig}</div></div>"""
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=folium.Popup(f"<b>#{num} {label}</b><br>Original: #{orig}", max_width=200),
            tooltip=f"#{num} {label}",
            icon=folium.DivIcon(html=html, icon_size=(w,w), icon_anchor=(w//2,w//2))
        ).add_to(m)
    return m, ordered

# ── INTERFACE ─────────────────────────────────────────────────────────────────

st.markdown("""
<div class="app-header">
  <h1>🚚 Router Master Pro</h1>
  <p>GMPRO · Roterizador inteligente para entregas</p>
</div>""", unsafe_allow_html=True)

if "resultado" not in st.session_state:
    st.session_state.resultado = None

# Upload — aceita CSV e XLSX
uploaded_file = st.file_uploader(
    "📂 Planilha de paradas",
    type=['csv', 'xlsx'],
    help="Colunas obrigatórias: Latitude, Longitude"
)

if uploaded_file is not None:
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            # tenta múltiplos separadores para compatibilidade mobile
            raw = uploaded_file.read()
            for sep in [',', ';', '\t']:
                try:
                    df = pd.read_csv(io.BytesIO(raw), sep=sep)
                    if len(df.columns) > 1:
                        break
                except:
                    pass
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}"); st.stop()

    # Normaliza nomes de colunas (remove espaços, ignora maiúsculas)
    df.columns = [c.strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}
    if 'latitude' not in col_map or 'longitude' not in col_map:
        st.error(f"❌ Colunas encontradas: {list(df.columns)}\nPrecisa ter Latitude e Longitude."); st.stop()
    df = df.rename(columns={col_map['latitude']: 'Latitude', col_map['longitude']: 'Longitude'})
    if 'nome' in col_map:
        df = df.rename(columns={col_map['nome']: 'Nome'})

    df = df.dropna(subset=['Latitude','Longitude']).reset_index(drop=True)
    if len(df) < 2: st.error("❌ Mínimo 2 paradas."); st.stop()
    if len(df) > 100:
        st.warning(f"⚠️ Limitando a 100 de {len(df)} paradas.")
        df = df.head(100)

    st.markdown(f"""
<div class="metric-row">
  <div class="metric-card"><div class="metric-value">{len(df)}</div>
    <div class="metric-label">Paradas</div></div>
  <div class="metric-card"><div class="metric-value">✅</div>
    <div class="metric-label">Arquivo OK</div></div>
</div>""", unsafe_allow_html=True)

    if st.button("🚀  OTIMIZAR ROTA"):
        with st.spinner("⏳ Calculando rota..."):
            route_order, total_sec, D = optimize(df)

        _, ordered_df = build_map(df, route_order)
        ordered_df.insert(0, 'Ordem', range(1, len(ordered_df)+1))

        st.session_state.resultado = {
            "route_order": route_order, "total_sec": total_sec,
            "ordered_df": ordered_df, "df": df,
        }

    if st.session_state.resultado is not None:
        res   = st.session_state.resultado
        order = res["route_order"]
        secs  = res["total_sec"]
        odf   = res["ordered_df"]
        dfr   = res["df"]

        horas = int(secs // 3600)
        mins  = int((secs % 3600) // 60)

        st.markdown(f'<div class="success-box">✅ Rota pronta! {horas}h {mins}min · {len(dfr)} paradas</div>',
                    unsafe_allow_html=True)
        st.markdown(f"""
<div class="metric-row">
  <div class="metric-card"><div class="metric-value">{horas}h {mins}m</div>
    <div class="metric-label">Duração estimada</div></div>
  <div class="metric-card"><div class="metric-value">{len(dfr)}</div>
    <div class="metric-label">Paradas</div></div>
</div>""", unsafe_allow_html=True)

        mapa, _ = build_map(dfr, order)
        st_folium(mapa, use_container_width=True, height=420, returned_objects=[])

        st.markdown('<div class="section-title">📋 Ordem das paradas</div>', unsafe_allow_html=True)
        stops_html = ""
        total_stops = len(odf)
        for _, row in odf.iterrows():
            num  = int(row['Ordem'])
            nome = str(row.get('Nome', f'Parada {num}'))
            bg   = '#276749' if num==1 else ('#742a2a' if num==total_stops else '#1a365d')
            stops_html += f"""<div class="stop-item">
              <div class="stop-badge" style="background:{bg};">{num}</div>
              <div class="stop-name">{nome}</div></div>"""
        st.markdown(stops_html, unsafe_allow_html=True)

        buf = io.BytesIO()
        odf.to_excel(buf, index=False)
        st.download_button("📥 Baixar rota (.xlsx)", data=buf.getvalue(),
                           file_name="rota_otimizada.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.markdown("""
<div style="text-align:center;padding:40px 16px;color:#718096;">
  <div style="font-size:3rem;margin-bottom:10px;">📂</div>
  <div style="font-size:1rem;font-weight:600;color:#a0aec0;margin-bottom:6px;">Nenhuma planilha carregada</div>
  <div style="font-size:0.82rem;">Suba um .xlsx ou .csv com colunas<br><b>Latitude</b> e <b>Longitude</b></div>
</div>""", unsafe_allow_html=True)
