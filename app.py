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

# --- PROCESSAMENTO OMR ROBUSTO (DETECÇÃO DE ÂNCORAS) ---

def ordenar_pontos(pts):
    """ Ordena os 4 cantos: top-left, top-right, bottom-right, bottom-left """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def extrair_cartao_desentortado(gray):
    """ Encontra os marcadores pretos dos cantos e desentorta a imagem """
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Encontrar contornos
    cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    quadrados = []
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        
        # Filtrar contornos que pareçam os marcadores quadrados dos cantos
        if len(approx) == 4 and cv2.contourArea(c) > 500:
            (x, y, w, h) = cv2.boundingRect(approx)
            ar = w / float(h)
            if 0.7 <= ar <= 1.3:  # Proporção próxima de um quadrado
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    quadrados.append((cX, cY))

    # Se encontrar ao menos 4 marcadores, aplica a transformação de perspectiva
    if len(quadrados) >= 4:
        # Pega os 4 marcadores mais externos
        pts = np.array(quadrados[:4], dtype="float32")
        rect = ordenar_pontos(pts)
        
        W, H = 1000, 1400
        dst = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(gray, M, (W, H))
        return warped, True
    else:
        # Se não detectar os 4 cantos com precisão, força redimensionamento direto
        return cv2.resize(gray, (1000, 1400)), False

def processar_gabarito_omr(imagem_np):
    gray = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
    img_retificada, detectou_ancoras = extrair_cartao_desentortado(gray)
    
    img_debug = cv2.cvtColor(img_retificada, cv2.COLOR_GRAY2RGB)
    
    # Binarizar para destacar as marcações a caneta
    blurred = cv2.GaussianBlur(img_retificada, (3, 3), 0)
    thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    respostas_lidas = {}

    # Com a imagem desentortada e retificada em (1000 x 1400),
    # as coordenadas das tabelas passam a ser 100% precisas e constantes:
    blocos = {
        "Biologia": (1, (430, 680), (195, 385)),
        "Química": (21, (430, 680), (615, 805)),
        "Física": (11, (780, 1030), (195, 385)),
        "Matemática": (31, (780, 1030), (615, 805))
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
                
                # Pega 40% central do círculo (foco total na bolha)
                miolo = bolha[int(hb*0.3):int(hb*0.7), int(wb*0.3):int(wb*0.7)]
                total_preenchido = cv2.countNonZero(miolo)
                pixels_por_opcao.append(total_preenchido)

                # Desenha marcação na imagem tratada para confirmação visual
                abs_x1 = x1 + bx1 + int(wb*0.3)
                abs_y1 = y1 + by1 + int(hb*0.3)
                abs_x2 = x1 + bx1 + int(wb*0.7)
                abs_y2 = y1 + by1 + int(hb*0.7)
                cv2.rectangle(img_debug, (abs_x1, abs_y1), (abs_x2, abs_y2), (0, 255, 0), 1)

            max_pixels = max(pixels_por_opcao)
            
            # Validação do preenchimento
            if max_pixels > 20:
                idx_marcado = pixels_por_opcao.index(max_pixels)
                respostas_lidas[questao_num] = OPCOES[idx_marcado]
            else:
                respostas_lidas[questao_num] = "Sem Resposta"

    return respostas_lidas, img_debug, detectou_ancoras

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
        
        with st.spinner("Desentortando imagem e processando respostas..."):
            respostas_aluno, img_debug, detectou_ancoras = processar_gabarito_omr(img_np)
        
        if detectou_ancoras:
            st.success("✅ Âncoras do cartão detectadas com sucesso! Imagem alinhada.")
        else:
            st.warning("⚠️ Marcadores das pontas não foram 100% identificados. Enquadre melhor a folha inteira na foto.")

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

        with st.expander("🔍 Ver cartão retificado e verificação de leitura"):
            st.image(img_debug, caption="Foto desentortada e retificada com caixas verdes sobre as bolhas", use_container_width=True)
            st.write(respostas_aluno)
