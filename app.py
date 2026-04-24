import streamlit as st
import pandas as pd

from datetime import datetime, timedelta, date
import tempfile
import requests
import os
import base64

from PIL import Image as PILImage
from supabase import create_client

from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Image, Paragraph
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER


# =====================================================
# CONFIG GENERAL
# =====================================================

st.set_page_config(page_title="Cotizador MAS Servicios", layout="wide")

IVA = 0.15


# =====================================================
# SUPABASE
# =====================================================

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


# =====================================================
# USUARIOS
# =====================================================

USERS = st.secrets["USERS"]


# =====================================================
# MASIVOS - CONFIG
# =====================================================

PERIODOS = {
    "Mensual": 1,
    "Trimestral": 3,
    "Semestral": 6,
    "Anual": 12
}

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


# =====================================================
# VIAJES - CONFIG
# =====================================================

PRODUCTOS_VIAJES = {
    "AGENCIAS 50K GC600 H85": {
        "edad_min": 0,
        "edad_max": 84,
        "dias_min": 3,
        "dias_max": 120,
        "tarifa_diaria": 5.50,
        "descripcion": "Asistencia médica 50K, límite de edad 75/85 años, gastos de cancelación $600 y deportes amateur 10K."
    },
    "INFINITE 100K + 600 CAN": {
        "edad_min": 0,
        "edad_max": 84,
        "dias_min": 3,
        "dias_max": 120,
        "tarifa_diaria": 6.00,
        "descripcion": "Asistencia médica 100K, gastos de cancelación $600 y deportes amateur 10K."
    },
    "ADVISOR 100K": {
        "edad_min": 15,
        "edad_max": 44,
        "dias_min": 3,
        "dias_max": 365,
        "tarifa_diaria": 1.70,
        "descripcion": "Asistencia médica accidente 100K, límite de edad 45 años, gastos de cancelación $600 y deportes amateur 10K."
    },
    "SENIOR + 85": {
        "edad_min": 85,
        "edad_max": 98,
        "dias_min": 3,
        "dias_max": 180,
        "tarifa_diaria": 19.00,
        "descripcion": "Asistencia médica 30K con preexistencias 5K para pasajeros senior."
    },
    "PLATINUM 60K PRE INT": {
        "edad_min": 0,
        "edad_max": 84,
        "dias_min": 3,
        "dias_max": 120,
        "tarifa_diaria": 3.50,
        "descripcion": "Asistencia médica 60K con preexistencia internacional."
    }
}

UPGRADES_VIAJES = {
    "DEP CAT 2": {"tipo": "diario", "valor": 5.00},
    "DEP CAT 3": {"tipo": "diario", "valor": 9.00},
    "DEP CAT 4": {"tipo": "diario", "valor": 11.00},
    "PRE-EXISTENCIA": {"tipo": "diario", "valor": 4.00},
    "FUTURA MAMA": {"tipo": "fijo", "valor": 45.00},
    "OBJETOS PERSONALES": {"tipo": "fijo", "valor": 50.00},
    "TECH PROTECTION": {"tipo": "fijo", "valor": 60.00},
    "MASCOTAS 5K": {"tipo": "fijo", "valor": 38.00},
    "MASCOTAS 10K": {"tipo": "fijo", "valor": 65.00},
    "Parque Temático WorldWide": {"tipo": "fijo", "valor": 12.00}
}


# =====================================================
# LOGO
# =====================================================

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


logo_base64 = get_base64_logo(logo_path)


# =====================================================
# ESTILOS
# =====================================================

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


# =====================================================
# SESSION STATE
# =====================================================

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
    "plan": "Plan Base Digital",

    "viajes_nombre": "",
    "viajes_telefono": "",
    "viajes_correo": "",
    "viajes_fecha_nacimiento": date(1995, 1, 1),
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =====================================================
# LOGIN / LOGOUT
# =====================================================

if st.session_state.logout:
    st.session_state.authenticated = False
    st.session_state.usuario = None
    st.session_state.vendedor = None
    st.session_state.logout = False
    st.session_state.modulo = None
    st.session_state.tipo_cliente = None
    st.rerun()


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


