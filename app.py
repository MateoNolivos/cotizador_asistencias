import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Image, Paragraph
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from PIL import Image as PILImage
from supabase import create_client
import tempfile
import requests
import os
import base64


# =========================
# SUPABASE
# =========================

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


# =========================
# USUARIOS
# =========================

USERS = st.secrets["USERS"]


# =========================
# PERIODOS
# =========================

PERIODOS = {
    "Mensual": 1,
    "Trimestral": 3,
    "Semestral": 6,
    "Anual": 12
}


# =========================
# PLANES
# =========================

PLANES = {
    "Plan Base Digital": {
        "cop_mensual": 0.265923014668853,
        "descripcion": "Plan enfocado en teleasistencia y orientación digital.",
        "coberturas": [
            {"asistencia": "Telemedicina General + Scan Face", "limite_eventos": "Ilimitado", "cobertura": "Atención médica virtual 24/7"},
            {"asistencia": "Asistencia educativa", "limite_eventos": "2 eventos", "cobertura": "Sesiones de asesoría educativa virtual hasta 2 horas"},
            {"asistencia": "Asistencia legal", "limite_eventos": "2 eventos", "cobertura": "Orientación legal telefónica/virtual"},
            {"asistencia": "Teleorientación ginecológica", "limite_eventos": "6 eventos", "cobertura": "Consulta virtual programada"},
            {"asistencia": "Limpieza dental", "limite_eventos": "1 evento", "cobertura": "Profilaxis dental anual hasta USD 100"},
            {"asistencia": "Entrega de medicamentos", "limite_eventos": "1 evento", "cobertura": "Servicio logístico"}
        ]
    },
    "Plan Integral Salud": {
        "cop_mensual": 0.430565037067061,
        "descripcion": "Plan con cobertura médica más integral y robusta.",
        "coberturas": [
            {"asistencia": "Telemedicina General + Scan Face", "limite_eventos": "Ilimitado", "cobertura": "Atención médica virtual 24/7"},
            {"asistencia": "Asistencia educativa", "limite_eventos": "2 eventos", "cobertura": "Sesiones de asesoría educativa virtual hasta 2 horas"},
            {"asistencia": "Asistencia legal", "limite_eventos": "2 eventos", "cobertura": "Orientación legal telefónica/virtual"},
            {"asistencia": "Consulta médica ginecológica", "limite_eventos": "6 eventos", "cobertura": "Consulta médica con especialista"},
            {"asistencia": "Limpieza dental", "limite_eventos": "1 evento", "cobertura": "Profilaxis dental anual hasta USD 100"},
            {"asistencia": "Descuento en medicamentos", "limite_eventos": "15% - 30%", "cobertura": "Beneficio comercial en farmacias afiliadas"}
        ]
    }
}


# =========================
# LOGO
# =========================

logo_url = "https://masservicios.com.ec/wp-content/uploads/2026/02/cropped-logo_ms.png"

if not os.path.exists("logo_mass.jpg"):
    response = requests.get(logo_url, timeout=20)
    response.raise_for_status()

    with open("logo_temp.png", "wb") as f:
        f.write(response.content)

    img = PILImage.open("logo_temp.png")

    if img.mode == "RGBA":
        background = PILImage.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        background.save("logo_mass.jpg")
    else:
        img.save("logo_mass.jpg")

logo_path = "logo_mass.jpg"


