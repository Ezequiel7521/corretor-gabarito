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

# --- LEITURA ÓPTICA ROBUSTA ---

def processar_gabarito_preciso(imagem_np):
    # Converter para escala de cinza e padronizar tamanho
    gray = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
    gray_resized = cv2.resize(gray, (1000, 1400))
    img_debug = cv2.cvtColor(gray_resized, cv2.COLOR_GRAY2RGB)
    
    # Binarização adaptativa
    blurred = cv2.GaussianBlur(gray_resized, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 15, 3
    )

    respostas_lidas = {}

    # Mapeamento com margem de recuo para não pegar linhas da tabela
    blocos = {
        "Biologia": (1, (430, 720), (230, 470)),
        "Química": (21, (430, 720), (670, 910)),
        "Física": (11, (830, 1120), (230, 470)),
        "Matemática": (31, (830, 1120), (670, 910))
    }

    for materia, (q_inicio, (y1, y2), (x1, x2)) in blocos.items():
        sub_thresh = thresh[y1:y2, x1:x2]
        h_bloco, w_bloco = sub_thresh.shape

        h_linha = h_bloco / 10.0
        w_col = w_bloco / 5.0

        for i in range(10):
            questao_num = q_inicio + i
            pixels_por_opcao = []

            for j in range(5):
                bx1 = int(j * w_col)
                bx2 = int((j + 1) * w_col)
                by1 = int(i * h_linha)
                by2 = int((i + 1) * h_linha)

                bolha = sub_thresh[by1:by2, bx1:bx2]
                hb, wb = bolha.shape
                
                # Pega estritamente o centro do círculo (descarta as bordas)
                miolo = bolha[int(hb*0.3):int(hb*0.7), int(wb*0.3):int(wb*0.7)]
                total_preenchido = cv2.countNonZero(miolo)
                pixels_por_opcao.append(total_preenchido)

                # Desenha marcação verde/vermelha na imagem para depuração
                abs_x1 = x1 + bx1 + int(wb*0.3)
                abs_y1 = y1 + by1 + int(hb*0.3)
                abs_x2 = x1 + bx1 + int(wb*0.7)
                abs_y2 = y1 + by1 + int(hb*0.7)
                cv2.rectangle(img_debug, (abs_x1, abs_y1), (abs_x2, abs_y2), (255, 0, 0), 1)

            max_pixels = max(pixels_por_opcao)
            
            # Identifica a opção marcada
            if max_pixels > 10:
                idx_marcado = pixels_por_opcao.index(max_pixels)
                respostas_lidas[questao_num] = OPCOES[idx_marcado]
            else:
                respostas_lidas[questao_num] = "Sem Resposta"

    return respostas_lidas, img_debug

# --- INTERFACE STREAMLIT ---
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
        
        with st.spinner("Analisando círculos preenchidos..."):
            respostas_aluno, img_debug = processar_gabarito_preciso(img_np)
        
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

        # Exibe imagem com os locais de leitura marcados para verificação
        with st.expander("🔍 Ver mapa de pontos analisados pelo app"):
            st.image(img_debug, caption="Quadros azuis representam os centros das bolhas lidas", use_container_width=True)
            st.write(respostas_aluno)
