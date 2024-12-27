import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
import datetime

# Configuração da página
st.set_page_config(
    page_title="Conversor Lemitti",
    page_icon="📊",
    layout="wide"
)

# Estilo CSS personalizado
st.markdown("""
    <style>
        .main {
            padding: 2rem;
        }
        .stButton>button {
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)

# Título principal
st.title("🔄 Conversor de Planilhas - Formato Lemitti")
st.markdown("---")

# Upload do arquivo
st.subheader("1. Upload do Arquivo")
uploaded_file = st.file_uploader("Faça upload do arquivo CSV ou Excel", type=["csv", "xlsx", "xls"])

if uploaded_file:
    try:
        # Detectar o tipo de arquivo e ler adequadamente
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success("✅ Arquivo carregado com sucesso!")
        
        # Exibir prévia dos dados
        st.subheader("2. Prévia dos Dados")
        st.dataframe(df.head())
        
        # Configuração das colunas
        st.subheader("3. Mapeamento de Colunas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            col_nome = st.selectbox("Coluna para 'NOME':", options=df.columns)
            col_cidade = st.selectbox("Coluna para 'CIDADE':", options=[None] + list(df.columns))
        
        with col2:
            col_uf = st.selectbox("Coluna para 'UF':", options=[None] + list(df.columns))
            col_dt_nasc = st.selectbox("Coluna para 'DT_NASCIMENTO':", options=[None] + list(df.columns))

        # Seleção do formato de saída
        output_format = st.radio(
            "Selecione o formato do arquivo de saída:",
            ["CSV", "TXT"],
            horizontal=True
        )

        if st.button("Processar Dados", type="primary"):
            # Criar DataFrame de saída
            df_output = pd.DataFrame()
            df_output['NOME'] = df[col_nome].str.upper()
            
            if col_cidade:
                df_output['CIDADE'] = df[col_cidade].str.upper()
            else:
                df_output['CIDADE'] = ""
                
            if col_uf:
                df_output['UF'] = df[col_uf].str.upper()
            else:
                df_output['UF'] = ""
                
            if col_dt_nasc:
                # Tentar converter as datas para o formato correto
                try:
                    df_output['DT_NASCIMENTO'] = pd.to_datetime(df[col_dt_nasc]).dt.strftime('%d/%m/%Y')
                except:
                    st.warning("⚠️ Não foi possível converter algumas datas. Mantendo formato original.")
                    df_output['DT_NASCIMENTO'] = df[col_dt_nasc]
            else:
                df_output['DT_NASCIMENTO'] = ""

            # Exibir prévia dos dados convertidos
            st.subheader("4. Dados Convertidos")
            st.dataframe(df_output.head())

            # Preparar arquivo para download
            if output_format == "CSV":
                output = df_output.to_csv(index=False).encode('utf-8')
                file_extension = "csv"
                mime = "text/csv"
            else:  # TXT
                output = df_output.to_csv(index=False, sep='|').encode('utf-8')
                file_extension = "txt"
                mime = "text/plain"
            
            # Botão de download
            st.download_button(
                label=f"📥 Baixar Arquivo {output_format}",
                data=output,
                file_name=f"lemitti_convertido_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}",
                mime=mime
            )

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
        st.info("ℹ️ Por favor, verifique se o arquivo está no formato correto e tente novamente.") 