def get_base64_logo(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# =========================
# CONFIG
# =========================

st.set_page_config(page_title="Cotizador MAS Servicios", layout="wide")

logo_base64 = get_base64_logo(logo_path)

st.markdown(f"""
<style>
header {{visibility: hidden;}}
footer {{visibility: hidden;}}

.logo-header {{
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
}}

.main {{
    margin-top:120px;
}}

.card-option {{
    background: #ffffff;
    border: 1px solid #E6EAF0;
    border-radius: 18px;
    padding: 28px;
    text-align: center;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
    min-height: 170px;
}}

.card-icon {{
    font-size: 48px;
    margin-bottom: 8px;
}}

.card-title {{
    font-size: 24px;
    font-weight: 700;
    color: #1F3A5F;
}}

.card-subtitle {{
    font-size: 14px;
    color: #667085;
}}
</style>

<div class="logo-header">
    <img src="data:image/jpg;base64,{logo_base64}" width="200">
</div>
<div class="main">
""", unsafe_allow_html=True)


# =========================
# SESSION STATE
# =========================

defaults = {
    "authenticated": False,
    "logout": False,
    "modulo": None,
    "tipo_cliente": None,
    "cliente": "",
    "cedula": "",
    "fecha_nacimiento": date(1990, 1, 1),
    "direccion": "",
    "telefono": "",
    "mail": "",
    "ruc": "",
    "personas": 1,
    "periodo": "Mensual",
    "plan": "Plan Base Digital"
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =========================
# LOGOUT
# =========================

if st.session_state.logout:
    st.session_state.authenticated = False
    st.session_state.usuario = None
    st.session_state.vendedor = None
    st.session_state.logout = False
    st.session_state.modulo = None
    st.session_state.tipo_cliente = None
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
# TOP BAR
# =========================

col1, col2 = st.columns([6, 1])
col1.success(f"Vendedor: {st.session_state.vendedor}")

if col2.button("Cerrar sesión"):
    st.session_state.logout = True
    st.rerun()


# =========================
# FUNCIONES
# =========================

def volver_inicio():
    st.session_state.modulo = None
    st.session_state.tipo_cliente = None


def nueva_cotizacion():
    st.session_state.cliente = ""
    st.session_state.cedula = ""
    st.session_state.fecha_nacimiento = date(1990, 1, 1)
    st.session_state.direccion = ""
    st.session_state.telefono = ""
    st.session_state.mail = ""
    st.session_state.ruc = ""
    st.session_state.personas = 1
    st.session_state.periodo = "Mensual"
    st.session_state.plan = "Plan Base Digital"


def guardar_log_supabase(
    modulo,
    tipo_cliente,
    cliente,
    cedula,
    fecha_nacimiento,
    direccion,
    telefono,
    mail,
    ruc,
    vendedor,
    personas,
    periodo_label,
    plan_nombre,
    cop_mensual,
    cop_final_persona,
    precio_total
):
    data = {
        "fecha_registro": datetime.now().isoformat(),
        "modulo": modulo,
        "tipo_cliente": tipo_cliente,
        "cliente": cliente,
        "cedula": cedula if tipo_cliente == "B2C" else None,
        "fecha_nacimiento": str(fecha_nacimiento) if tipo_cliente == "B2C" else None,
        "direccion": direccion if tipo_cliente == "B2C" else None,
        "telefono": telefono if tipo_cliente == "B2C" else None,
        "mail": mail if tipo_cliente == "B2C" else None,
        "ruc": ruc if tipo_cliente == "B2B" else None,
        "vendedor": vendedor,
        "asistencia": "TELEMEDICINA",
        "plan": plan_nombre,
        "periodo": periodo_label,
        "personas": int(personas),
        "cop_mensual": round(float(cop_mensual), 2),
        "cop_por_persona": round(float(cop_final_persona), 2),
        "precio_total": round(float(precio_total), 2)
    }

    supabase.table("logs_cotizaciones").insert(data).execute()


def generar_pdf(
    tipo_cliente,
    cliente,
    cedula,
    fecha_nacimiento,
    direccion,
    telefono,
    mail,
    ruc,
    vendedor,
    personas,
    periodo_label,
    plan_nombre,
    cop_mensual,
    cop_final_persona,
    precio_total,
    df_coberturas
):
    fecha_hoy = datetime.today()
    vigencia = fecha_hoy + timedelta(days=14)

    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp_pdf.name, pagesize=letter)

    styles = getSampleStyleSheet()

    style_normal = ParagraphStyle(
        "normal_custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    style_header = ParagraphStyle(
        "header_custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.black,
    )

    def draw_logo_and_title(title_text):
        logo = Image(logo_path)
        logo.drawHeight = 45
        logo.drawWidth = 150
        logo.drawOn(c, 40, 735)

        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(colors.HexColor("#1F3A5F"))
        c.drawString(220, 748, title_text)

        c.setStrokeColor(colors.HexColor("#D9E2F3"))
        c.setLineWidth(1)
        c.line(40, 728, 570, 728)
        c.setFillColor(colors.black)

    def draw_section_title(text, x, y):
        c.setFillColor(colors.HexColor("#1F3A5F"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, text)
        c.setFillColor(colors.black)

    def make_key_value_table(rows, col_widths=(160, 340)):
        table = Table(rows, colWidths=list(col_widths), rowHeights=22)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B8C7DB")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEEB")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return table

    draw_logo_and_title("Proforma de Telemedicina")
    draw_section_title("Datos del cliente", 40, 700)

    if tipo_cliente == "B2C":
        data_cliente = [
            ["Tipo de cliente", "B2C"],
            ["Cliente", cliente],
            ["Cédula", cedula],
            ["Fecha de nacimiento", fecha_nacimiento.strftime("%d/%m/%Y")],
            ["Dirección", direccion],
            ["Teléfono", telefono],
            ["Mail", mail],
            ["Vendedor", vendedor],
        ]
        y_cliente = 518
    else:
        data_cliente = [
            ["Tipo de cliente", "B2B"],
            ["Cliente / Empresa", cliente],
            ["RUC", ruc],
            ["Vendedor", vendedor],
        ]
        y_cliente = 606

    table_cliente = make_key_value_table(data_cliente)
    table_cliente.wrapOn(c, 40, 0)
    table_cliente.drawOn(c, 40, y_cliente)

    draw_section_title("Datos de cotización", 40, 490)

    data_cotizacion = [
        ["Asistencia", "TELEMEDICINA"],
        ["Plan", plan_nombre],
        ["Número de personas", f"{personas:,.0f}"],
        ["Periodo", periodo_label],
        ["Fecha", fecha_hoy.strftime("%d/%m/%Y")],
        ["Válido hasta", vigencia.strftime("%d/%m/%Y")],
    ]

    table_cotizacion = make_key_value_table(data_cotizacion)
    table_cotizacion.wrapOn(c, 40, 0)
    table_cotizacion.drawOn(c, 40, 355)

    draw_section_title("Resumen económico", 40, 330)

    data_resumen = [
        ["Concepto", "Valor"],
        ["COP mensual base", f"${cop_mensual:,.2f}"],
        ["COP por persona", f"${cop_final_persona:,.2f}"],
        ["Precio total", f"${precio_total:,.2f}"],
    ]

    table_resumen = Table(data_resumen, colWidths=[260, 140], rowHeights=24)
    table_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F1F1F")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#B8C7DB")),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    table_resumen.wrapOn(c, 40, 0)
    table_resumen.drawOn(c, 40, 230)

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(40, 35, "Documento generado automáticamente por el cotizador de telemedicina.")
    c.setFillColor(colors.black)

    c.showPage()
    draw_logo_and_title("Coberturas del plan")

    c.setFont("Helvetica", 10)
    c.drawString(40, 705, f"Plan seleccionado: {plan_nombre}")

    data_coberturas = [[
        Paragraph("<b>Asistencia</b>", style_header),
        Paragraph("<b>Límite de eventos</b>", style_header),
        Paragraph("<b>Cobertura</b>", style_header),
    ]]

    for _, row in df_coberturas.iterrows():
        data_coberturas.append([
            Paragraph(str(row["asistencia"]), style_normal),
            Paragraph(str(row["limite_eventos"]), style_normal),
            Paragraph(str(row["cobertura"]), style_normal),
        ])

    table_cob = Table(data_coberturas, colWidths=[180, 110, 235], repeatRows=1)

    estilo_cob = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C7DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    for i in range(1, len(data_coberturas)):
        bg = colors.whitesmoke if i % 2 == 0 else colors.white
        estilo_cob.append(("BACKGROUND", (0, i), (-1, i), bg))

    table_cob.setStyle(TableStyle(estilo_cob))
    table_cob.wrapOn(c, 40, 0)
    table_cob.drawOn(c, 30, 470)

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(40, 35, "Coberturas sujetas a condiciones de contratación y vigencia de la proforma.")
    c.setFillColor(colors.black)

    c.save()
    return temp_pdf.name


