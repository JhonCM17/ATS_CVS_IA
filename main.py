import fitz  # PyMuPDF
import docx
import pandas as pd
import streamlit as st
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import re

# Cargar API key
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

# Prompt y evaluación con OpenAI
def evaluar_cv(cv_texto, perfil_deseado):
    prompt = f"""
A partir del siguiente CV, extrae esta información estructurada:

- Nombres completos del candidato
- Correo electrónico
- Número de teléfono
- Sexo (se deduce a partir del nombre y solo puedes usar "Masculino", "Femenino")
- Estudios: carrera(s) y especialización(es)
- Clasifica el CV en base a las áreas más afines. Las opciones son: ["Data analytics", "Producto", "Diseño Gráfico", "TI", "Planeamiento", "RRHH", "Marketing", "Pagos"] pero no los coloques con "" o [] solo la palabra como tal .

Luego, evalúa qué tan bien se ajusta este candidato al siguiente perfil buscado:

Perfil buscado:
{perfil_deseado}

Responde en este formato exacto:

Nombres: ...
Correo: ...
Teléfono: ...
Sexo: ...
Estudios: ...
Áreas: ...
Puntuación: X/10
Justificación: ...

CV:
\"\"\"
{cv_texto}
\"\"\"
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "Eres un experto en selección de personal, extracción de datos de CVs y clasificación profesional."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# Extraer cada campo de la respuesta estructurada
def parsear_evaluacion(texto):
    def extraer(campo):
        patron = rf"{campo}:\s*(.*)"
        match = re.search(patron, texto, re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    return {
        "nombres": extraer("Nombres"),
        "correo": extraer("Correo"),
        "teléfono": extraer("Teléfono"),
        "sexo": extraer("Sexo"),
        "estudios": extraer("Estudios"),
        "áreas": extraer("Áreas"),
        "puntuación": extraer("Puntuación"),
        "justificación": extraer("Justificación")
    }

# ===================== INTERFAZ STREAMLIT ======================

st.set_page_config(page_title="Evaluador de CVs IA", layout="wide")
st.title("🤖 Evaluador de CVs con IA")
st.markdown("Carga CVs en PDF o Word y obtén información estructurada + puntuación según el perfil deseado.")

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
            info = parsear_evaluacion(evaluacion)
            info["archivo"] = nombre
            resultados.append(info)
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
