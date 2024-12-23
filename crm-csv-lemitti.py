import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from bs4 import BeautifulSoup
import time
import pandas as pd
import logging
import traceback
import requests
from typing import List, Dict
import json
from tallos import TallosAPI
import datetime


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da página Streamlit
st.set_page_config(page_title="Busca de Médicos", layout="wide")
st.title("Sistema de Busca de Médicos")

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument("--disable-blink-features=AutomationControlled")

# Automatic ChromeDriver configuration
service = Service(ChromeDriverManager().install())


def wait_and_find_element(driver, by, value, timeout=30):
    """
    Helper function to wait for and find elements with proper error handling
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        logger.error(f"Timeout waiting for element: {value}")
        return None
    except Exception as e:
        logger.error(f"Error finding element {value}: {str(e)}")
        return None

def generate_contact_search(name, crm, uf):
    """
    Opens a new tab to search for additional contact information
    """
    try:
        logger.info(f"Iniciando busca de contato - Nome: {name}, CRM: {crm}")
        
        driver = webdriver.Chrome(service=service, options=options)
        # Open website in new tab
        driver.get("https://crmma.org.br/busca-medicos")
        
        # Wait for form and fill fields
        form = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "buscaForm"))
        )
        
        # Fill CRM field
        crm_field = driver.find_element(By.NAME, "crm")
        crm_field.send_keys(crm)
        
        # Select UF
        uf_select = Select(driver.find_element(By.NAME, "uf"))
        uf_select.select_by_visible_text(uf)
        
        time.sleep(5)
        
        # Click search
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.w-100.btn-buscar.btnPesquisar"))
        )
        driver.execute_script("arguments[0].click();", search_button)
        
        # Wait for results
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".loading"))
        )
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading"))
        )
        
        # Keep browser open for user interaction
        # The browser will stay open until manually closed
        return driver
        
    except Exception as e:
        logger.error(f"Erro ao gerar contato: {str(e)}")
        driver.quit()
        return None

def search_doctor_in_lemitti(nome_medico):
    """
    Search for additional contact information using Lemitti API
    Returns dict with new contact information or None if not found
    """
    try:
        # API endpoints
        pessoa_endpoint = "https://api.lemit.com.br/api/v1/consulta/pessoa/"
        empresa_endpoint = "https://api.lemit.com.br/api/v1/consulta/empresa/"
        
        # Headers with Bearer token
        headers = {
            'Authorization': 'Bearer uSwyMC7m4FPTMvgTJkjqBQ35Z4Mx7LfX9vmceL7G'
        }
        
        # Debug request details
        logger.info(f"Fazendo requisição para pessoa endpoint com nome: {nome_medico}")
        logger.info(f"Headers: {headers}")
        
        # Try pessoa endpoint first
        response = requests.post(
            pessoa_endpoint,
            headers=headers,
            json={'nome': nome_medico}
        )
        
        # Log response details
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        logger.info(f"Response content: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Parsed JSON data: {json.dumps(data, indent=2)}")
            
            if data.get('telefones') or data.get('enderecos'):
                return {
                    "Telefone": data.get('telefones', ['Não disponível'])[0],
                    "Endereço": data.get('enderecos', ['Não disponível'])[0]
                }
            else:
                logger.info("Nenhum telefone ou endereço encontrado nos dados")
        else:
            logger.error(f"Erro na requisição: {response.status_code}")
            logger.error(f"Erro detalhado: {response.text}")
        
        # If no results, try empresa endpoint with debug logging
        logger.info(f"Tentando empresa endpoint para: {nome_medico}")
        response = requests.post(
            empresa_endpoint,
            headers=headers,
            json={'nome': nome_medico}
        )
        
        # Log empresa endpoint response
        logger.info(f"Empresa status code: {response.status_code}")
        logger.info(f"Empresa response content: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Empresa parsed data: {json.dumps(data, indent=2)}")
            
            if data.get('telefones') or data.get('enderecos'):
                return {
                    "Telefone": data.get('telefones', ['Não disponível'])[0],
                    "Endereço": data.get('enderecos', ['Não disponível'])[0]
                }
            else:
                logger.info("Nenhum telefone ou endereço encontrado nos dados da empresa")
        else:
            logger.error(f"Erro na requisição empresa: {response.status_code}")
            logger.error(f"Erro detalhado empresa: {response.text}")
        
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro de conexão: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON: {str(e)}")
        logger.error(f"Conteúdo que causou erro: {response.text}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao consultar API Lemitti: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def format_results_to_csv(results, search_uf):
    """
    Format search results into the required CSV format:
    NOME;CIDADE;UF;DT_NASCIMENTO
    """
    # Results are already in the correct format, just return them directly
    return results

def start_rd_chat_conversation(doctor_data):
    """
    Starts a chat conversation in RD Station for a found doctor
    """
    try:
        # RD Station API endpoint
        url = "https://api.rd.services/platform/events"
        
        # Prepare the payload
        payload = {
            "event_type": "CHAT_STARTED",
            "event_family": "CDP",
            "payload": {
                "chat_subject": "Confirmação de Dados Médicos",
                "cf_chat_status": "Online",
                "email": doctor_data.get('email', ''),  # If email is available
                "name": doctor_data.get('Nome', ''),
                "city": doctor_data.get('Cidade', ''),
                "uf": doctor_data.get('UF', '')
            }
        }
        
        # Headers with authentication
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": "Bearer YOUR_RD_STATION_TOKEN"  # Replace with your actual token
        }
        
        # Make the request
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            logger.info(f"Chat iniciado com sucesso para médico: {doctor_data.get('Nome')}")
            return True
        else:
            logger.error(f"Erro ao iniciar chat: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Erro ao iniciar chat RD Station: {str(e)}")
        return False

def search_doctors(nome, uf, situacao="ATIVO", especialidade="", area_atuacao=""):
    """
    Perform doctor search and generate CSV output with pagination support
    """
    driver = webdriver.Chrome(service=service, options=options)
    results = []
    
    try:
        logger.info(f"Iniciando busca - UF: {uf}, Nome: {nome}")
        
        # Open website
        driver.get("https://crmma.org.br/busca-medicos")
        
        # Wait for form and fill fields
        form = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "buscaForm"))
        )
        
        if nome:
            nome_field = driver.find_element(By.NAME, "nome")
            nome_field.send_keys(nome)
            print(f"Nome preenchido: {nome}")
        
        # Select UF
        uf_select = Select(driver.find_element(By.NAME, "uf"))
        uf_select.select_by_visible_text(uf)
        print(f"UF selecionada: {uf}")
        
        time.sleep(5)
        
        # Handle specialty and area selections
        if especialidade:
            specialty_select = Select(driver.find_element(By.NAME, "especialidade"))
            try:
                specialty_select.select_by_visible_text(especialidade)
            except NoSuchElementException:
                logger.warning(f"Especialidade não encontrada: {especialidade}")
        
        if area_atuacao:
            area_select = Select(driver.find_element(By.NAME, "areaAtuacao"))
            try:
                area_select.select_by_visible_text(area_atuacao)
            except NoSuchElementException:
                logger.warning(f"Área de Atuação não encontrada: {area_atuacao}")
        
        if situacao:
            situation_select = Select(driver.find_element(By.NAME, "tipoSituacao"))
            situation_value = "A" if situacao == "ATIVO" else "I"
            situation_select.select_by_value(situation_value)
        
        # Click search button
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.w-100.btn-buscar.btnPesquisar"))
        )
        driver.execute_script("arguments[0].click();", search_button)
        
        # Wait for initial loading
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".loading"))
        )
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading"))
        )
        
        time.sleep(20)
        
        # Get total number of records
        total_records_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#resultados .text-center"))
        )
        total_records = int(total_records_element.text.split()[0])
        total_pages = (total_records + 9) // 10  # 10 results per page
        
        logger.info(f"Total de registros: {total_records}, Páginas: {total_pages}")
        
        # Process each page
        for page in range(1, total_pages + 1):
            logger.info(f"Processando página {page} de {total_pages}")
            
            if page > 1:
                try:
                    next_page = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, f".paginationjs-page[data-num='{page}']"))
                    )
                    driver.execute_script("arguments[0].click();", next_page)
                    
                    # Wait for loading
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".loading"))
                    )
                    WebDriverWait(driver, 30).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading"))
                    )
                    time.sleep(3)
                except Exception as e:
                    logger.error(f"Erro na navegação da página {page}: {str(e)}")
                    continue
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            doctor_items = soup.find_all('div', class_='resultado-item')
            
            for item in doctor_items:
                try:
                    name = item.find('h4').text.strip()
                    crm = item.find('div', class_='col-md-4').text.strip().split(':')[1].strip()
                    
                    address_div = item.find('div', class_='endereco')
                    full_address = address_div.text.strip().split(':')[1].strip() if address_div else "Não disponível"
                    
                    # Parse address components
                    address_parts = full_address.split(' - ')
                    street_address = address_parts[0].strip() if len(address_parts) > 0 else ""
                    city_uf = address_parts[-1].strip() if len(address_parts) > 1 else ""
                    
                    # Extract city and UF, always using search UF
                    if '/' in city_uf:
                        city = city_uf.split('/')[0].strip()
                    else:
                        city = city_uf.strip() if city_uf else "N/A"
                    
                    state = uf  # Always use the UF from search parameter
                    doctor_data = {
                        "Nome": name,
                        "Cidade": city,
                        "UF": state,
                        "DT_NASCIMENTO": ""
                    }
                    
                    # Start chat conversation if doctor is found
                    if start_rd_chat_conversation(doctor_data):
                        st.success(f"Chat iniciado com {name}")
                    
                    results.append(doctor_data)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar médico: {str(e)}")
                    continue
            
            time.sleep(2)  # Delay between pages
        
        if results:
            # Create CSV string
            csv_content = "NOME;CIDADE;UF;DT_NASCIMENTO\n"
            for row in results:
                csv_content += f"{row['Nome']};{row['Cidade']};{row['UF']};{row['DT_NASCIMENTO']}\n"
            
            # Add CSV download button
            st.download_button(
                label="Baixar CSV",
                data=csv_content,
                file_name="medicos.csv",
                mime="text/csv"
            )
            
            return results
            
    except Exception as e:
        logger.error(f"Erro durante a busca: {str(e)}")
        st.error("Ocorreu um erro durante a busca. Por favor, tente novamente.")
    finally:
        driver.quit()
    
    return []

def load_enriched_csv(uploaded_file) -> pd.DataFrame:
    """
    Load and validate the enriched CSV file
    """
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
        required_columns = [
            'NOME', 'CPF/CNPJ', 'DDD', 'FONE', 'EMAIL-1', 
            'CIDADE', 'UF', 'CEP', 'FULL-LOGRADOURO'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Coluna obrigatória ausente: {col}")
                return None
                
        return df
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {str(e)}")
        return None

def create_tallos_contact(contact_data: dict, selected_integration_id: str) -> dict:
    """
    Format contact data for Tallos API
    """
    try:
        # Clean and format phone number
        phone = contact_data.get('FONE', '')
        if contact_data.get('DDD'):
            phone = f"{contact_data['DDD']}{phone}".strip()
        
        # Remove any non-numeric characters and format phone number
        phone = ''.join(filter(str.isdigit, phone))
        if len(phone) >= 11:  # Ensure we have enough digits for full phone number
            formatted_phone = f"+55 {phone[:2]} {phone[2:7]}-{phone[7:11]}"
        else:
            formatted_phone = phone  # Keep original if not enough digits
        # Format the contact payload
        payload = {
            "full_name": contact_data.get('NOME', ''),
            "cel_phone": formatted_phone,
            # "email": contact_data.get('EMAIL', ''),
            # "address": contact_data.get('ENDERECO', ''),
            # "city": contact_data.get('CIDADE', ''),
            # "state": contact_data.get('UF', ''),
            "integration": selected_integration_id["key"],  # Add integration ID
            # "channel": "whatsapp",
            # "channel_metadata": {
            #     "integration": selected_integration_id  # Add integration ID here as well
            # }
        }
        
        return payload
        
    except Exception as e:
        st.error(f"Error formatting contact data: {str(e)}")
        return None

def get_formatted_integrations(tallos_api):
    """Get and format WhatsApp integrations for selection"""
    try:
        integrations = tallos_api.get_whatsapp_integrations()
        
        if not integrations:
            return []
            
        formatted = []
        for integration in integrations:
            if isinstance(integration, dict):
                formatted_integration = {
                    'key': integration.get('key'),
                    'label': integration.get('label', 'Unnamed')
                }
                formatted.append(formatted_integration)
                
        return formatted
        
    except Exception as e:
        st.error(f"Error getting integrations: {str(e)}")
        return []

def send_tallos_message(tallos_api, contact_data: dict, message_template: str, selected_operator_id: str, selected_integration: dict) -> bool:
    """Send message via Tallos API"""
    try:
        # Create contact payload
        contact_payload = create_tallos_contact(contact_data, selected_integration)
        if not contact_payload:
            st.error(f"Erro ao formatar dados do contato: {contact_data.get('NOME', 'Unknown')}")
            return False
            
        contact_response = tallos_api.create_contact(contact_payload)
        
        if not contact_response or '_id' not in contact_response:
            st.error(f"Erro ao criar contato: {contact_data.get('NOME', 'Unknown')}")
            return False
            
        # Format message with contact data
        formatted_message = message_template
        for key, value in contact_data.items():
            placeholder = f"{{{key}}}"
            if placeholder in formatted_message:
                formatted_message = formatted_message.replace(placeholder, str(value))
        
        logger.info(f"Sending message to {contact_response['_id']} with template {message_template}")
        # Send message
        message_response = tallos_api.send_message(
            customer_id=contact_response['_id'],
            message=formatted_message,
            operator_id=selected_operator_id
        )
        
        logger.info(f"Message response: {message_response}")
        
        if message_response and message_response.get('status') == 'success':
            return True
        else:
            st.error(f"Erro ao enviar mensagem para: {contact_data.get('NOME', 'Unknown')}")
            return False
            
    except Exception as e:
        st.error(f"Erro no processo de envio: {str(e)}")
        return False

def flatten_templates(templates_response: dict) -> List[dict]:
    """
    Flatten and format the templates from the API response into a clean list
    Returns a list of dicts with id and shortened content
    """
    flattened = []
    try:
        if not isinstance(templates_response, dict):
            st.error("Invalid templates response format")
            return flattened
            
        templates = templates_response.get('templates', {})
        
        # Handle direct list of templates
        template_list = templates.get('templates', []) if isinstance(templates, dict) else templates
        
        if isinstance(template_list, list):
            for template in template_list:
                if isinstance(template, dict):
                    # Get first 50 characters of content for preview
                    content = template.get('content', '')
                    short_content = content[:50] + '...' if len(content) > 50 else content
                    
                    flattened.append({
                        'id': template.get('id'),
                        'content': short_content,
                        'full_content': content
                    })
                    
        return flattened
    except Exception as e:
        st.error(f"Error processing templates: {str(e)}")
        return []

def process_templates(templates: List[Dict]) -> List[Dict]:
    """
    Process and validate template data
    """
    processed = []
    for template in templates:
        if isinstance(template, dict):
            processed_template = {
                'id': template.get('id', ''),
                'content': template.get('content', ''),
                'content_media': template.get('content_media', None)
            }
            processed.append(processed_template)
    return processed

# Cache para o estado da sessão
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

# Interface Streamlit
st.sidebar.header("Filtros de Busca")

# Campos de busca com validação
nome_medico = st.sidebar.text_input("Nome do Médico", max_chars=100)
estado = st.sidebar.selectbox(
    "Estado",
    ["", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", 
     "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", 
     "SP", "SE", "TO"]
)
situacao = st.sidebar.selectbox("Situação", ["ATIVO", "INATIVO"])
especialidade = st.sidebar.selectbox(
    "Especialidade do Médico",
    ["", "ACUPUNTURA", "ADMINISTRAÇÃO EM SAÚDE", "ADMINISTRAÇÃO HOSPITALAR", 
     "ALERGIA E IMUNOLOGIA", "ALERGIA E IMUNOPATOLOGIA", "ANATOMIA PATOLÓGICA",
     "ANESTESIOLOGIA", "ANGIOLOGIA", "ANGIOLOGIA E CIRURGIA VASCULAR",
     "BRONCOESOFAGOLOGIA", "CANCEROLOGIA", "CANCEROLOGIA/CANCEROLOGIA CIRÚRGICA",
     "CANCEROLOGIA/CANCEROLOGIA PEDIÁTRICA", "CARDIOLOGIA", "CIRURGIA CARDIOVASCULAR",
     "CIRURGIA DA MÃO", "CIRURGIA DE CABEÇA E PESCOÇO", "CIRURGIA DIGESTIVA",
     "CIRURGIA DO APARELHO DIGESTIVO", "CIRURGIA DO TRAUMA", "CIRURGIA GASTROENTEROLÓGICA",
     "CIRURGIA GERAL", "CIRURGIA ONCOLÓGICA", "CIRURGIA PEDIÁTRICA", "CIRURGIA PLÁSTICA",
     "CIRURGIA TORÁCICA", "CIRURGIA TORÁXICA", "CIRURGIA VASCULAR", 
     "CIRURGIA VASCULAR PERIFÉRICA", "CITOPATOLOGIA", "CLÍNICA MÉDICA",
     "COLOPROCTOLOGIA", "DENSITOMETRIA ÓSSEA", "DERMATOLOGIA", 
     "DIAGNÓSTICO POR IMAGEM", "DOENÇAS INFECCIOSAS E PARASITÁRIAS",
     "ELETROENCEFALOGRAFIA", "ENDOCRINOLOGIA", "ENDOCRINOLOGIA E METABOLOGIA",
     "ENDOSCOPIA", "ENDOSCOPIA DIGESTIVA", "ENDOSCOPIA PERORAL",
     "ENDOSCOPIA PERORAL VIAS AÉREAS", "FISIATRIA", "FONIATRIA", "GASTROENTEROLOGIA",
     "GENÉTICA CLÍNICA", "GENÉTICA LABORATORIAL", "GENÉTICA MÉDICA", "GERIATRIA",
     "GERIATRIA E GERONTOLOGIA", "GINECOLOGIA", "GINECOLOGIA E OBSTETRÍCIA",
     "HANSENOLOGIA", "HEMATOLOGIA", "HEMATOLOGIA E HEMOTERAPIA", "HEMOTERAPIA",
     "HEPATOLOGIA", "HOMEOPATIA", "IMUNOLOGIA CLÍNICA", "INFECTOLOGIA",
     "INFORMÁTICA MÉDICA", "MASTOLOGIA", "MEDICINA DE EMERGÊNCIA",
     "MEDICINA DE FAMÍLIA E COMUNIDADE", "MEDICINA DO ADOLESCENTE",
     "MEDICINA DO ESPORTE", "MEDICINA DO TRABALHO", "MEDICINA DO TRÁFEGO",
     "MEDICINA ESPORTIVA", "MEDICINA FÍSICA E REABILITAÇÃO",
     "MEDICINA GERAL COMUNITÁRIA", "MEDICINA INTENSIVA",
     "MEDICINA INTERNA OU CLÍNICA MÉDICA", "MEDICINA LEGAL",
     "MEDICINA LEGAL E PERÍCIA MÉDICA", "MEDICINA NUCLEAR",
     "MEDICINA PREVENTIVA E SOCIAL", "MEDICINA SANITÁRIA", "NEFROLOGIA",
     "NEUROCIRURGIA", "NEUROFISIOLOGIA CLÍNICA", "NEUROLOGIA",
     "NEUROLOGIA PEDIÁTRICA", "NEUROPEDIATRIA", "NUTRIÇÃO PARENTERAL E ENTERAL",
     "NUTROLOGIA", "OBSTETRIA", "OFTALMOLOGIA", "ONCOLOGIA", "ONCOLOGIA CLÍNICA",
     "ORTOPEDIA E TRAUMATOLOGIA", "OTORRINOLARINGOLOGIA", "PATOLOGIA",
     "PATOLOGIA CLÍNICA", "PATOLOGIA CLÍNICA/MEDICINA LABORATORIAL", "PEDIATRIA",
     "PNEUMOLOGIA", "PNEUMOLOGIA E TISIOLOGIA", "PROCTOLOGIA", "PSIQUIATRIA",
     "PSIQUIATRIA INFANTIL", "RADIODIAGNÓSTICO", "RADIOLOGIA",
     "RADIOLOGIA E DIAGNÓSTICO POR IMAGEM", "RADIOTERAPIA", "REUMATOLOGIA",
     "SEXOLOGIA", "TERAPIA INTENSIVA", "TERAPIA INTENSIVA PEDIÁTRICA",
     "TISIOLOGIA", "TOCO-GINECOLOGIA", "ULTRASSONOGRAFIA",
     "ULTRASSONOGRAFIA EM GINECOLOGIA E OBSTETRÍCIA", "ULTRASSONOGRAFIA GERAL",
     "UROLOGIA"]
)
area_atuacao = st.sidebar.selectbox(
    "Área de Atuação",
    ["", "Administração Hospitalar", "Administração em Saúde", "Adolescência", 
     "Alergia e Imunologia Pediátrica", "Andrologia", "Angiorradiologia e Cirurgia Endovascular",
     "Atendimento ao Queimado", "Auditoria Médica", "Biologia Molecular", "Bioquímica",
     "Cardiologia Pediátrica", "Cirurgia Bariátrica", "Cirurgia Crânio-Maxilo-Facial",
     "Cirurgia Dermatológica", "Cirurgia Oncológica", "Cirurgia Videolaparoscópica",
     "Cirurgia da Coluna", "Cirurgia da Mão", "Cirurgia de Cabeça e Pescoço",
     "Cirurgia do Joelho", "Cirurgia do Ombro", "Cirurgia do Pé", "Cirurgia do Quadril",
     "Cirurgia do Trauma", "Citopatologia", "Colonoscopia", "Cosmiatria",
     "Densitometria Óssea", "Dor", "Ecocardiografia", "Ecocardiografia Pediátrica",
     "Ecografia Vascular com DOPPLER", "Eletrencefalografia", "Eletrofisiologia Clínica Invasiva",
     "Eletroneuromiografia", "Emergência Pediátrica", "Endocrinologia Pediátrica",
     "Endoscopia Digestiva", "Endoscopia Ginecológica", "Endoscopia Respiratória",
     "Epidemiologia", "Ergometria", "Estimulação Cardíaca Eletrônica Implantável",
     "Foniatria", "Gastroenterologia Pediátrica", "Hansenologia",
     "Hematologia e Hemoterapia Pediátrica", "Hemodinâmica e Cardiologia Intervencionista",
     "Hemodinâmica/Cardiol. Intervencionista Pediátrica", "Hepatologia", "Histeroscopia",
     "Histopatologia", "Infectologia Hospitalar", "Infectologia Pediátrica", "Laparoscopia",
     "Mamografia", "Medicina Aeroespacial", "Medicina Fetal", "Medicina Intensiva Neonatal",
     "Medicina Intensiva Pediátrica", "Medicina Paliativa", "Medicina Sanitária",
     "Medicina Tropical", "Medicina de Urgência", "Medicina do Adolescente",
     "Medicina do Sono", "Nefrologia Pediátrica", "Neonatologia", "Neurofisiologia Clínica",
     "Neurologia Pediátrica", "Neurorradiologia", "Neurorradiologia Diagnóstica",
     "Neurorradiologia Terapêutica", "Nutrição Parenteral e Enteral",
     "Nutrição Parenteral e Enteral Pediátrica", "Nutrologia Pediátrica", "Oncogenética",
     "Oncologia Clínica", "Oncologia Pediátrica", "Ortopedia Pediátrica",
     "Pediatria Preventiva e Social", "Perícia Médica", "Pneumologia Pediátrica",
     "Polissonografia", "Potenciais Evocados", "Psicogeriatria", "Psicoterapia",
     "Psiquiatria Forense", "Psiquiatria da Infância e Adolescência",
     "Radiologia Intervencionista e Angiorradiologia", "Reprodução Assistida",
     "Reprodução Humana", "Ressonância Magnética", "Reumatologia Pediátrica",
     "Sexologia", "Toxicologia Médica", "Transplante de medula óssea",
     "Tratamento da Dor", "Ultrassonografia", "Ultrassonografia Geral",
     "Ultrassonografia em ginecologia e obstetrícia"]
)

# Botão de busca com feedback visual
if st.sidebar.button("Buscar Médicos"):
    if not estado:
        st.warning("Por favor, selecione um estado para realizar a busca.")
    else:
        try:
            with st.spinner("Realizando busca..."):
                results = search_doctors(
                    nome_medico, 
                    estado, 
                    situacao, 
                    especialidade, 
                    area_atuacao
                )
                
                if results:
                    # Display results count
                    st.success(f"Foram encontrados {len(results)} médicos.")
                    
                    # Display results in table format
                    df = pd.DataFrame(format_results_to_csv(results, estado))
                    st.dataframe(df)
                    
                    # CSV download button is already added in search_doctors function
                else:
                    st.warning("Nenhum resultado encontrado para os critérios informados.")
        except Exception as e:
            logger.error(f"Erro na interface: {str(e)}")
            logger.error(traceback.format_exc())
            st.error("Ocorreu um erro inesperado. Por favor, tente novamente.")

# Informações adicionais e histórico
st.sidebar.markdown("---")
st.sidebar.markdown("""
### Como usar:
1. Preencha os campos desejados
2. Clique em "Buscar Médicos"
3. Aguarde os resultados
4. Use o botão de download para salvar os resultados
""")

# Exibe histórico de buscas
if st.session_state.search_history:
    with st.expander("Histórico de Buscas"):
        for search in st.session_state.search_history[-5:]:  # Mostra últimas 5 buscas
            st.write(f"Data: {search['timestamp']}")
            st.write(f"Parâmetros: {search['params']}")
            st.write(f"Resultados encontrados: {search['count']}")
            st.write("---")

# Add this new section to your Streamlit interface
st.header("Envio de Mensagens via Tallos")

# Initialize Tallos API
tallos_api = TallosAPI(st.secrets["TALLOS_API_TOKEN"])

# Get operators and templates with safer data handling
employees_response = tallos_api.get_employees()
logger.info(f"Employees response: {json.dumps(employees_response, indent=2)}")

# Initialize flattened_templates at the top level
flattened_templates = []

# Get and flatten templates
templates_response = tallos_api.get_templates()
logger.info(f"Templates response: {json.dumps(templates_response, indent=2)}")

# Flatten templates immediately after getting the response
if templates_response:
    try:
        flattened_templates = flatten_templates(templates_response)
    except Exception as e:
        logger.error(f"Error flattening templates: {str(e)}")
        st.error("Error processing templates. Please check the API response format.")

# Safer dictionary comprehension with error handling
operators = {}
if employees_response:
    try:
        # Adjust these keys based on the actual API response structure
        operators = {
            emp.get('id', f'emp_{i}'): emp 
            for i, emp in enumerate(employees_response)
            if isinstance(emp, dict)
        }
    except Exception as e:
        logger.error(f"Error processing employees: {str(e)}")
        st.error("Error loading operators data. Please check the API response format.")

templates = {}
if templates_response:
    try:
        # Adjust these keys based on the actual API response structure
        templates = {
            temp.get('id', f'template_{i}'): temp 
            for i, temp in enumerate(templates_response)
            if isinstance(temp, dict)
        }
    except Exception as e:
        logger.error(f"Error processing templates: {str(e)}")
        st.error("Error loading templates data. Please check the API response format.")

# Display data preview for debugging
if st.checkbox("Show API Response Debug"):
    st.json({"employees": employees_response, "templates": templates_response})

# File upload
uploaded_file = st.file_uploader("Carregar CSV enriquecido", type=['csv'])

if uploaded_file is not None:
    df = load_enriched_csv(uploaded_file)
    
    if df is not None:
        # Display data preview
        st.subheader("Preview dos dados")
        st.dataframe(df.head())
        
        # Operator selection with ID mapping
        st.subheader("Selecionar Operador")
        operator_options = [(op['_id'], f"{op['name']} ({op['email']})") for op in operators.values()]
        selected_operator_id = st.selectbox(
            "Escolha o operador",
            options=[op[0] for op in operator_options],
            format_func=lambda x: next(op[1] for op in operator_options if op[0] == x)
        )
        
        # Template selection with ID mapping
        st.subheader("Template da Mensagem")

        # Create options list with template content as display text
        template_options = []
        if flattened_templates:
            # Add all templates from API
            template_options = [(template['id'], template['content']) for template in flattened_templates]
            
        # Add personalized option at the end
        template_options.append(("personalizado", "Personalizado"))

        # Create the selectbox with template contents as options
        selected_template_id = st.selectbox(
            "Escolha o template",
            options=[t[0] for t in template_options],
            format_func=lambda x: next((t[1][:100] + "..." if len(t[1]) > 100 else t[1]) 
                              for t in template_options if t[0] == x),
            key="template_selector"
        )

        # Initialize session state for template if not exists
        if 'current_template' not in st.session_state:
            st.session_state.current_template = """Olá {NOME},

