import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from PIL import Image as PILImage
import tempfile
import requests
import os


# =========================
# USUARIOS
# =========================

USERS = {
    "pablop2026": {"password": "MASecu20$6p", "nombre": "Pablo Pastor"},
    "fauston2026": {"password": "MASecu20$6f", "nombre": "Fausto Nolivos"},
    "mateon2026": {"password": "MASecu20$6m", "nombre": "Mateo Nolivos"}
}


# =========================
# MAPA PERIODOS
# =========================

PERIODOS = {
    "Anual": 12,
    "Semestral": 6,
    "Trimestral": 3,
    "Mensual": 1
}


# =========================
# LOGO
# =========================

logo_url = "https://masservicios.com.ec/wp-content/uploads/2026/02/cropped-logo_ms.png"

if not os.path.exists("logo_mass.jpg"):

    response = requests.get(logo_url)

    with open("logo_temp.png", "wb") as f:
        f.write(response.content)

    img = PILImage.open("logo_temp.png")

    if img.mode == "RGBA":
        background = PILImage.new("RGB", img.size, (255,255,255))
        background.paste(img, mask=img.split()[3])
        background.save("logo_mass.jpg")
    else:
        img.save("logo_mass.jpg")

logo_path = "logo_mass.jpg"


# =========================
# HEADER
# =========================

st.markdown("""
<style>

header {visibility: hidden;}
footer {visibility: hidden;}

.logo-header {
position: fixed;
top: 0;
left: 0;
width: 100%;
background: white;
padding: 10px 20px;
z-index: 1000;
border-bottom: 1px solid #eee;
display:flex;
align-items:center;
}

.logo-header h2{
margin-left:20px;
font-family:sans-serif;
}

.main {
margin-top:120px;
}

</style>
""", unsafe_allow_html=True)


