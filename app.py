import json
import os
import cv2
import numpy as np
import streamlit as st
from PIL import Image
import google.generativeai as genai

st.set_page_config(page_title="Corretor Inteligente CEDAC", layout="wide")

st.title("📝 Corretor Automático de Cartão-Resposta (IA)")
st.subheader("C.E. DEP. ALEXANDRE COSTA - CEDAC")

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
st.sidebar.header("⚙️ Configuração do Simulado")
area_selecionada = st.sidebar.selectbox("Escolha a Área da Prova:", list(ESTRUTURA_AREAS.keys()))

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
st.sidebar.header(f"🎯 Gabarito: {area_selecionada}")

texto_gabarito = st.sidebar.text_area(
    "Entrada rápida (ex: A,B,C,D... ou 40 letras juntas):",
    placeholder="Cole aqui as 40 respostas para esta área..."
)

if st.sidebar.button("⚡ Salvar Gabarito desta Área"):
    letras = [char.upper() for char in texto_gabarito.replace(" ", "").replace(",", "").replace("\n", "") if char.upper() in OPCOES]
    if len(letras) == 40:
        gabarito_novo = {str(i+1): letras[i] for i in range(40)}
        salvar_gabarito_area(arquivo_gabarito_atual, gabarito_novo)
        gabarito_ativo = gabarito_novo
        st.sidebar.success(f"Gabarito de {area_selecionada} salvo com sucesso!")
    else:
        st.sidebar.error(f"Encontradas {len(letras)} alternativas. Necessário exatas 40 respostas.")

with st.sidebar.expander("📝 Editar Questão por Questão"):
    gabarito_temp = {}
    for i in range(1, 41):
        idx_padrao = OPCOES.index(gabarito_ativo.get(str(i), "A"))
        gabarito_temp[str(i)] = st.selectbox(f"Questão {i:02d}:", OPCOES, index=idx_padrao, key=f"q_select_{area_selecionada}_{i}")
    
    if st.button("💾 Salvar Edição Manual"):
        salvar_gabarito_area(arquivo_gabarito_atual, gabarito_temp)
        gabarito_ativo = gabarito_temp
        st.success(f"Gabarito manual de {area_selecionada} salvo!")

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

# --- CHAVE DA API GEMINI ---
api_key_env = st.secrets.get("GEMINI_API_KEY", "")
api_key = st.sidebar.text_input("Chave API Gemini:", value=api_key_env, type="password")

# --- INTERFACE PRINCIPAL ---
st.write("---")
st.info(f"📍 **Área Selecionada:** {area_selecionada}")

# Padrão alterado para Galeria/Câmera NAtiva do Sistema
opcao_envio = st.radio(
    "Escolha a forma de envio:", 
    ["Carregar Arquivo / Câmera do Celular", "Câmera Integrada (Navegador)"],
    index=0
)

imagem_capturada = None

if opcao_envio == "Carregar Arquivo / Câmera do Celular":
    imagem_capturada = st.file_uploader("Selecione 'Câmera' ou escolha uma foto da galeria", type=["jpg", "jpeg", "png"])
else:
    imagem_capturada = st.camera_input("Tire a foto do cartão-resposta")

if imagem_capturada is not None:
    image = Image.open(imagem_capturada)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.image(image, caption="Gabarito Capturado", use_container_width=True)

    with col2:
        st.write("### 📊 Resultado da Correção")
        
        if not api_key:
            st.error("⚠️ Insira a Chave de API do Gemini no menu lateral para ativar a leitura por IA.")
        else:
            with st.spinner("A IA está analisando a foto e lendo as respostas..."):
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

                    st.markdown("#### Campo Exclusivo da Banca")
                    
                    res_col1, res_col2 = st.columns(2)
                    itens = list(pontos.items())
                    
                    with res_col1:
                        st.metric(itens[0][0], f"{itens[0][1]} / 10")
                        st.metric(itens[2][0], f"{itens[2][1]} / 10")
                    with res_col2:
                        st.metric(itens[1][0], f"{itens[1][1]} / 10")
                        st.metric(itens[3][0], f"{itens[3][1]} / 10")
                        
                    st.divider()
                    st.subheader(f"🏆 NOTA FINAL: {nota_final:.1f} / 10,0")

                    with st.expander("🔍 Ver detalhes de cada questão lida pela IA"):
                        st.json(respostas_aluno)

                except Exception as e:
                    st.error(f"Erro no processamento da imagem: {e}")