Esperamos que esteja bem! 
Identificamos seu cadastro em {CIDADE}/{UF}.

Gostaríamos de confirmar seus dados:
Endereço: {FULL-LOGRADOURO}
CEP: {CEP}

Por favor, confirme se estas informações estão corretas."""

        if selected_template_id == "personalizado":  # Custom template
            message_template = st.text_area(
                "Personalize sua mensagem",
                value=st.session_state.current_template,  # Use saved template
                height=200,
                help="Use {NOME}, {CIDADE}, {UF}, etc. para inserir dados do contato",
                key="custom_template"
            )
            # Save any changes to session state
            st.session_state.current_template = message_template
        else:
            # Find the selected template in the flattened templates
            selected_template = next(
                (t for t in flattened_templates if t['id'] == selected_template_id), 
                None
            )
            
            if selected_template:
                message_template = selected_template['full_content']
                st.session_state.current_template = message_template  # Save to session state
                
                st.text_area(
                    "Preview do template", 
                    value=message_template,
                    disabled=True,
                    height=200,
                    help="Os placeholders serão substituídos automaticamente ao enviar"
                )
                
                # Show media URL if available
                if selected_template.get('content_media'):
                    st.info(f"Mídia anexada: {selected_template['content_media']}")
            else:
                st.error("Template selecionado não encontrado")
        
        
        # Get WhatsApp integrations
        integrations = get_formatted_integrations(tallos_api)

        # Add integration selection to the interface
        if integrations:
            st.subheader("WhatsApp Integration")
            
            # Criar lista de opções com o ID correto
            integration_options = [
                {"label": integration['label'], "key": integration['key']}
                for integration in integrations
            ]
            
            # Usar selectbox com dicionário de opções
            selected_integration = st.selectbox(
                "Selecione a integração",
                options=integration_options,
                format_func=lambda x: x['label'],
                key="whatsapp_integration"
            )
            
            # Pegar o ID correto da integração selecionada
            selected_integration_id = selected_integration['key']
            
            # Mostrar detalhes da integração selecionada para debug
            st.code(f"Integração selecionada: {selected_integration['label']} (ID: {selected_integration_id})")
        else:
            st.error("Não foi possível buscar as integrações do WhatsApp")
        
        # Send messages button
        if st.button("Enviar Mensagens"):
            if not selected_integration:
                st.error("Por favor, selecione uma integração do WhatsApp primeiro")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                success_count = 0
                total = len(df)
                
                for index, row in df.iterrows():
                    contact_data = row.to_dict()
                    if send_tallos_message(
                        tallos_api=tallos_api,
                        contact_data=contact_data,
                        message_template=message_template,
                        selected_operator_id=selected_operator_id,
                        selected_integration=selected_integration
                    ):
                        success_count += 1
                    
                    # Update progress
                    progress = (index + 1) / total
                    progress_bar.progress(progress)
                    status_text.text(f"Processando: {index + 1}/{total}")
                
                st.success(f"Envio concluído! {success_count}/{total} mensagens enviadas com sucesso.")

# Display logs
if st.sidebar.checkbox("Mostrar Histórico de Envios"):
    if 'send_logs' in st.session_state and st.session_state.send_logs:
        st.sidebar.subheader("Histórico de Envios")
        for log in st.session_state.send_logs:
            st.sidebar.write(f"Data: {log['timestamp']}")
            st.sidebar.write(f"Total de contatos: {log['total_contacts']}")
            st.sidebar.write(f"Envios bem-sucedidos: {log['successful_sends']}")
            st.sidebar.write("---")

# Update the debug section
if st.checkbox("Mostrar informações de debug"):
    debug_info = {
        "Total de templates": len(flattened_templates),
        "Estrutura da resposta": {
            "Grupos de templates": len(templates_response.get('templates', [])) if templates_response else 0,
            "Exemplo de template": flattened_templates[0] if flattened_templates else None
        },
        "Templates": flattened_templates[:5],  # Mostrar apenas os primeiros 5 templates como exemplo
        "Template selecionado": selected_template_id if 'selected_template_id' in locals() else None
    }
    st.json(debug_info)

# Add this where you want to show debug information
if st.checkbox("Show API Debug Logs"):
    with st.expander("Latest API Logs"):
        # Create a text area to display logs
        log_output = st.empty()
        
        # Function to update logs
        def update_logs():
            # Get last 10 log entries (you'll need to implement log storage)
            recent_logs = [
                "Contact creation payload:",
                json.dumps(contact_payload, indent=2),
                "API Response:",
                json.dumps(contact_response, indent=2),
                "Message payload:",
                json.dumps(message_payload, indent=2)
            ]
            log_output.code("\n".join(recent_logs))
