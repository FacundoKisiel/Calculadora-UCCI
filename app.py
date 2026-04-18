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

# 2. ESTILO VISUAL (DARK MODE PROFESIONAL)
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

# 3. CONEXIÓN A BASE DE DATOS (GOOGLE SHEETS)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- NUEVA LÓGICA DE CARGA DIRECTA ---
def cargar_datos():
    try:
        # Extraemos el ID de la planilla de los secrets
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id = raw_url.split("/d/")[1].split("/")[0]
        
        # URL directa para CSV (hoja 1: Pacientes, hoja 2: Bombas)
        # Nota: Si tus hojas no están en ese orden, usaremos el nombre
        url_pacientes = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Pacientes"
        url_bombas = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Bombas"
        
        df_p = pd.read_csv(url_pacientes)
        df_b = pd.read_csv(url_bombas)
        return df_p, df_b
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame(columns=["cama", "peso"]), pd.DataFrame()

# Reemplaza la llamada inicial:
df_pacientes, df_bombas = cargar_datos()

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

# 5. CARGA INICIAL DE DATOS
df_pacientes, df_bombas = cargar_datos()

# 6. PANEL LATERAL (GESTIÓN)
with st.sidebar:
    st.header("⚙️ Gestión de Cama")
    cama_input = st.number_input("N° de Cama", min_value=1, step=1)
    peso_input = st.number_input("Peso (kg)", min_value=1.0, value=70.0)

    if st.button("Registrar / Actualizar Paciente"):
        nueva_fila = pd.DataFrame([{"cama": str(cama_input), "peso": peso_input}])
        # Actualizamos la lista de pacientes evitando duplicados
        df_act = pd.concat([df_pacientes, nueva_fila]).drop_duplicates(subset=["cama"], keep="last")
        conn.update(worksheet="Pacientes", data=df_act)
        st.success(f"Unidad {cama_input} sincronizada")
        st.rerun()
    
    st.divider()
    if st.button("🔄 Sincronizar Red"):
        st.rerun()
    
    if st.button("Cerrar Sesión"):
        st.session_state.password_correct = False
        st.rerun()

# 7. MONITOR PRINCIPAL
st.title("Monitor de Infusiones - Red UCC I")

if df_pacientes.empty:
    st.info("No hay pacientes registrados en la red. Use el panel lateral.")
else:
    # Ordenar camas numéricamente
    camas_ids = sorted(df_pacientes["cama"].unique(), key=lambda x: int(x))
    tabs = st.tabs([f"Unidad {c}" for c in camas_ids])

    for i, cama_id in enumerate(camas_ids):
        with tabs[i]:
            # Obtener peso del paciente
            peso_p = df_pacientes[df_pacientes["cama"] == str(cama_id)]["peso"].values[0]
            
            col_h1, col_h2 = st.columns([4, 1])
            col_h1.subheader(f"Unidad {cama_id} | {peso_p} kg")
            
            # --- BOTÓN AÑADIR BOMBA ---
            if col_h2.button(f"➕ Añadir Infusión", key=f"btn_add_{cama_id}"):
                nueva_b = pd.DataFrame([{
                    "cama": str(cama_id), 
                    "droga": "Noradrenalina", 
                    "mg": 4.0, 
                    "vol": 250, 
                    "modo": "TITULAR", 
                    "ritmo": 0.0, 
                    "dosis": 0.0, 
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }])
                df_bombas = pd.concat([df_bombas, nueva_b]).reset_index(drop=True)
                conn.update(worksheet="Bombas", data=df_bombas)
                st.rerun()

            # --- LISTADO DE BOMBAS ---
            bombas_actuales = df_bombas[df_bombas["cama"] == str(cama_id)]
            
            for idx, row in bombas_actuales.iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1.5, 2.5, 1, 0.4])
                    
                    with c1:
                        # Droga y Dilución (Lectura de la nube)
                        st.markdown(f"**{row['droga']}**")
                        st.caption(f"{row['mg']} mg / {row['vol']} ml")
                        
                        # Si quieres editar mg/vol, deberías hacerlo en la Sheet o agregar inputs aquí que disparen un conn.update
                        # Por ahora, mantenemos la visualización y cálculo rápido
                    
                    with c2:
                        # Modo y Valor (Sincronizado)
                        val_actual = st.number_input(f"Ritmo/Dosis ({idx})", value=float(row['ritmo']), key=f"inp_{idx}")
                        
                        if val_actual != row['ritmo']:
                            df_bombas.at[idx, 'ritmo'] = val_actual
                            conn.update(worksheet="Bombas", data=df_bombas)
                            st.rerun()

                        if row['modo'] == "TITULAR":
                            # Cálculo de gammas
                            res = (row['ritmo'] * row['mg'] * 1000) / (60 * peso_p * row['vol']) if row['vol'] > 0 else 0
                            st.metric("DOSIS (gammas)", f"{res:.3f}")
                        else:
                            st.metric("RITMO (ml/h)", f"{row['ritmo']:.1f}")

                    with c3:
                        conc = (row['mg'] * 1000 / row['vol']) if row['vol'] > 0 else 0
                        st.write(f"Conc: {conc:.1f} µg/ml")
                        st.caption(f"Act: {row['timestamp']}")

                    with c4:
                        st.write(" ")
                        if st.button("🗑️", key=f"del_{idx}"):
                            df_bombas = df_bombas.drop(idx)
                            conn.update(worksheet="Bombas", data=df_bombas)
                            st.rerun()

# 8. PIE DE PÁGINA (MODIFICADO)
st.markdown("""
    <p style='text-align: center; color: #444; font-size: 0.7rem; margin-top: 50px;'>
    HOSPITAL ITALIANO DE CÓRDOBA | SERVICIO DE CARDIOLOGÍA
    </p>
    """, unsafe_allow_html=True)
