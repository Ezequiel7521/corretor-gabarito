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

# --- PROCESSAMENTO AVANÇADO DE VISÃO COMPUTACIONAL (OMR) ---

def extrair_respostas_imagem(imagem_np):
    gray = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Binarização
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )

    respostas_lidas = {}

    # Define regiões de interesse (ROIs) proporcionais para os 4 blocos de matérias
    # [Biologia: Topo-Esq, Química: Topo-Dir, Física: Baixo-Esq, Matemática: Baixo-Dir]
    h, w = thresh.shape
    blocos = {
        "Biologia": (1, range(int(h * 0.35), int(h * 0.65)), range(int(w * 0.15), int(w * 0.48))),
        "Química": (21, range(int(h * 0.35), int(h * 0.65)), range(int(w * 0.52), int(w * 0.85))),
        "Física": (11, range(int(h * 0.68), int(h * 0.95)), range(int(w * 0.15), int(w * 0.48))),
        "Matemática": (31, range(int(h * 0.68), int(h * 0.95)), range(int(w * 0.52), int(w * 0.85)))
    }

    for materia, (q_inicio, y_range, x_range) in blocos.items():
        sub_thresh = thresh[min(y_range):max(y_range), min(x_range):max(x_range)]
        sub_h, sub_w = sub_thresh.shape

        h_linha = sub_h / 10.0
        w_col = sub_w / 5.0

        for i in range(10):
            questao_num = q_inicio + i
            maior_preenchimento = -1
            opcao_marcada = "A"

            for j, opcao in enumerate(OPCOES):
                x1 = int(j * w_col)
                x2 = int((j + 1) * w_col)
                y1 = int(i * h_linha)
                y2 = int((i + 1) * h_linha)

                # Recorta a região do círculo
                bolha = sub_thresh[y1:y2, x1:x2]
                
                # Margem de segurança para evitar pegar bordas de linhas do papel
                h_b, w_b = bolha.shape
                bolha_centro = bolha[int(h_b*0.2):int(h_b*0.8), int(w_b*0.2):int(w_b*0.8)]
                
                total_pixels = cv2.countNonZero(bolha_centro)

                if total_pixels > maior_preenchimento:
                    maior_preenchimento = total_pixels
                    opcao_marcada = opcao

            respostas_lidas[questao_num] = opcao_marcada

    return respostas_lidas

# --- INTERFACE DE CAPTURA ---
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
        
        with st.spinner("Analisando cartão-resposta..."):
            respostas_aluno = extrair_respostas_imagem(img_np)
        
        pontos = {"Biologia": 0, "Física": 0, "Química": 0, "Matemática": 0}
        
        for q in range(1, 11):
            if respostas_aluno.get(q) == gabarito_oficial[q]:
                pontos["Biologia"] += 1
                
        for q in range(11, 21):
            if respostas_aluno.get(q) == gabarito_oficial[q]:
                pontos["Física"] += 1
                
        for q in range(21, 31):
            if respostas_aluno.get(q) == gabarito_oficial[q]:
                pontos["Química"] += 1
                
        for q in range(31, 41):
            if respostas_aluno.get(q) == gabarito_oficial[q]:
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

        # Exibir auditoria de leitura de respostas
        with st.expander("🔍 Conferir respostas identificadas em cada questão"):
            st.write(respostas_aluno)
