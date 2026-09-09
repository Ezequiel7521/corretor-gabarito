import cv2
import numpy as np
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Corretor de Gabarito - SEDUC MA", layout="wide")

st.title("📝 Corretor Automático de Cartão-Resposta")
st.subheader("C.E. DEP. ALEXANDRE COSTA - CEDAC")

# --- CADASTRO DO GABARITO OFICIAL ---
st.sidebar.header("🎯 Gabarito Oficial")

OPCOES = ["A", "B", "C", "D", "E"]
materias = {
    "Biologia (Q01 - Q10)": (1, 10),
    "Física (Q11 - Q20)": (11, 20),
    "Química (Q21 - Q30)": (21, 30),
    "Matemática (Q31 - Q40)": (31, 40)
}

gabarito_oficial = {}

with st.sidebar.form("form_gabarito"):
    for materia, (inicio, fim) in materias.items():
        st.subheader(materia)
        for q in range(inicio, fim + 1):
            gabarito_oficial[q] = st.selectbox(
                f"Questão {q:02d}:", 
                OPCOES, 
                index=0, 
                key=f"q_{q}"
            )
    salvar = st.form_submit_button("Salvar Gabarito")

# --- PROCESSAMENTO DE IMAGEM ---
def extrair_respostas(imagem_np):
    gray = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Dicionário com leitura simulada/estruturada das questões
    respostas_detectadas = {}
    for q in range(1, 41):
        respostas_detectadas[q] = "A" # Substituir com cálculo dos círculos (countNonZero)
        
    return respostas_detectadas, thresh

# --- ENTRADA DE IMAGEM VIA CÂMERA DO CELULAR ---
st.write("---")

opcao_envio = st.radio("Escolha a forma de envio:", ["Tirar Foto (Câmera)", "Carregar Arquivo (Galeria)"])

imagem_capturada = None

if opcao_envio == "Tirar Foto (Câmera)":
    imagem_capturada = st.camera_input("Tire a foto do cartão-resposta")
else:
    imagem_capturada = st.file_uploader("Escolha a foto na galeria", type=["jpg", "jpeg", "png"])

if imagem_capturada is not None:
    image = Image.open(imagem_capturada)
    img_np = np.array(image)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.image(image, caption="Gabarito Capturado", use_container_width=True)

    with col2:
        st.write("### 📊 Resultado da Correção")
        
        respostas_aluno, imagem_processada = extrair_respostas(img_np)
        
        pontos = {"Biologia": 0, "Física": 0, "Química": 0, "Matemática": 0}
        
        for q in range(1, 11):
            if respostas_aluno[q] == gabarito_oficial[q]:
                pontos["Biologia"] += 1
                
        for q in range(11, 21):
            if respostas_aluno[q] == gabarito_oficial[q]:
                pontos["Física"] += 1
                
        for q in range(21, 31):
            if respostas_aluno[q] == gabarito_oficial[q]:
                pontos["Química"] += 1
                
        for q in range(31, 41):
            if respostas_aluno[q] == gabarito_oficial[q]:
                pontos["Matemática"] += 1

        total_acertos = sum(pontos.values())
        nota_final = (total_acertos / 40.0) * 10.0

        st.markdown("#### Campo Exclusivo da Banca")
        
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric("Biologia", f"{pontos['Biologia']} / 10")
            st.metric("Química", f"{pontos['Química']} / 10")
        with res_col2:
            st.metric("Física", f"{pontos['Física']} / 10")
            st.metric("Matemática", f"{pontos['Matemática']} / 10")
            
        st.divider()
        st.subheader(f"🏆 NOTA FINAL: {nota_final:.1f} / 10,0")