st.markdown(f"""
<div class="logo-header">
<img src="{logo_url}" width="200">
<h2>Cotizador de Asistencias</h2>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main">', unsafe_allow_html=True)


# =========================
# SESSION STATE
# =========================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "logout" not in st.session_state:
    st.session_state.logout = False

if "asistencias_count" not in st.session_state:
    st.session_state.asistencias_count = 1


# =========================
# LOGOUT
# =========================

if st.session_state.logout:

    st.session_state.authenticated = False
    st.session_state.usuario = None
    st.session_state.vendedor = None
    st.session_state.logout = False

    st.rerun()


# =========================
# LOGIN
# =========================

if not st.session_state.authenticated:

    st.title("Acceso al Sistema")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):

        if usuario in USERS and USERS[usuario]["password"] == password:

            st.session_state.authenticated = True
            st.session_state.usuario = usuario
            st.session_state.vendedor = USERS[usuario]["nombre"]

            st.rerun()

        else:
            st.error("Usuario o contraseña incorrectos")

    st.stop()


# =========================
# BOTONES SUPERIORES
# =========================

col1, col2 = st.columns([6,1])

col1.success(f"Vendedor: {st.session_state.vendedor}")

if col2.button("Cerrar sesión"):
    st.session_state.logout = True


# =========================
# NUEVA COTIZACION
# =========================

def nueva_cotizacion():

    st.session_state.cliente = ""
    st.session_state.asistencias_count = 1


# =========================
# CLIENTE
# =========================

cliente = st.text_input("CLIENTE", key="cliente")

if cliente == "":
    st.warning("Ingrese el nombre del cliente")
    st.stop()


# =========================
# DATA
# =========================

df = pd.read_excel("asistencias.xlsx")


# =========================
# FLUJO ASISTENCIAS
# =========================

for i in range(st.session_state.asistencias_count):

    st.markdown(f"---")
    st.subheader(f"Asistencia {i+1}")

    personas = st.number_input(
        "Número de personas",
        min_value=1,
        step=1,
        key=f"personas_{i}"
    )

    periodo_label = st.selectbox(
        "Periodo de contratación",
        list(PERIODOS.keys()),
        key=f"periodo_{i}"
    )

    periodo_valor = PERIODOS[periodo_label]

    asistencias = ["Seleccione asistencia"] + list(df["asistencia"].unique())

    asistencia = st.selectbox(
        "Asistencia",
        asistencias,
        key=f"asistencia_{i}"
    )

    if asistencia != "Seleccione asistencia":

        df_periodo = df[
            (df["asistencia"] == asistencia) &
            (df["periodo"] == periodo_valor)
        ]

        coberturas = df_periodo["cobertura"].unique()

        cobertura = st.multiselect(
            "Seleccione coberturas",
            coberturas,
            key=f"cobertura_{i}"
        )

        if cobertura:

            df_filtrado = df_periodo[
                df_periodo["cobertura"].isin(cobertura)
            ]

            precio_unitario = df_filtrado["precio"].sum()
            precio_total = precio_unitario * personas

            st.subheader("Detalle")

            df_display = df_filtrado.copy()
            df_display["precio"] = df_display["precio"].apply(lambda x: f"${x:,.0f}")

            st.dataframe(
                df_display[["asistencia","cobertura","precio"]],
                hide_index=True
            )

            col1, col2 = st.columns(2)

            col1.metric(
                "Precio Total x Asistencia",
                f"${precio_unitario:,.0f}"
            )

            col2.metric(
                "Precio Total",
                f"${precio_total:,.0f}"
            )


            # =========================
            # PDF
            # =========================

            if st.button(f"Generar Proforma PDF {i+1}"):

                fecha_hoy = datetime.today()
                vigencia = fecha_hoy + timedelta(days=14)

                temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

                c = canvas.Canvas(temp_pdf.name, pagesize=letter)

                logo = Image(logo_path)
                logo.drawHeight = 60
                logo.drawWidth = 200
                logo.drawOn(c,200,720)

                c.setFont("Helvetica-Bold",16)
                c.drawString(180,690,"Proforma de Asistencias")

                c.setFont("Helvetica",11)

                c.drawString(50,650,f"Cliente: {cliente}")
                c.drawString(50,630,f"Vendedor: {st.session_state.vendedor}")
                c.drawString(50,610,f"Número de personas: {personas:,.0f}")
                c.drawString(50,590,f"Periodo: {periodo_label}")

                c.drawString(50,570,f"Fecha: {fecha_hoy.strftime('%d/%m/%Y')}")
                c.drawString(50,550,f"Válido hasta: {vigencia.strftime('%d/%m/%Y')}")

                c.setFont("Helvetica-Bold",12)
                c.drawString(50,520,f"ASISTENCIA N° {i+1}")

                data = [["Asistencia","Cobertura","Precio Unitario"]]

                for _,row in df_filtrado.iterrows():

                    data.append([
                        row["asistencia"],
                        row["cobertura"],
                        f"${row['precio']:,.0f}"
                    ])

                data.append(["","Precio Total x Asistencia",f"${precio_unitario:,.0f}"])
                data.append(["","Precio Total",f"${precio_total:,.0f}"])

                table = Table(data,colWidths=[200,200,120])

                style = TableStyle([

                    ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
                    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                    ("GRID",(0,0),(-1,-1),1,colors.grey),
                    ("ALIGN",(2,1),(2,-1),"RIGHT"),
                    ("FONTNAME",(1,-2),(2,-1),"Helvetica-Bold")

                ])

                table.setStyle(style)

                table.wrapOn(c,50,380)
                table.drawOn(c,50,380)

                c.save()

                with open(temp_pdf.name,"rb") as f:

                    st.download_button(
                        label="Descargar Proforma",
                        data=f,
                        file_name=f"proforma_{cliente}_{i+1}.pdf",
                        mime="application/pdf"
                    )


# =========================
# AGREGAR ASISTENCIA
# =========================

def agregar_asistencia():
    st.session_state.asistencias_count += 1

st.markdown("---")

st.button(
    "➕ Agregar otra asistencia",
    on_click=agregar_asistencia
)


# =========================
# NUEVA COTIZACION
# =========================

st.button(
    "Nueva Cotización",
    on_click=nueva_cotizacion
)

