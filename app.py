import streamlit as st
import pandas as pd
import time
import os
from datetime import datetime
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import pywhatkit as kit
from streamlit_gsheets import GSheetsConnection

# Variáveis globais para manter a sessão do navegador
if 'driver' not in st.session_state:
    st.session_state.driver = None

def init_browser(headless=False):
    """Inicializa o navegador Chrome controlado pelo Selenium"""
    if st.session_state.driver is None:
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Se estiver na nuvem (Streamlit Cloud), precisamos de argumentos específicos
            if headless:
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
            
            # Tentar usar o webdriver_manager primeiro
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except Exception as e1:
                # Fallback para Streamlit Cloud (usando o chromium instalado via packages.txt)
                try:
                    options.binary_location = "/usr/bin/chromium"
                    driver = webdriver.Chrome(options=options)
                except Exception as e2:
                    # Fallback local normal
                    try:
                        driver = webdriver.Chrome(options=options)
                    except Exception as e3:
                        raise Exception(f"Erro ao iniciar Chrome: {str(e1)} | {str(e2)} | {str(e3)}")
            
            st.session_state.driver = driver
            return driver
        except Exception as e:
            st.error(f"Erro ao iniciar o navegador: {e}")
            st.info("💡 **Dica:** Certifique-se de que o Google Chrome está instalado no seu computador.")
            return None
    return st.session_state.driver

def close_browser():
    """Fecha o navegador e limpa a sessão"""
    if st.session_state.driver:
        try:
            st.session_state.driver.quit()
        except:
            pass
        st.session_state.driver = None

# Função para enviar mensagens
def send_messages_selenium(df, delay):
    """Envia mensagens via WhatsApp Web usando Selenium"""
    driver = st.session_state.driver
    
    if driver is None:
        st.error("O navegador não foi iniciado. Clique em '1. Abrir WhatsApp Web' primeiro.")
        return 0, 0
    
    # Verificar se o login foi feito (esperar aparecer a barra lateral do WhatsApp)
    with st.spinner("⏳ Verificando login no WhatsApp Web..."):
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//div[@id="pane-side"]'))
            )
        except:
            st.warning("⚠️ Não detectamos o WhatsApp logado. Se você já escaneou o QR Code, pode ignorar esta mensagem e o robô tentará enviar assim mesmo.")
        
    total = len(df)
    success_count = 0
    error_count = 0
    
    # Containers para feedback
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_container = st.expander("📋 Log de Envios", expanded=True)
    
    for index, row in df.iterrows():
        try:
            nome = row['Nome']
            telefone = format_phone(row['Telefone']) # Garante formato +55...
            mensagem = row['texto']
            
            # Remover o + para o link do WhatsApp (ele aceita apenas números)
            phone_no = telefone.replace('+', '')
            
            status_text.markdown(f"**Enviando para:** {nome} ({telefone})")
            
            # Codificar mensagem para URL
            msg_encoded = urllib.parse.quote(mensagem)
            
            # Navegar para o chat específico
            link = f"https://web.whatsapp.com/send?phone={phone_no}&text={msg_encoded}"
            driver.get(link)
            
            # Esperar até que a caixa de texto ou o botão de envio esteja carregado
            try:
                # Esperar o botão de enviar aparecer e ser clicável
                send_button = WebDriverWait(driver, 25).until(
                    EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
                )
                time.sleep(1) 
                send_button.click()
                success_sent = True
            except:
                # Fallback: Tentar pressionar ENTER na caixa de texto
                try:
                    chat_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                    chat_box.send_keys(Keys.ENTER)
                    success_sent = True
                except:
                    success_sent = False

            if success_sent:
                # Esperar um pouco para garantir o envio
                time.sleep(3) 
                success_count += 1
                with log_container:
                    st.success(f"✅ {nome} - Mensagem enviada!")
            else:
                # Se falhar ambos, verificar se o número é inválido
                try:
                    invalid_popup = driver.find_element(By.XPATH, '//div[contains(text(), "inválido")]')
                    with log_container:
                        st.warning(f"⚠️ {nome} - Número inválido ou não tem WhatsApp.")
                    error_count += 1
                except:
                    raise Exception("Não foi possível encontrar o botão de enviar nem a caixa de texto.")

            # Aguardar antes do próximo envio
            if index < total - 1:
                status_text.markdown(f"⏳ Aguardando {delay} segundos...")
                time.sleep(delay)
                
        except Exception as e:
            error_count += 1
            with log_container:
                st.error(f"❌ {nome} - Erro: {str(e)}")
        
        progress = (index + 1) / total
        progress_bar.progress(progress)
        
    status_text.empty()
    progress_bar.empty()
    
    return success_count, error_count