# =========================
# SELECCIÓN INICIAL
# =========================

if st.session_state.modulo is None:
    st.title("Selecciona el tipo de cotización")

    col_masivos, col_viajes = st.columns(2)

    with col_masivos:
        st.markdown("""
        <div class="card-option">
            <div class="card-icon">👥</div>
            <div class="card-title">MASIVOS</div>
            <div class="card-subtitle">Cotizador para asistencias masivas</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Ingresar a MASIVOS", use_container_width=True):
            st.session_state.modulo = "MASIVOS"
            st.rerun()

    with col_viajes:
        st.markdown("""
        <div class="card-option">
            <div class="card-icon">✈️</div>
            <div class="card-title">VIAJES</div>
            <div class="card-subtitle">Cotizador para asistencias de viaje</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Ingresar a VIAJES", use_container_width=True):
            st.session_state.modulo = "VIAJES"
            st.rerun()

    st.stop()


# =========================
# VIAJES
# =========================

if st.session_state.modulo == "VIAJES":
    st.title("✈️ Cotizador de Viajes")
    st.info("Esta sección queda lista para trabajarla luego.")
    st.button("Volver al inicio", on_click=volver_inicio)
    st.stop()


# =========================
# MASIVOS
# =========================

st.title("👥 Cotizador de Masivos")

if st.button("Volver al inicio"):
    volver_inicio()
    st.rerun()

st.markdown("---")

if st.session_state.tipo_cliente is None:
    st.subheader("Selecciona el tipo de cliente")

    col_b2c, col_b2b = st.columns(2)

    with col_b2c:
        st.markdown("""
        <div class="card-option">
            <div class="card-icon">🙋‍♂️</div>
            <div class="card-title">B2C</div>
            <div class="card-subtitle">Cliente individual con datos personales</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Cotizar B2C", use_container_width=True):
            st.session_state.tipo_cliente = "B2C"
            st.rerun()

    with col_b2b:
        st.markdown("""
        <div class="card-option">
            <div class="card-icon">🏢</div>
            <div class="card-title">B2B</div>
            <div class="card-subtitle">Empresa o cliente corporativo</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Cotizar B2B", use_container_width=True):
            st.session_state.tipo_cliente = "B2B"
            st.rerun()

    st.stop()


if st.button("Cambiar B2B / B2C"):
    st.session_state.tipo_cliente = None
    st.rerun()


# =========================
# DATOS CLIENTE
# =========================

st.subheader(f"Datos del cliente - {st.session_state.tipo_cliente}")

if st.session_state.tipo_cliente == "B2C":
    col_cliente_1, col_cliente_2 = st.columns(2)

    with col_cliente_1:
        cliente = st.text_input("Nombre del cliente", key="cliente")
        cedula = st.text_input("Cédula", key="cedula")
        fecha_nacimiento = st.date_input(
            "Fecha de nacimiento",
            key="fecha_nacimiento",
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY"
        )

    with col_cliente_2:
        direccion = st.text_input("Dirección", key="direccion")
        telefono = st.text_input("Número de teléfono", key="telefono")
        mail = st.text_input("Mail", key="mail")

    ruc = ""

    campos_faltantes = []

    if cliente == "":
        campos_faltantes.append("Nombre del cliente")
    if cedula == "":
        campos_faltantes.append("Cédula")
    if direccion == "":
        campos_faltantes.append("Dirección")
    if telefono == "":
        campos_faltantes.append("Número de teléfono")
    if mail == "":
        campos_faltantes.append("Mail")

else:
    col_cliente_1, col_cliente_2 = st.columns(2)

    with col_cliente_1:
        cliente = st.text_input("Nombre del cliente / empresa", key="cliente")

    with col_cliente_2:
        ruc = st.text_input("RUC", key="ruc")

    cedula = ""
    fecha_nacimiento = date(1990, 1, 1)
    direccion = ""
    telefono = ""
    mail = ""

    campos_faltantes = []

    if cliente == "":
        campos_faltantes.append("Nombre del cliente / empresa")
    if ruc == "":
        campos_faltantes.append("RUC")


if campos_faltantes:
    st.warning("Complete los siguientes campos: " + ", ".join(campos_faltantes))
    st.stop()


# =========================
# DATOS DE COTIZACIÓN
# =========================

st.markdown("---")
st.subheader("Datos de cotización")

col_a, col_b, col_c = st.columns(3)

with col_a:
    personas = st.number_input(
        "Número de personas",
        min_value=1,
        step=1,
        key="personas"
    )

with col_b:
    periodo_label = st.selectbox(
        "Periodo de contratación",
        list(PERIODOS.keys()),
        key="periodo"
    )

with col_c:
    plan_nombre = st.selectbox(
        "Plan",
        list(PLANES.keys()),
        key="plan"
    )


# =========================
# CÁLCULO
# =========================

periodo_meses = PERIODOS[periodo_label]
cop_mensual = PLANES[plan_nombre]["cop_mensual"]

if periodo_label == "Mensual":
    cop_final_persona = cop_mensual
else:
    cop_final_persona = cop_mensual * periodo_meses

precio_total = cop_final_persona * personas
df_coberturas = pd.DataFrame(PLANES[plan_nombre]["coberturas"])


# =========================
# RESULTADO
# =========================

st.markdown("---")
st.subheader("Resultado de la cotización")

col1, col2, col3 = st.columns(3)

col1.metric("Asistencia", "TELEMEDICINA")
col2.metric("COP por persona", f"${cop_final_persona:,.2f}")
col3.metric("Precio total", f"${precio_total:,.2f}")

st.info(PLANES[plan_nombre]["descripcion"])

st.subheader("Coberturas del plan")
st.dataframe(df_coberturas, hide_index=True, use_container_width=True)


with st.expander("Ver detalle del cálculo"):
    st.write(f"**COP mensual base:** ${cop_mensual:,.2f}")
    st.write(f"**Periodo seleccionado:** {periodo_label} ({periodo_meses} mes(es))")

    if periodo_label == "Mensual":
        st.write("**Lógica aplicada:** COP final = COP mensual base")
    else:
        st.write(
            f"**Lógica aplicada:** COP final = COP mensual base × meses = "
            f"${cop_mensual:,.2f} × {periodo_meses}"
        )

    st.write(f"**COP final por persona:** ${cop_final_persona:,.2f}")
    st.write(f"**Número de personas:** {personas}")
    st.write(f"**Precio total:** ${precio_total:,.2f}")


# =========================
# BOTÓN PDF + SUPABASE
# =========================

if st.button("Generar Proforma PDF"):
    try:
        guardar_log_supabase(
            modulo=st.session_state.modulo,
            tipo_cliente=st.session_state.tipo_cliente,
            cliente=cliente,
            cedula=cedula,
            fecha_nacimiento=fecha_nacimiento,
            direccion=direccion,
            telefono=telefono,
            mail=mail,
            ruc=ruc,
            vendedor=st.session_state.vendedor,
            personas=personas,
            periodo_label=periodo_label,
            plan_nombre=plan_nombre,
            cop_mensual=cop_mensual,
            cop_final_persona=cop_final_persona,
            precio_total=precio_total
        )

        pdf_path = generar_pdf(
            tipo_cliente=st.session_state.tipo_cliente,
            cliente=cliente,
            cedula=cedula,
            fecha_nacimiento=fecha_nacimiento,
            direccion=direccion,
            telefono=telefono,
            mail=mail,
            ruc=ruc,
            vendedor=st.session_state.vendedor,
            personas=personas,
            periodo_label=periodo_label,
            plan_nombre=plan_nombre,
            cop_mensual=cop_mensual,
            cop_final_persona=cop_final_persona,
            precio_total=precio_total,
            df_coberturas=df_coberturas
        )

        nombre_archivo = cliente.replace(" ", "_").replace("/", "_")

        st.success("Proforma generada y registrada correctamente en Supabase.")

        with open(pdf_path, "rb") as f:
            st.download_button(
                label="Descargar Proforma",
                data=f,
                file_name=f"proforma_telemedicina_{nombre_archivo}.pdf",
                mime="application/pdf"
            )

    except Exception as e:
        st.error(f"Ocurrió un error al generar o guardar la proforma: {e}")


# =========================
# NUEVA COTIZACIÓN
# =========================

st.markdown("---")
st.button("Nueva Cotización", on_click=nueva_cotizacion)

st.markdown("</div>", unsafe_allow_html=True)
