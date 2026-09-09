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

# --- ALGORITMO DE LEITURA ÓPTICA (OMR REAL) ---

def ordenar_pontos(pts):
    """ Ordena os 4 cantos detectados: [superior-esq, superior-dir, inferior-dir, inferior-esq] """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def alinhar_folha(imagem_np):
    """ Detecta os marcadores nos cantos e desentorta a imagem """
    gray = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

    doc_cnt = None
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            doc_cnt = approx
            break

    # Se encontrar os contornos externos da folha/ancoras
    if doc_cnt is not None:
        pts = doc_cnt.reshape(4, 2)
        rect = ordenar_pontos(pts)
        (tl, tr, br, bl) = rect

        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(gray, M, (maxWidth, maxHeight))
        return cv2.resize(warped, (1000, 1400))
    else:
        # Se não encontrar os cantos com precisão, redimensiona diretamente
        return cv2.resize(gray, (1000, 1400))

def processar_gabarito_real(imagem_np):
    img_alinhada = alinhar_folha(imagem_np)
    
    # Binarizar a imagem (deixar apenas traços escuros e fundo branco)
    _, thresh = cv2.threshold(img_alinhada, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    respostas_lidas = {}

    # Mapeamento proporcional das 4 colunas de blocos na folha CEDAC
    # Formato dos blocos: Biologia(Esq-Topo), Química(Dir-Topo), Física(Esq-Baixo), Matemática(Dir-Baixo)
    blocos = {
        "Biologia": {"q_inicio": 1, "x_range": (180, 480), "y_range": (380, 680)},
        "Química": {"q_inicio": 21, "x_range": (610, 910), "y_range": (380, 680)},
        "Física": {"q_inicio": 11, "x_range": (180, 480), "y_range": (760, 1060)},
        "Matemática": {"q_inicio": 31, "x_range": (610, 910), "y_range": (760, 1060)}
    }

    for materia, coords in blocos.items():
        q_num = coords["q_inicio"]
        x1, x2 = coords["x_range"]
        y1, y2 = coords["y_range"]

        h_linha = (y2 - y1) / 10.0
        w_col = (x2 - x1) / 5.0

        for i in range(10):
            questao_atual = q_num + i
            maior_preenchimento = 0
            opcao_escolhida = None

            for j, opcao in enumerate(OPCOES):
                cx1 = int(x1 + j * w_col)
                cx2 = int(x1 + (j + 1) * w_col)
                cy1 = int(y1 + i * h_linha)
                cy2 = int(y1 + (i + 1) * h_linha)

                # Cortar a bolha individual
                bolha = thresh[cy1:cy2, cx1:cx2]
                total_pixels = cv2.countNonZero(bolha)

                if total_pixels > maior_preenchimento:
                    maior_preenchimento = total_pixels
                    opcao_escolhida = opcao

            # Threshold para evitar marcar questões em branco (mínimo de preenchimento)
            if maior_preenchimento > 100:
                respostas_lidas[questao_atual] = opcao_escolhida
            else:
                respostas_lidas[questao_atual] = "Sem Resposta"

    return respostas_lidas, img_alinhada

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
        
        with st.spinner("Lendo círculos preenchidos..."):
            respostas_aluno, imagem_alinhada = processar_gabarito_real(img_np)
        
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

        # Exibir mapa de respostas identificadas para conferência
        with st.expander("🔍 Ver respostas detectadas pelo app"):
            st.json(respostas_aluno)