# Configuração da página
st.set_page_config(
    page_title="WhatsApp Massa",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para visual moderno
st.markdown("""
<style>
    /* Importar fonte moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Estilo do header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-weight: 700;
        font-size: 2.5rem;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    
    /* Cards de estatísticas */
    .stat-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        transition: transform 0.3s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    
    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: #667eea;
        margin: 0;
    }
    
    .stat-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.5rem;
    }
    
    /* Botões customizados */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Tabela customizada */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Alertas */
    .stAlert {
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #f5f7fa 0%, #c3cfe2 100%);
    }
</style>
""", unsafe_allow_html=True)

# Header principal
st.markdown("""
<div class="main-header">
    <h1>📱 WhatsApp Massa</h1>
    <p>Envie mensagens personalizadas para múltiplos contatos de forma automática</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configurações")
    
    # Upload de arquivo
    uploaded_file = st.file_uploader(
        "📂 Carregar arquivo de contatos (Excel)",
        type=['xlsx', 'xls'],
        help="Faça upload de um arquivo Excel com as colunas: Nome, Telefone, texto"
    )
    
    st.markdown("---")
    st.markdown("### 📊 Google Sheets")
    gsheets_url = st.text_input(
        "Link da Planilha Google",
        placeholder="https://docs.google.com/spreadsheets/d/...",
        help="Cole o link da sua planilha Google (ela deve estar compartilhada como 'Qualquer pessoa com o link')"
    )
    
    use_gsheets = st.toggle("Usar Dados do Google Sheets", value=False)
    
    st.markdown("---")
    
    # Configurações de envio
    st.markdown("### 🕐 Configurações de Envio")
    delay_between_messages = st.slider(
        "Intervalo entre mensagens (segundos)",
        min_value=10,
        max_value=60,
        value=20,
        help="Tempo de espera entre cada envio para evitar bloqueios"
    )
    
    st.markdown("---")
    
    # Informações
    st.markdown("### ℹ️ Informações")
    st.info("""
    **Como usar:**
    1. Carregue o arquivo Excel
    2. Revise os contatos
    3. Clique em 'Enviar Mensagens'
    4. Aguarde o WhatsApp Web abrir
    5. Não feche o navegador durante o envio
    """)
    
    st.warning("""
    ⚠️ **Atenção:**
    - Mantenha o WhatsApp Web aberto
    - Não use o mouse durante o envio
    - Intervalos curtos podem causar bloqueio
    """)

# Função para carregar dados
@st.cache_data
def load_data(file_path):
    """Carrega dados do arquivo Excel"""
    try:
        # Tentar ler forçando Telefone como string
        df = pd.read_excel(file_path, dtype={'Telefone': str})
        return df
    except ValueError:
        # Se falhar (ex: coluna não existe), ler normal
        try:
            df = pd.read_excel(file_path)
            return df
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {str(e)}")
            return None
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {str(e)}")
        return None

# Função para validar dados
def validate_data(df):
    """Valida se o DataFrame tem as colunas necessárias"""
    required_columns = ['Nome', 'Telefone', 'texto']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"❌ Colunas faltando: {', '.join(missing_columns)}")
        return False
    return True

# Função para formatar telefone
def format_phone(phone):
    """Formata o número de telefone para o padrão internacional"""
    # Converter para string e remover caracteres não numéricos
    phone_str = str(phone).split('.')[0]  # Remove decimal .0 se existir
    phone_str = ''.join(filter(str.isdigit, phone_str))
    
    # Adicionar código do país se necessário
    if not phone_str.startswith('55'):
        phone_str = '55' + phone_str
        
    return '+' + phone_str

# Função para enviar mensagens
def send_messages(df, delay):
    """Envia mensagens via WhatsApp"""
    total = len(df)
    success_count = 0
    error_count = 0
    
    # Containers para feedback
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Log de envios
    log_container = st.expander("📋 Log de Envios", expanded=True)
    
    for index, row in df.iterrows():
        try:
            nome = row['Nome']
            telefone_bruto = row['Telefone']
            telefone = format_phone(telefone_bruto)
            mensagem = row['texto']
            
            # Validação básica de comprimento (DDI + DDD + 9 + 8 dígitos = 13 dígitos, ou sem o 9 extra = 12)
            if len(telefone) < 13:
                raise ValueError(f"Número de telefone inválido (muito curto): {telefone}")

            # Atualizar status
            status_text.markdown(f"**Enviando para:** {nome} ({telefone})")
            
            # Enviar mensagem instantaneamente
            # wait_time: tempo para carregar o WhatsApp Web (Aumentado para 20s)
            # tab_close: True para fechar a aba
            # close_time: tempo extra após carregar para garantir envio (Aumentado para 10s)
            kit.sendwhatmsg_instantly(
                phone_no=telefone, 
                message=mensagem, 
                wait_time=25, 
                tab_close=True, 
                close_time=10
            )
            
            success_count += 1
            
            with log_container:
                st.success(f"✅ {nome} ({telefone}) - Mensagem enviada!")
            
            # Aguardar antes do próximo envio
            if index < total - 1:  # Não esperar no último envio
                status_text.markdown(f"⏳ Aguardando {delay} segundos antes do próximo envio...")
                time.sleep(delay)
            
        except Exception as e:
            error_count += 1
            with log_container:
                st.error(f"❌ {nome} - Erro: {str(e)}")
        
        # Atualizar barra de progresso
        progress = (index + 1) / total
        progress_bar.progress(progress)
    
    # Finalizar
    status_text.empty()
    progress_bar.empty()
    
    return success_count, error_count

# Determinar fonte de dados
if use_gsheets and gsheets_url:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=gsheets_url)
        # Garantir que as colunas existem
        if not validate_data(df):
            df = None
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        df = None
elif uploaded_file is not None:
    df = load_data(uploaded_file)
else:
    # Tentar carregar arquivo padrão
    default_file = "contatos.xlsx"
    if os.path.exists(default_file):
        df = load_data(default_file)
    else:
        df = None

# Interface principal
if df is not None:
    if validate_data(df):
        # Estatísticas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{len(df)}</p>
                <p class="stat-label">Total de Contatos</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            unique_messages = df['texto'].nunique()
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{unique_messages}</p>
                <p class="stat-label">Mensagens Únicas</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            estimated_time = len(df) * delay_between_messages / 60
            st.markdown(f"""
            <div class="stat-card">
                <p class="stat-number">{estimated_time:.1f}</p>
                <p class="stat-label">Tempo Estimado (min)</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Edição dos dados
        st.markdown("### ✏️ Editar e Visualizar Contatos")
        st.info("💡 **Dica:** Você pode adicionar, remover ou editar contatos diretamente na tabela abaixo. Clique em **Limpar e Corrigir** para ajustar automaticamente os números.")
        
        # Inicializar estado da tabela se não existir ou se for um novo arquivo
        # Identificador simples para o arquivo (nome e tamanho)
        file_id = f"{uploaded_file.name if uploaded_file else 'default'}_{df.shape}"
        
        if "current_file_id" not in st.session_state or st.session_state.current_file_id != file_id:
            st.session_state.current_file_id = file_id
            st.session_state.editor_data = df[['Nome', 'Telefone', 'texto']].copy()
        
        # Botões de Ação para a Tabela
        col_actions1, col_actions2, col_dummy = st.columns([1, 1, 2])
        
        with col_actions1:
            if st.button("🧹 Limpar e Corrigir Números", help="Remove formatação errada e padroniza para +55..."):
                # Aplicar formatação em todos os números da tabela atual
                try:
                    st.session_state.editor_data['Telefone'] = st.session_state.editor_data['Telefone'].apply(format_phone)
                    st.toast("✅ Números corrigidos com sucesso!", icon="✨")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao corrigir: {e}")

        with col_actions2:
            if st.button("🔄 Recarregar do Arquivo Origem", help="Descarta edições e volta para o arquivo original"):
                st.session_state.editor_data = df[['Nome', 'Telefone', 'texto']].copy()
                st.rerun()

        # Tabela editável (lendo e escrevendo no session_state)
        edited_df = st.data_editor(
            st.session_state.editor_data,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Telefone": st.column_config.TextColumn(
                    "Telefone",
                    help="Digite o número (ex: 5518999998888)",
                    validate="^[\d\+\-\(\)\s]+$"
                ),
                "texto": st.column_config.TextColumn(
                    "Mensagem",
                    width="large"
                )
            },
            key="editor_contatos_ui"  # Key diferente para não conflitar
        )
        
        # Sincronizar edições manuais de volta para o session_state para persistir
        st.session_state.editor_data = edited_df

        # Preview da formatação (baseado no que está na tela)
        with st.expander("👀 Ver Preview dos Números Formatados (Como será enviado)", expanded=False):
            try:
                preview_df = edited_df.copy()
                preview_df['Telefone Formatado'] = preview_df['Telefone'].apply(format_phone)
                st.dataframe(
                    preview_df[['Nome', 'Telefone', 'Telefone Formatado']],
                    use_container_width=True
                )
            except Exception:
                st.warning("Preencha os dados corretamente para ver o preview.")

        st.markdown("---")
        
        # Nova Seção de Controle do Navegador e Envio
        st.markdown("---")
        st.markdown("### 🚀 Controle de Envio")
        st.info("ℹ️ **Passo a Passo para Envio em Segundo Plano:**\n1. Clique em **'Abrir WhatsApp Web'**.\n2. Escaneie o QR Code na janela que abrir.\n3. Volte aqui e clique em **'Enviar Mensagens'**.\n4. **Pode minimizar a janela do Chrome** e usar o PC normalmente!")

        col_conn1, col_conn2 = st.columns(2)
        
        with col_conn1:
            # Detectar se está rodando local ou remoto
            is_local = os.name == 'nt' # Windows é local
            button_label = "🔓 1. Abrir WhatsApp Web" if is_local else "🔓 1. Iniciar Sessão (Nuvem)"
            
            if st.button(button_label, help="Abre o navegador para você escanear o QR Code", use_container_width=True):
                driver = init_browser(headless=not is_local)
                if driver:
                    driver.get("https://web.whatsapp.com")
                    st.success("Navegador iniciado!")
        
        with col_conn2:
            if st.button("🔒 Fechar Conexão", help="Fecha o navegador e encerra a sessão", use_container_width=True):
                close_browser()
                st.info("Conexão fechada.")
                st.rerun()

        # Mostrar QR Code se for remoto ou se o usuário quiser ver
        if st.session_state.driver:
            with st.expander("📸 Ver Tela do WhatsApp (QR Code)", expanded=not is_local):
                if st.button("🔄 Atualizar Captura de Tela"):
                    pass # Só para forçar rerun do componente
                
                try:
                    screenshot = st.session_state.driver.get_screenshot_as_png()
                    st.image(screenshot, caption="Captura do WhatsApp Web", use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao capturar tela: {e}")

        # Verificar status da conexão
        if st.session_state.driver:
            st.success("✅ **Status:** Navegador Conectado e Pronto!")
            
            # Botão de envio (SÓ APARECE SE CONECTADO)
            if st.button("📨 2. Iniciar Envio em Massa", type="primary", use_container_width=True):
                if len(edited_df) == 0:
                    st.error("❌ A lista de contatos está vazia!")
                else:
                    st.markdown("### 📤 Enviando...")
                    with st.spinner("O robô está trabalhando... Pode minimizar a janela do Chrome."):
                        success, errors = send_messages_selenium(edited_df, delay_between_messages)
                    
                    st.success(f"✅ Finalizado! {success} enviados, {errors} erros.")
                    st.balloons()
        else:
            st.warning("⚠️ **Status:** Navegador Desconectado. Clique no botão 1 para iniciar.")

else:
    # Tela inicial quando não há dados
    st.markdown("### 👋 Bem-vindo!")
    st.info("""
    📂 **Nenhum arquivo carregado**
    
    Para começar:
    1. Carregue um arquivo Excel na barra lateral, ou
    2. Coloque um arquivo chamado `contatos.xlsx` na mesma pasta do aplicativo
    
    **Formato esperado do arquivo:**
    - Coluna **Nome**: Nome do contato
    - Coluna **Telefone**: Número com DDD (ex: 5518988067827)
    - Coluna **texto**: Mensagem a ser enviada
    """)
    
    # Exemplo de estrutura
    st.markdown("### 📋 Exemplo de Estrutura")
    example_df = pd.DataFrame({
        'Nome': ['João Silva', 'Maria Santos'],
        'Telefone': ['5511999998888', '5511988887777'],
        'texto': ['Olá João, tudo bem?', 'Oi Maria, como vai?']
    })
    st.dataframe(example_df, use_container_width=True)
