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

# 2. ESTILO VISUAL (DARK MODE)
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

# 3. DICCIONARIO DE DROGAS ACTUALIZADO (SEGÚN TU PEDIDO)
# mg representa la masa (o UI en vasopresina) y vol la dilución estándar inicial
DROGAS_DB = {
    "Noradrenalina": {"masa": 4.0, "vol": 250, "unidad": "mg"},
    "Adrenalina": {"masa": 1.0, "vol": 100, "unidad": "mg"},
    "Vasopresina": {"masa": 20.0, "vol": 100, "unidad": "UI"},
    "Lidocaina": {"masa": 100.0, "vol": 100, "unidad": "mg"},
    "Nitroglicerina": {"masa": 25.0, "vol": 250, "unidad": "mg"},
    "Furosemida": {"masa": 20.0, "vol": 20, "unidad": "mg"},
    "Atropina": {"masa": 1.0, "vol": 10, "unidad": "mg"},
    "Amiodarona": {"masa": 150.0, "vol": 100, "unidad": "mg"},
    "Dobutamina": {"masa": 250.0, "vol": 250, "unidad": "mg"},
    "Dopamina": {"masa": 400.0, "vol": 250, "unidad": "mg"},
    "Milrinona": {"masa": 20.0, "vol": 100, "unidad": "mg"},
    "Nitroprusiato": {"masa": 50.0, "vol": 250, "unidad": "mg"},
    "Propofol": {"masa": 1000.0, "vol": 100, "unidad": "mg"},
    "Fentanilo": {"masa": 0.5, "vol": 100, "unidad": "mg"},
    "Remifentanilo": {"masa": 5.0, "vol": 100, "unidad": "mg"},
    "Isoproterenol": {"masa": 1.0, "vol": 250, "unidad": "mg"}
}

# 4. CONEXIÓN A GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_p = conn.read(worksheet="Pacientes", ttl=0)
        df_b = conn.read(worksheet="Bombas", ttl=0)
        df_p = df_p.dropna(how='all')
        df_b = df_b.dropna(how='all')
        if not df_p.empty: df_p["cama"] = df_p["cama"].astype(str)
        if not df_b.empty: df_b["cama"] = df_b["cama"].astype(str)
        return df_p, df_b
    except Exception:
        return pd.DataFrame(columns=["cama", "peso"]), pd.DataFrame(columns=["cama", "droga", "mg", "vol", "ritmo", "timestamp"])

# 5. SEGURIDAD
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

# 6. CARGA DE DATOS
df_pacientes, df_bombas = cargar_datos()

# 7. PANEL LATERAL
with st.sidebar:
    st.header("⚙️ Gestión")
    cama_input = st.number_input("Cama", min_value=1, step=1)
    peso_input = st.number_input("Peso (kg)", min_value=1.0, value=70.0)

    if st.button("Registrar Unidad"):
        nueva_fila = pd.DataFrame([{"cama": str(cama_input), "peso": peso_input}])
        df_act = pd.concat([df_pacientes, nueva_fila]).drop_duplicates(subset=["cama"], keep="last")
        conn.update(worksheet="Pacientes", data=df_act)
        st.cache_data.clear()
        st.success(f"Cama {cama_input} registrada")
        st.rerun()
    
    st.divider()
    if st.button("🔄 Sincronizar"):
        st.cache_data.clear()
        st.rerun()

# 8. MONITOR PRINCIPAL
st.title("Control de Infusiones - Servicio de Cardiología")

if df_pacientes.empty:
    st.info("No hay pacientes activos.")