col_top_1, col_top_2 = st.columns([6, 1])
col_top_1.success(f"Vendedor: {st.session_state.vendedor}")

if col_top_2.button("Cerrar sesión"):
    st.session_state.logout = True
    st.rerun()


# =====================================================
# FUNCIONES GENERALES
# =====================================================

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

    st.session_state.viajes_nombre = ""
    st.session_state.viajes_telefono = ""
    st.session_state.viajes_correo = ""
    st.session_state.viajes_fecha_nacimiento = date(1995, 1, 1)


def guardar_log_supabase(data):
    supabase.table("logs_cotizaciones").insert(data).execute()


# =====================================================
# MASIVOS - PDF
# =====================================================

def generar_pdf_masivos(
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
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#B8C7DB")),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
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

    table_cob.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C7DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    table_cob.wrapOn(c, 40, 0)
    table_cob.drawOn(c, 30, 470)

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(40, 35, "Coberturas sujetas a condiciones de contratación y vigencia de la proforma.")
    c.setFillColor(colors.black)

    c.save()
    return temp_pdf.name


# =====================================================
# VIAJES - FUNCIONES
# =====================================================

def calcular_edad_viajes(fecha_nacimiento: date, fecha_referencia: date = date.today()) -> int:
    edad = fecha_referencia.year - fecha_nacimiento.year

    if (fecha_referencia.month, fecha_referencia.day) < (
        fecha_nacimiento.month,
        fecha_nacimiento.day
    ):
        edad -= 1

    return edad


def calcular_dias_viajes(fecha_inicio: date, fecha_fin: date) -> int:
    return (fecha_fin - fecha_inicio).days + 1


def calcular_upgrade_viajes(nombre_upgrade: str, dias: int) -> float:
    upgrade = UPGRADES_VIAJES[nombre_upgrade]

    if upgrade["tipo"] == "diario":
        return upgrade["valor"] * dias

    return upgrade["valor"]


def calcular_cotizacion_viajes(
    producto,
    fecha_nacimiento,
    fecha_inicio,
    fecha_fin,
    upgrades_seleccionados
):
    producto_info = PRODUCTOS_VIAJES[producto]

    edad = calcular_edad_viajes(fecha_nacimiento)
    dias = calcular_dias_viajes(fecha_inicio, fecha_fin)

    if fecha_fin < fecha_inicio:
        return {
            "valido": False,
            "mensaje": "La fecha fin no puede ser menor a la fecha inicio."
        }

    if edad < producto_info["edad_min"] or edad > producto_info["edad_max"]:
        return {
            "valido": False,
            "mensaje": f"No se puede cotizar. Edad permitida: {producto_info['edad_min']} a {producto_info['edad_max']} años.",
            "edad": edad,
            "dias": dias
        }

    if dias < producto_info["dias_min"] or dias > producto_info["dias_max"]:
        return {
            "valido": False,
            "mensaje": f"Rango de días incorrecto. Días permitidos: {producto_info['dias_min']} a {producto_info['dias_max']}.",
            "edad": edad,
            "dias": dias
        }

    tarifa_diaria = producto_info["tarifa_diaria"]
    subtotal_base = dias * tarifa_diaria

    detalle_upgrades = []
    total_upgrades = 0

    for upgrade in upgrades_seleccionados:
        valor_upgrade = calcular_upgrade_viajes(upgrade, dias)
        total_upgrades += valor_upgrade

        detalle_upgrades.append({
            "upgrade": upgrade,
            "tipo": UPGRADES_VIAJES[upgrade]["tipo"],
            "valor": valor_upgrade
        })

    subtotal = subtotal_base + total_upgrades
    iva = subtotal * IVA
    total = subtotal + iva

    return {
        "valido": True,
        "producto": producto,
        "edad": edad,
        "dias": dias,
        "tarifa_diaria": tarifa_diaria,
        "subtotal_base": subtotal_base,
        "detalle_upgrades": detalle_upgrades,
        "total_upgrades": total_upgrades,
        "subtotal": subtotal,
        "iva": iva,
        "total": total,
        "mensaje_edad": "Edad correcta.",
        "mensaje_dias": "Rango de días correcto."
    }


def generar_pdf_viajes(
    resultado,
    fecha_inicio,
    fecha_fin,
    nombre_cliente,
    telefono_cliente,
    correo_cliente
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

    def draw_header(titulo):
        logo = Image(logo_path)
        logo.drawHeight = 45
        logo.drawWidth = 150
        logo.drawOn(c, 40, 735)

        c.setFillColor(colors.HexColor("#1F3A5F"))
        c.setFont("Helvetica-Bold", 18)
        c.drawString(220, 748, titulo)

        c.setStrokeColor(colors.HexColor("#D9E2F3"))
        c.setLineWidth(1)
        c.line(40, 728, 570, 728)

        c.setFillColor(colors.black)

    def draw_footer():
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(colors.grey)
        c.drawString(
            40,
            35,
            "Coberturas sujetas a condiciones de contratación y vigencia de la proforma."
        )
        c.setFillColor(colors.black)

    def draw_section_title(text, x, y):
        c.setFillColor(colors.HexColor("#1F3A5F"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, text)
        c.setFillColor(colors.black)

    def make_key_value_table(rows, col_widths=(170, 330), row_height=22):
        table = Table(rows, colWidths=list(col_widths), rowHeights=row_height)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B8C7DB")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEEB")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]))
        return table

    draw_header("Proforma de Viajes")

    draw_section_title("Datos personales", 40, 700)

    data_personales = [
        ["Nombre pasajero", nombre_cliente],
        ["Teléfono", telefono_cliente],
        ["Correo", correo_cliente],
    ]

    table_personales = make_key_value_table(data_personales)
    table_personales.wrapOn(c, 40, 0)
    table_personales.drawOn(c, 40, 620)

    draw_section_title("Datos del viaje", 40, 590)

    data_viaje = [
        ["Producto", resultado["producto"]],
        ["Edad pasajero", f"{resultado['edad']} años"],
        ["Fecha inicio", fecha_inicio.strftime("%d/%m/%Y")],
        ["Fecha fin", fecha_fin.strftime("%d/%m/%Y")],
        ["Días de viaje", str(resultado["dias"])],
        ["Fecha emisión", fecha_hoy.strftime("%d/%m/%Y")],
        ["Válido hasta", vigencia.strftime("%d/%m/%Y")]
    ]

    table_viaje = make_key_value_table(data_viaje)
    table_viaje.wrapOn(c, 40, 0)
    table_viaje.drawOn(c, 40, 410)

    draw_section_title("Resumen económico", 40, 380)

    data_resumen = [
        ["Concepto", "Valor"],
        ["Subtotal base", f"${resultado['subtotal_base']:,.2f}"],
        ["Upgrades", f"${resultado['total_upgrades']:,.2f}"],
        ["Subtotal", f"${resultado['subtotal']:,.2f}"],
        ["IVA 15%", f"${resultado['iva']:,.2f}"],
        ["Total final", f"${resultado['total']:,.2f}"],
    ]

    table_resumen = Table(data_resumen, colWidths=[300, 170], rowHeights=26)
    table_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F2F6FC")),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#B8C7DB")),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))

    table_resumen.wrapOn(c, 40, 0)
    table_resumen.drawOn(c, 40, 210)

    if resultado["detalle_upgrades"]:
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(
            40,
            185,
            "El detalle de upgrades seleccionados se muestra en la siguiente página."
        )
        c.setFillColor(colors.black)

    draw_footer()

    if resultado["detalle_upgrades"]:
        c.showPage()
        draw_header("Detalle de Upgrades")

        draw_section_title("Upgrades seleccionados", 40, 700)

        data_upgrades = [[
            Paragraph("<b>Upgrade</b>", style_header),
            Paragraph("<b>Tipo</b>", style_header),
            Paragraph("<b>Valor</b>", style_header),
        ]]

        for row in resultado["detalle_upgrades"]:
            data_upgrades.append([
                Paragraph(str(row["upgrade"]), style_normal),
                Paragraph(str(row["tipo"]).capitalize(), style_normal),
                Paragraph(f"${row['valor']:,.2f}", style_normal),
            ])

        table_upg = Table(
            data_upgrades,
            colWidths=[280, 120, 120],
            repeatRows=1
        )

        table_upg.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C7DB")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))

        table_upg.wrapOn(c, 40, 0)
        table_upg.drawOn(c, 40, 610)

        draw_footer()

    c.save()
    return temp_pdf.name


