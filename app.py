import json
import os
import cv2
import numpy as np
import streamlit as st
from PIL import Image
import google.generativeai as genai

# Configuração da página
st.set_page_config(
    page_title="Corretor CEDAC",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILIZAÇÃO CSS PERSONALIZADA ---
st.markdown("""
    <style>
    /* Fundo geral e tipografia */
    .main {
        background-color: #f8fafc;
    }
    
    /* Card de cabeçalho principal */
    .header-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .header-card h1 {
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
        margin-bottom: 4px !important;
    }
    .header-card p {
        color: #e0f2fe !important;
        font-size: 1.0rem !important;
        margin-bottom: 0 !important;
    }

    /* Cards de informação e áreas */
    .info-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #3b82f6;
        padding: 16px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }

    /* Placa de Nota Final */
    .grade-box {
        background: #f0fdf4;
        border: 2px solid #22c55e;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-top: 15px;
    }
    .grade-box h2 {
        color: #15803d !important;
        margin: 0 !important;
        font-size: 2rem !important;
    }

    /* Sidebar personalizada */
    section[data-testid="stSidebar"] {
        background-color: #0f172a !important;
    }
    section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }
    section[data-testid="stSidebar"] .stButton button {
        background-color: #2563eb !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ELEGANTE ---
st.markdown("""
    <div class="header-card">
        <h1>🎓 Corretor Inteligente CEDAC</h1>
        <p>C.E. DEP. ALEXANDRE COSTA — Correção Automática</p>
    </div>
""", unsafe_allow_html=True)

OPCOES = ["A", "B", "C", "D", "E"]

# --- DEFINIÇÃO DAS ÁREAS E ESTRUTURA DE ARQUIVOS DE GABARITO ---
ESTRUTURA_AREAS = {
    "Ciências da Natureza e Matemática": {
        "arquivo": "gabarito_natureza.json",
        "materias": [
            ("Biologia", 1, 10),
            ("Física", 11, 20),
            ("Química", 21, 30),
            ("Matemática", 31, 40)
        ]
    },
    "Ciências Humanas": {
        "arquivo": "gabarito_humanas.json",
        "materias": [
            ("História", 1, 10),
            ("Geografia", 11, 20),
            ("Sociologia", 21, 30),
            ("Filosofia", 31, 40)
        ]
    },
    "Linguagens e Códigos": {
        "arquivo": "gabarito_linguagens.json",
        "materias": [
            ("Língua Portuguesa", 1, 10),
            ("Língua Inglesa", 11, 20),
            ("Artes", 21, 30),
            ("Educação Física", 31, 40)
        ]
    }
}

# --- BARRA LATERAL: SELEÇÃO DA ÁREA ---
st.sidebar.markdown("### ⚙️ Painel do Professor")
area_selecionada = st.sidebar.selectbox("📚 Escolha a Área da Prova:", list(ESTRUTURA_AREAS.keys()))

dados_area = ESTRUTURA_AREAS[area_selecionada]
arquivo_gabarito_atual = dados_area["arquivo"]
materias_atuais = dados_area["materias"]

# --- FUNÇÕES DE PERSISTÊNCIA DE GABARITO POR ÁREA ---
def carregar_gabarito_area(caminho_file):
    if os.path.exists(caminho_file):
        try:
            with open(caminho_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {str(i): "A" for i in range(1, 41)}

def salvar_gabarito_area(caminho_file, gabarito):
    with open(caminho_file, "w", encoding="utf-8") as f:
        json.dump(gabarito, f, ensure_ascii=False, indent=2)

gabarito_ativo = carregar_gabarito_area(arquivo_gabarito_atual)

# --- BARRA LATERAL: GERENCIAMENTO DE GABARITO ---
st.sidebar.divider()
st.sidebar.markdown(f"#### 🎯 Gabarito Oficial: {area_selecionada}")

texto_gabarito = st.sidebar.text_area(
    "Entrada rápida (ex: A,B,C,D... ou 40 letras):",
    placeholder="Cole as 40 respostas aqui...",
    height=100
)

if st.sidebar.button("⚡ Salvar Gabarito Oficial", use_container_width=True):
    letras = [char.upper() for char in texto_gabarito.replace(" ", "").replace(",", "").replace("\n", "") if char.upper() in OPCOES]
    if len(letras) == 40:
        gabarito_novo = {str(i+1): letras[i] for i in range(40)}
        salvar_gabarito_area(arquivo_gabarito_atual, gabarito_novo)
        gabarito_ativo = gabarito_novo
        st.sidebar.success(f"Gabarito de {area_selecionada} salvo com sucesso!")
    else:
        st.sidebar.error(f"Encontradas {len(letras)} alternativas. Necessário exatas 40 respostas.")

with st.sidebar.expander("✏️ Editar Questão por Questão"):
    gabarito_temp = {}
    for i in range(1, 41):
        idx_padrao = OPCOES.index(gabarito_ativo.get(str(i), "A"))
        gabarito_temp[str(i)] = st.selectbox(f"Questão {i:02d}:", OPCOES, index=idx_padrao, key=f"q_select_{area_selecionada}_{i}")
    
    if st.button("💾 Salvar Edição Manual", use_container_width=True):
        salvar_gabarito_area(arquivo_gabarito_atual, gabarito_temp)
        gabarito_ativo = gabarito_temp
        st.success(f"Gabarito manual salvo!")

# --- PROCESSAMENTO COM IA (GEMINI 3.6 FLASH) ---
def ler_gabarito_com_ia(imagem_pil, api_key, estrutura):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.6-flash")
    
    descricao_materias = "\n".join([f"- {m[0]}: Questões {m[1]:02d} a {m[2]:02d}" for m in estrutura])
    
    prompt = f"""
    Análise visual de Cartão-Resposta (OMR).
    Sua tarefa é identificar a alternativa assinalada para as 40 questões da folha.
    As questões estão divididas nos 4 blocos da folha da seguinte forma:
    {descricao_materias}

    Retorne EXATAMENTE um JSON válido com a numeração de 1 a 40 no seguinte formato, sem texto adicional:
    {{
      "1": "A",
      "2": "C",
      "3": "Sem Resposta",
      ...
      "40": "E"
    }}
    Se houver rasura ou mais de uma alternativa preenchida na mesma questão, marque como "Rasura".
    Se a bolha estiver vazia, marque como "Sem Resposta".
    """
    
    response = model.generate_content([prompt, imagem_pil])
    texto_resposta = response.text.strip()
    
    if texto_resposta.startswith("```json"):
        texto_resposta = texto_resposta.replace("```json", "").replace("```", "").strip()
    
    return json.loads(texto_resposta)

# API Key obtida dos Secrets do Streamlit Cloud
api_key = st.secrets.get("GEMINI_API_KEY", "")

# --- INTERFACE PRINCIPAL ---
st.markdown(f"""
    <div class="info-card">
        <strong>📍 Área Selecionada no Momento:</strong> <span style="color:#2563eb; font-weight:bold;">{area_selecionada}</span>
    </div>
""", unsafe_allow_html=True)

opcao_envio = st.radio(
    "📷 Como deseja enviar a foto do cartão-resposta?", 
    ["Carregar Foto (Galeria ou Câmera do Celular)", "Usar Câmera Nativa do Navegador"],
    index=0
)

imagem_capturada = None

if opcao_envio == "Carregar Foto (Galeria ou Câmera do Celular)":
    imagem_capturada = st.file_uploader("Selecione uma imagem ou abra a câmera", type=["jpg", "jpeg", "png"])
else:
    imagem_capturada = st.camera_input("Posicione a folha de resposta na câmera")

if imagem_capturada is not None:
    image = Image.open(imagem_capturada)

    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        st.markdown("##### 📄 Cartão Capturado")
        st.image(image, use_container_width=True)

    with col2:
        st.markdown("##### 📊 Relatório de Desempenho")
        
        if not api_key:
            st.error("⚠️ Chave de API do Gemini não encontrada nos Secrets. Por favor, configure a chave no painel do Streamlit.")
        else:
            with st.spinner("✨ A IA está lendo o cartão-resposta..."):
                try:
                    respostas_aluno = ler_gabarito_com_ia(image, api_key, materias_atuais)
                    
                    pontos = {}
                    for mat_nome, q_inicio, q_fim in materias_atuais:
                        acertos_mat = sum(
                            1 for q in range(q_inicio, q_fim + 1) 
                            if respostas_aluno.get(str(q)) == gabarito_ativo.get(str(q))
                        )
                        pontos[mat_nome] = acertos_mat

                    total_acertos = sum(pontos.values())
                    nota_final = (total_acertos / 40.0) * 10.0

                    # Exibição organizada por disciplina
                    res_col1, res_col2 = st.columns(2)
                    itens = list(pontos.items())
                    
                    with res_col1:
                        st.metric(label=f"📘 {itens[0][0]}", value=f"{itens[0][1]} / 10")
                        st.metric(label=f"📙 {itens[2][0]}", value=f"{itens[2][1]} / 10")
                    with res_col2:
                        st.metric(label=f"📗 {itens[1][0]}", value=f"{itens[1][1]} / 10")
                        st.metric(label=f"📕 {itens[3][0]}", value=f"{itens[3][1]} / 10")
                        
                    # Destaque da Nota Final
                    st.markdown(f"""
                        <div class="grade-box">
                            <span style="color:#166534; font-weight:600; font-size:0.9rem;">NOTA FINAL DO SIMULADO</span>
                            <h2>{nota_final:.1f} <span style="font-size:1.1rem; color:#15803d;">/ 10,0</span></h2>
                        </div>
                    """, unsafe_allow_html=True)

                    with st.expander("🔍 Ver Raio-X detalhado de cada questão"):
                        st.json(respostas_aluno)

                except Exception as e:
                    st.error(f"Erro ao analisar a imagem: {e}")