else:
    camas_ids = sorted(df_pacientes["cama"].unique(), key=lambda x: int(float(x)))
    tabs = st.tabs([f"Unidad {c}" for c in camas_ids])

    for i, cama_id in enumerate(camas_ids):
        with tabs[i]:
            datos_p = df_pacientes[df_pacientes["cama"] == str(cama_id)]
            peso_p = float(datos_p["peso"].values[0]) if not datos_p.empty else 70.0
            
            col_h1, col_h2 = st.columns([3, 2])
            col_h1.subheader(f"Unidad {cama_id} | {peso_p} kg")
            
            with col_h2:
                with st.expander("➕ Añadir Droga"):
                    droga_sel = st.selectbox("Seleccionar droga", list(DROGAS_DB.keys()), key=f"sel_{cama_id}")
                    if st.button("Confirmar", key=f"add_{cama_id}"):
                        config = DROGAS_DB[droga_sel]
                        nueva_b = pd.DataFrame([{
                            "cama": str(cama_id), "droga": droga_sel, 
                            "mg": config["masa"], "vol": config["vol"],
                            "ritmo": 0.0, "timestamp": datetime.now().strftime("%H:%M:%S")
                        }])
                        df_bombas = pd.concat([df_bombas, nueva_b], ignore_index=True)
                        conn.update(worksheet="Bombas", data=df_bombas)
                        st.cache_data.clear()
                        st.rerun()

            if not df_bombas.empty:
                bombas_cama = df_bombas[df_bombas["cama"].astype(str) == str(cama_id)]
                
                for idx, row in bombas_cama.iterrows():
                    # Determinamos etiqueta de unidad (UI para Vasopresina, mg para el resto)
                    uni_label = "UI" if row['droga'] == "Vasopresina" else "mg"
                    
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([1.5, 2, 1.5, 0.5])
                        
                        with c1:
                            st.markdown(f"**{row['droga']}**")
                            new_mg = st.number_input(uni_label, value=float(row['mg']), key=f"mg_{idx}")
                            new_vol = st.number_input("ml dilución", value=float(row['vol']), key=f"vol_{idx}")
                            if new_mg != row['mg'] or new_vol != row['vol']:
                                df_bombas.at[idx, 'mg'] = new_mg
                                df_bombas.at[idx, 'vol'] = new_vol
                                conn.update(worksheet="Bombas", data=df_bombas)
                                st.rerun()

                        with c2:
                            ritmo_actual = st.number_input("Ritmo (ml/h)", value=float(row['ritmo']), key=f"rit_{idx}", step=0.1)
                            # Cálculo: (ml/h * masa * 1000) / (60 * peso * vol)
                            if new_vol > 0 and peso_p > 0:
                                dosis_calc = (ritmo_actual * new_mg * 1000) / (60 * peso_p * new_vol)
                            else:
                                dosis_calc = 0.0
                            
                            etiqueta_final = "γ/kg/min" if row['droga'] != "Vasopresina" else "mU/kg/min"
                            st.metric("DOSIS", f"{dosis_calc:.3f} {etiqueta_final}")
                            
                            if ritmo_actual != row['ritmo']:
                                df_bombas.at[idx, 'ritmo'] = ritmo_actual
                                conn.update(worksheet="Bombas", data=df_bombas)
                                st.cache_data.clear()
                                st.rerun()

                        with c3:
                            st.caption("Cálculo Inverso")
                            target = st.number_input("Gamas/mU deseadas", value=dosis_calc, key=f"inv_{idx}", step=0.01)
                            if new_mg > 0:
                                ml_h_sug = (target * 60 * peso_p * new_vol) / (new_mg * 1000)
                                st.write(f"Sugerido: **{ml_h_sug:.1f} ml/h**")
                            
                        with c4:
                            st.write(" ")
                            if st.button("🗑️", key=f"del_{idx}"):
                                df_bombas = df_bombas.drop(idx)
                                conn.update(worksheet="Bombas", data=df_bombas)
                                st.cache_data.clear()
                                st.rerun()
            else:
                st.info("Sin infusiones activas.")

st.markdown("<p style='text-align: center; color: #444; font-size: 0.8rem; margin-top: 30px;'>HOSPITAL ITALIANO DE CÓRDOBA | SERVICIO DE CARDIOLOGÍA</p>", unsafe_allow_html=True)
