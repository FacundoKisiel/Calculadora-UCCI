import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Servicio de Cardiología - UCC I", 
    layout="wide", 
    page_icon="🏥"
)

# 2. ESTILO VISUAL
st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle, #1e2024 0%, #0c0d0f 100%); color: #e0e0e0; }
    [data-testid="stVerticalBlockBorderWrapper"] { 
        background: #181a1d !important; 
        border: 1px solid #2d2d2d !important; 
        border-radius: 15px; padding: 20px; margin-bottom: 15px;
    }
    [data-testid="stMetricValue"] { color: #00e676 !important; font-family: 'JetBrains Mono', monospace; }
    .stButton>button { border-radius: 10px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # ttl=0 fuerza a leer de la nube sin usar memoria vieja
        df_p = conn.read(worksheet="Pacientes", ttl=0)
        df_b = conn.read(worksheet="Bombas", ttl=0)
        
        # Limpieza: eliminamos filas totalmente vacías
        df_p = df_p.dropna(how='all')
        df_b = df_b.dropna(how='all')
        
        # Normalizamos la columna 'cama' a texto para que los filtros funcionen
        if not df_p.empty: df_p["cama"] = df_p["cama"].astype(str)
        if not df_b.empty: df_b["cama"] = df_b["cama"].astype(str)
        
        return df_p, df_b
    except Exception:
        return pd.DataFrame(columns=["cama", "peso"]), pd.DataFrame(columns=["cama", "droga", "mg", "vol", "modo", "ritmo", "dosis", "timestamp"])

# 4. SEGURIDAD
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.markdown("<h2 style='text-align: center;'>ESTACIÓN CENTRAL UCC I</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        p_in = st.text_input("CÓDIGO DE ACCESO:", type="password")
        if st.button("AUTENTICAR") or p_in == "UCCICARDIOLOGIA.":
            if p_in == "UCCICARDIOLOGIA.":
                st.session_state["password_correct"] = True
                st.rerun()
    st.stop()

# 5. CARGA INICIAL
df_pacientes, df_bombas = cargar_datos()

# 6. PANEL LATERAL
with st.sidebar:
    st.header("⚙️ Gestión de Cama")
    cama_input = st.number_input("N° de Cama", min_value=1, step=1)
    peso_input = st.number_input("Peso (kg)", min_value=1.0, value=70.0)

    if st.button("Registrar / Actualizar Paciente"):
        nueva_fila = pd.DataFrame([{"cama": str(cama_input), "peso": peso_input}])
        df_act = pd.concat([df_pacientes, nueva_fila]).drop_duplicates(subset=["cama"], keep="last")
        conn.update(worksheet="Pacientes", data=df_act)
        st.cache_data.clear()
        st.success(f"Unidad {cama_input} sincronizada")
        st.rerun()
    
    st.divider()
    if st.button("🔄 Sincronizar Red"):
        st.cache_data.clear()
        st.rerun()

# 7. MONITOR PRINCIPAL
st.title("Monitor de Infusiones - Red UCC I")

if df_pacientes.empty:
    st.info("No hay pacientes registrados. Use el panel lateral.")
else:
    # Obtener lista de camas única y limpia
    camas_ids = sorted(df_pacientes["cama"].unique(), key=lambda x: int(float(x)))
    tabs = st.tabs([f"Unidad {c}" for c in camas_ids])

    for i, cama_id in enumerate(camas_ids):
        with tabs[i]:
            datos_paciente = df_pacientes[df_pacientes["cama"] == str(cama_id)]
            peso_p = float(datos_paciente["peso"].values[0]) if not datos_paciente.empty else 70.0
            
            col_h1, col_h2 = st.columns([4, 1])
            col_h1.subheader(f"Unidad {cama_id} | {peso_p} kg")
            
            # --- AGREGAR INFUSIÓN ---
            if col_h2.button(f"➕ Añadir Infusión", key=f"add_{cama_id}"):
                nueva_b = pd.DataFrame([{
                    "cama": str(cama_id), "droga": "Noradrenalina", 
                    "mg": 4.0, "vol": 250.0, "modo": "TITULAR", 
                    "ritmo": 0.0, "dosis": 0.0, 
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }])
                df_bombas = pd.concat([df_bombas, nueva_b], ignore_index=True)
                conn.update(worksheet="Bombas", data=df_bombas)
                st.cache_data.clear()
                st.rerun()

            # --- MOSTRAR INFUSIONES FILTRADAS ---
            if not df_bombas.empty:
                # Filtrar asegurando que comparamos strings
                bombas_actuales = df_bombas[df_bombas["cama"].astype(str) == str(cama_id)]
                
                if bombas_actuales.empty:
                    st.caption("Sin infusiones activas.")
                
                for idx, row in bombas_actuales.iterrows():
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([1.5, 2.5, 1, 0.4])
                        
                        with c1:
                            st.markdown(f"**{row['droga']}**")
                            st.caption(f"{row['mg']} mg / {row['vol']} ml")
                        
                        with c2:
                            # Permitir edición de ritmo en tiempo real
                            val_ritmo = st.number_input(f"Ritmo ({idx})", value=float(row['ritmo']), key=f"rit_{idx}", step=0.1)
                            
                            if val_ritmo != row['ritmo']:
                                df_bombas.at[idx, 'ritmo'] = val_ritmo
                                conn.update(worksheet="Bombas", data=df_bombas)
                                st.cache_data.clear()
                                st.rerun()

                            # Cálculos de Gammas
                            res_gammas = (val_ritmo * float(row['mg']) * 1000) / (60 * peso_p * float(row['vol'])) if float(row['vol']) > 0 else 0
                            st.metric("DOSIS (gammas)", f"{res_gammas:.3f}")

                        with c3:
                            conc = (float(row['mg']) * 1000 / float(row['vol'])) if float(row['vol']) > 0 else 0
                            st.write(f"Conc: {conc:.1f} µg/ml")
                            st.caption(f"Act: {row['timestamp']}")

                        with c4:
                            st.write(" ")
                            if st.button("🗑️", key=f"del_{idx}"):
                                df_bombas = df_bombas.drop(idx)
                                conn.update(worksheet="Bombas", data=df_bombas)
                                st.cache_data.clear()
                                st.rerun()
            else:
                st.caption("Sin infusiones activas.")

# 8. PIE DE PÁGINA
st.markdown("""
    <p style='text-align: center; color: #444; font-size: 0.7rem; margin-top: 50px;'>
    HOSPITAL ITALIANO DE CÓRDOBA | SERVICIO DE CARDIOLOGÍA
    </p>
    """, unsafe_allow_html=True)
