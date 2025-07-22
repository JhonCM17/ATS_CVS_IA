import fitz  # PyMuPDF
import docx
import pandas as pd
import streamlit as st
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime

# Cargar clave API
load_dotenv()
client = OpenAI()

# Extraer texto desde PDF
def extraer_texto_pdf(file):
    texto = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for pagina in doc:
            texto += pagina.get_text()
    return texto

# Extraer texto desde DOCX
def extraer_texto_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

# Evaluar CV con GPT
def evaluar_cv(cv_texto, perfil_deseado):
    prompt = f"""
El reclutador busca el siguiente perfil:

{perfil_deseado}

Evalúa el siguiente CV según ese perfil. Asigna una puntuación del 1 al 10 (donde 10 es perfecto) y justifica brevemente tu calificación.

CV:
\"\"\"
{cv_texto}
\"\"\"

Devuelve el resultado en este formato:
Puntuación: X/10
Justificación: ...
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "Eres un experto en selección de personal y reclutamiento."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# === INTERFAZ STREAMLIT ===
st.set_page_config(page_title="Evaluador de CVs IA", layout="wide")
st.title("🤖 Evaluador de CVs con IA")
st.markdown("Carga CVs en PDF o Word y obtén puntuación automática comparada con el perfil deseado.")

perfil = st.text_area("📝 Perfil buscado", placeholder="Ejemplo: Diseñador gráfico con experiencia en Figma, branding y creatividad.")

archivos = st.file_uploader("📂 Cargar CVs (.pdf o .docx)", type=["pdf", "docx"], accept_multiple_files=True)

if st.button("📊 Evaluar CVs"):
    if not perfil:
        st.warning("⚠️ Por favor ingresa el perfil buscado.")
    elif not archivos:
        st.warning("⚠️ Carga al menos un archivo.")
    else:
        resultados = []

        for archivo in archivos:
            nombre = archivo.name
            st.write(f"⏳ Evaluando: `{nombre}`")

            if nombre.lower().endswith(".pdf"):
                texto = extraer_texto_pdf(archivo)
            elif nombre.lower().endswith(".docx"):
                texto = extraer_texto_docx(archivo)
            else:
                st.warning(f"Ignorado: {nombre}")
                continue

            evaluacion = evaluar_cv(texto, perfil)
            resultados.append({"archivo": nombre, "evaluación": evaluacion})
            st.success(f"✅ {nombre} evaluado")

        df = pd.DataFrame(resultados)
        st.subheader("📋 Resultados de Evaluación")
        st.dataframe(df)

        # Guardar en Excel en memoria
        buffer = BytesIO()
        nombre_archivo = f"resultados_evaluados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="⬇️ Descargar archivo Excel",
            data=buffer,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