# =====================================================
# SELECCIÓN INICIAL
# =====================================================

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


# =====================================================
# MÓDULO VIAJES
# =====================================================

if st.session_state.modulo == "VIAJES":
    st.title("✈️ Cotizador de Viajes")

    if st.button("Volver al inicio"):
        volver_inicio()
        st.rerun()

    st.markdown("Completa los datos del pasajero y del viaje para calcular la cotización.")

    st.markdown("---")
    st.subheader("Datos personales")

    col_personal_1, col_personal_2 = st.columns(2)

    with col_personal_1:
        nombre_cliente = st.text_input("Nombre del pasajero", key="viajes_nombre")
        telefono_cliente = st.text_input("Teléfono", key="viajes_telefono")

    with col_personal_2:
        correo_cliente = st.text_input("Correo electrónico", key="viajes_correo")

    campos_faltantes = []

    if nombre_cliente.strip() == "":
        campos_faltantes.append("Nombre del pasajero")
    if telefono_cliente.strip() == "":
        campos_faltantes.append("Teléfono")
    if correo_cliente.strip() == "":
        campos_faltantes.append("Correo electrónico")

    if campos_faltantes:
        st.warning("Complete los siguientes campos: " + ", ".join(campos_faltantes))
        st.stop()

    st.markdown("---")
    st.subheader("Datos del viaje")

    col1, col2 = st.columns(2)

    with col1:
        producto_viaje = st.selectbox(
            "Producto",
            list(PRODUCTOS_VIAJES.keys())
        )

        fecha_nacimiento_viaje = st.date_input(
            "Fecha de nacimiento",
            key="viajes_fecha_nacimiento",
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY"
        )

    with col2:
        fecha_inicio_viaje = st.date_input(
            "Fecha inicio del viaje",
            value=date.today(),
            format="DD/MM/YYYY"
        )

        fecha_fin_viaje = st.date_input(
            "Fecha fin del viaje",
            value=date.today(),
            format="DD/MM/YYYY"
        )

    st.markdown("---")

    upgrades_seleccionados = st.multiselect(
        "Upgrades / adicionales",
        list(UPGRADES_VIAJES.keys())
    )

    st.markdown("---")

    resultado_viaje = calcular_cotizacion_viajes(
        producto=producto_viaje,
        fecha_nacimiento=fecha_nacimiento_viaje,
        fecha_inicio=fecha_inicio_viaje,
        fecha_fin=fecha_fin_viaje,
        upgrades_seleccionados=upgrades_seleccionados
    )

    st.subheader("Resultado de la cotización")

    if not resultado_viaje["valido"]:
        st.error(resultado_viaje["mensaje"])

        if "edad" in resultado_viaje:
            st.write(f"**Edad calculada:** {resultado_viaje['edad']} años")

        if "dias" in resultado_viaje:
            st.write(f"**Días calculados:** {resultado_viaje['dias']} días")

        st.stop()

    col_a, col_b, col_c, col_d = st.columns(4)

    col_a.metric("Edad", f"{resultado_viaje['edad']} años")
    col_b.metric("Días de viaje", resultado_viaje["dias"])
    col_c.metric("Tarifa diaria", f"${resultado_viaje['tarifa_diaria']:,.2f}")
    col_d.metric("Total", f"${resultado_viaje['total']:,.2f}")

    st.success("Cotización válida.")
    st.info(PRODUCTOS_VIAJES[producto_viaje]["descripcion"])

    st.markdown("---")
    st.subheader("Detalle económico")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Subtotal base", f"${resultado_viaje['subtotal_base']:,.2f}")
    col2.metric("Total upgrades", f"${resultado_viaje['total_upgrades']:,.2f}")
    col3.metric("IVA 15%", f"${resultado_viaje['iva']:,.2f}")
    col4.metric("Total final", f"${resultado_viaje['total']:,.2f}")

    if resultado_viaje["detalle_upgrades"]:
        st.markdown("---")
        st.subheader("Detalle de upgrades")

        st.dataframe(
            pd.DataFrame(resultado_viaje["detalle_upgrades"]),
            hide_index=True,
            use_container_width=True
        )

    with st.expander("Ver detalle de validación"):
        producto_info = PRODUCTOS_VIAJES[producto_viaje]

        st.write(f"**Producto:** {producto_viaje}")
        st.write(f"**Edad permitida:** {producto_info['edad_min']} a {producto_info['edad_max']} años")
        st.write(f"**Días permitidos:** {producto_info['dias_min']} a {producto_info['dias_max']} días")
        st.write(f"**Validación edad:** {resultado_viaje['mensaje_edad']}")
        st.write(f"**Validación días:** {resultado_viaje['mensaje_dias']}")

    st.markdown("---")

    if st.button("Generar Proforma PDF"):
        try:
            data_log = {
                "fecha_registro": datetime.now().isoformat(),
                "modulo": "VIAJES",
                "tipo_cliente": "VIAJES",
                "cliente": nombre_cliente,
                "cedula": None,
                "fecha_nacimiento": str(fecha_nacimiento_viaje),
                "direccion": None,
                "telefono": telefono_cliente,
                "mail": correo_cliente,
                "ruc": None,
                "vendedor": st.session_state.vendedor,
                "asistencia": "VIAJES",
                "plan": producto_viaje,
                "periodo": f"{resultado_viaje['dias']} días",
                "personas": 1,
                "cop_mensual": round(float(resultado_viaje["tarifa_diaria"]), 2),
                "cop_por_persona": round(float(resultado_viaje["subtotal"]), 2),
                "precio_total": round(float(resultado_viaje["total"]), 2)
            }

            guardar_log_supabase(data_log)

            pdf_path = generar_pdf_viajes(
                resultado=resultado_viaje,
                fecha_inicio=fecha_inicio_viaje,
                fecha_fin=fecha_fin_viaje,
                nombre_cliente=nombre_cliente,
                telefono_cliente=telefono_cliente,
                correo_cliente=correo_cliente
            )

            st.success("Proforma generada y registrada correctamente en Supabase.")

            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="Descargar Proforma",
                    data=f,
                    file_name=f"proforma_viajes_{nombre_cliente.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"Ocurrió un error al generar o guardar la proforma: {e}")

    st.markdown("---")

    if st.button("Nueva Cotización"):
        nueva_cotizacion()
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# =====================================================
# MÓDULO MASIVOS
# =====================================================

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


