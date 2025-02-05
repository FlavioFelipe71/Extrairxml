import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st
from io import BytesIO
import base64
import os

##### Oculta o botão Deploy do Streamilit
st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True
)

# Função para ler a imagem e convertê-la para base64
def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return encoded_string        # Exibir o conteúdo do formulário de anamnese emocional
# Caminho da imagem
image_path = "fundo_softdib.jpg"
# Codificação da imagem em base64
base64_image = get_base64_image(image_path)

# CSS para definir a imagem de fundo com transparência
st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.9)), url('data:image/png;base64,{base64_image}') no-repeat center center fixed;
        background-size: cover;
    }}
    </style>
    """,
    unsafe_allow_html=True
)
###### CSS para definir a imagem de fundo [Fim]


def extrair_dados_xml(arquivos):
    dados = []
    
    for arquivo in arquivos:
        try:
            tree = ET.parse(arquivo)
            root = tree.getroot()

            # Obtendo namespace principal
            namespace = {'ns': root.tag.split('}')[0].strip('{')}
            
            for item in root.findall(".//ns:det", namespace):  # Busca todos os produtos
                prod = item.find("ns:prod", namespace)
                imposto = item.find("ns:imposto", namespace)  # Bloco de impostos

                if prod is not None:
                    cod_prod = prod.findtext("ns:cProd", "N/A", namespace).strip()
                    und = prod.findtext("ns:uCom", "N/A", namespace).strip()
                    desc_prod = prod.findtext("ns:xProd", "N/A", namespace).strip()
                    ncm = prod.findtext("ns:NCM", "N/A", namespace).strip()
                    quantidade = prod.findtext("ns:qCom", "N/A", namespace).strip()
                    valor_unitario = prod.findtext("ns:vUnCom", "N/A", namespace).strip()
                    cod_ean13 = prod.findtext("ns:cEANTrib", "N/A", namespace).strip()

                    # Busca o código ANP
                    cod_anp = prod.findtext("ns:cProdANP", "N/A", namespace).strip()
                    if cod_anp == "N/A":  # Tenta buscar sem namespace se não encontrar com namespace
                        cod_anp = prod.findtext("cProdANP", "N/A").strip()
                    if cod_anp == "N/A":  # Procura dentro dos elementos filhos
                        for subelem in prod.iter():
                            if "cProdANP" in subelem.tag:
                                cod_anp = subelem.text.strip()
                                break

                # Verificar a tag imposto e pegar o pIPI corretamente
                if imposto is not None:
                    cst = imposto.findtext("ns:CST", "N/A", namespace).strip()
                    p_ipi = imposto.findtext("ns:pIPI", "N/A", namespace).strip()

                # Tentar buscar CST sem namespace, caso o primeiro não funcione
                    if cst == "N/A":
                        cst = imposto.findtext("CST", "N/A").strip()

                    # Se ainda não encontrar, verificar manualmente no XML
                    if cst == "N/A":
                        for subelem in imposto.iter():
                            if "CST" in subelem.tag:
                                cst = subelem.text.strip()
                                break        

                    # Tentar buscar pIPI sem namespace, caso o primeiro não funcione
                    if p_ipi == "N/A":
                        p_ipi = imposto.findtext("pIPI", "N/A").strip()

                    # Se ainda não encontrar, verificar manualmente no XML
                    if p_ipi == "N/A":
                        for subelem in imposto.iter():
                            if "pIPI" in subelem.tag:
                                p_ipi = subelem.text.strip()
                                break


                    # Adicionar os dados à lista
                    dados.append([cod_prod, desc_prod, ncm, und,quantidade, valor_unitario, cod_ean13, cod_anp, cst, p_ipi])
        
        except Exception as e:
            st.error(f"Erro ao processar {arquivo.name}: {e}")
    
    colunas = ["Cod_Produto", "Desc_Produto", "NCM", "UN","Quantidade", "Valor_Unitario",  "Cod_ean13","Cod_ANP", "CST", "pIPI"]
    df = pd.DataFrame(dados, columns=colunas)

    # Ajustar os valores das colunas conforme solicitado
    # Remover os pontos (para formatação padrão brasileiro)
    df["Quantidade"] = df["Quantidade"].str.replace(".", "").astype(float) / 1000  # Divide por 1000
    df["Valor_Unitario"] = df["Valor_Unitario"].str.replace(".", "").astype(float) / 100000000  # Divide por 100000000
    
    # Ajustar a coluna pIPI para o formato numérico (caso necessário)
    df["pIPI"] = pd.to_numeric(df["pIPI"], errors='coerce')

    # Formatar as colunas para duas casas decimais no formato brasileiro
    df["Quantidade"] = df["Quantidade"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    df["Valor_Unitario"] = df["Valor_Unitario"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    df["pIPI"] = df["pIPI"].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    return df

def converter_csv(df):
    output = BytesIO()
    df.to_csv(output, index=False, sep=';', encoding='utf-8')
    output.seek(0)
    return output

# Configuração do Streamlit
st.set_page_config(page_title="Leitor de XML", layout="wide")
st.title("📂 Leitor de XML para Extração de Dados")

# Upload de arquivos XML
arquivos_xml = st.file_uploader("Faça upload dos arquivos XML", type=["xml"], accept_multiple_files=True)

if arquivos_xml:
    df = extrair_dados_xml(arquivos_xml)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # Botão para download do CSV
        csv_bytes = converter_csv(df)
        st.download_button(label="📥 Baixar CSV", data=csv_bytes, file_name="dados_extraidos.csv", mime="text/csv")
    else:
        st.warning("Nenhum dado encontrado nos arquivos XML. Verifique a estrutura dos arquivos.")
