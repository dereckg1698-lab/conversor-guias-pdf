import streamlit as st
import pandas as pd
import tempfile
import zipfile
import json
import os
import yagmail

from PIL import Image
from dotenv import load_dotenv
from google import genai

# ==========================
# CONFIG
# ==========================

load_dotenv()

try:
    # Streamlit Cloud
    API_KEY = st.secrets["GEMINI_API_KEY"]
    EMAIL_REMITENTE = st.secrets["EMAIL_USER"]
    EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]

except Exception:
    # Ejecución local
    API_KEY = os.getenv("GEMINI_API_KEY")
    EMAIL_REMITENTE = os.getenv("EMAIL_REMITENTE")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

client = genai.Client(api_key=API_KEY)

st.set_page_config(
    page_title="Conversor de Guías a PDF",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Conversor de Guías a PDF")

st.write(
    "Suba una o varias imágenes de guías de remisión."
)

correo_destino = st.text_input(
    "📧 Correo destino (opcional)"
)

imagenes = st.file_uploader(
    "Seleccione imágenes",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

# ==========================
# PROCESAR
# ==========================

if imagenes:

    resultados = []

    pdf_generados = []

    progress = st.progress(0)

    for i, archivo in enumerate(imagenes):

        imagen = Image.open(archivo)

        respuesta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                imagen,
                """
Extrae únicamente:

1. Número de guía de remisión
2. Fecha de emisión

Devuelve SOLO este JSON:

{
  "guia": "",
  "fecha": ""
}
"""
            ]
        )

        texto = respuesta.text.strip()

        texto = texto.replace("```json", "")
        texto = texto.replace("```", "")

        try:

            data = json.loads(texto)

            guia = data["guia"]
            fecha = data["fecha"]

        except:

            guia = "NO_DETECTADA"
            fecha = ""

        pdf_nombre = f"{guia}.pdf"

        pdf_path = os.path.join(
            tempfile.gettempdir(),
            pdf_nombre
        )

        if imagen.mode != "RGB":
            imagen = imagen.convert("RGB")

        imagen.save(pdf_path)

        pdf_generados.append(pdf_path)

        resultados.append(
            {
                "Archivo": archivo.name,
                "Guía": guia,
                "Fecha": fecha,
                "PDF": pdf_nombre
            }
        )

        progress.progress((i + 1) / len(imagenes))

    st.success(f"{len(resultados)} archivos procesados")

    df = pd.DataFrame(resultados)

    st.dataframe(df, use_container_width=True)

    # ==========================
    # UN SOLO PDF
    # ==========================

    if len(pdf_generados) == 1:

        with open(pdf_generados[0], "rb") as f:

            pdf_bytes = f.read()

        st.download_button(
            "📄 Descargar PDF",
            pdf_bytes,
            file_name=os.path.basename(pdf_generados[0]),
            mime="application/pdf"
        )

        archivo_envio = pdf_generados[0]

    # ==========================
    # VARIOS PDF -> ZIP
    # ==========================

    else:

        zip_path = os.path.join(
            tempfile.gettempdir(),
            "guias.zip"
        )

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zipf:

            for pdf in pdf_generados:

                zipf.write(
                    pdf,
                    os.path.basename(pdf)
                )

        with open(zip_path, "rb") as f:

            zip_bytes = f.read()

        st.download_button(
            "📦 Descargar ZIP",
            zip_bytes,
            file_name="guias.zip",
            mime="application/zip"
        )

        archivo_envio = zip_path

    # ==========================
    # ENVIAR CORREO
    # ==========================

    if correo_destino:

        if st.button("📨 Enviar por correo"):

            try:

                yag = yagmail.SMTP(
                    EMAIL_REMITENTE,
                    EMAIL_PASSWORD
                )

                yag.send(
                    to=correo_destino,
                    subject="Guías convertidas a PDF",
                    contents="""
Adjunto encontrará las guías procesadas.
""",
                    attachments=archivo_envio
                )

                st.success(
                    f"Correo enviado a {correo_destino}"
                )

            except Exception as e:

                st.error(str(e))