periodo_meses = PERIODOS[periodo_label]
cop_mensual = PLANES[plan_nombre]["cop_mensual"]

if periodo_label == "Mensual":
    cop_final_persona = cop_mensual
else:
    cop_final_persona = cop_mensual * periodo_meses

precio_total = cop_final_persona * personas
df_coberturas = pd.DataFrame(PLANES[plan_nombre]["coberturas"])


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


st.markdown("---")

if st.button("Generar Proforma PDF"):
    try:
        data_log = {
            "fecha_registro": datetime.now().isoformat(),
            "modulo": st.session_state.modulo,
            "tipo_cliente": st.session_state.tipo_cliente,
            "cliente": cliente,
            "cedula": cedula if st.session_state.tipo_cliente == "B2C" else None,
            "fecha_nacimiento": str(fecha_nacimiento) if st.session_state.tipo_cliente == "B2C" else None,
            "direccion": direccion if st.session_state.tipo_cliente == "B2C" else None,
            "telefono": telefono if st.session_state.tipo_cliente == "B2C" else None,
            "mail": mail if st.session_state.tipo_cliente == "B2C" else None,
            "ruc": ruc if st.session_state.tipo_cliente == "B2B" else None,
            "vendedor": st.session_state.vendedor,
            "asistencia": "TELEMEDICINA",
            "plan": plan_nombre,
            "periodo": periodo_label,
            "personas": int(personas),
            "cop_mensual": round(float(cop_mensual), 2),
            "cop_por_persona": round(float(cop_final_persona), 2),
            "precio_total": round(float(precio_total), 2)
        }

        guardar_log_supabase(data_log)

        pdf_path = generar_pdf_masivos(
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


st.markdown("---")
st.button("Nueva Cotización", on_click=nueva_cotizacion)

st.markdown("</div>", unsafe_allow_html=True)
