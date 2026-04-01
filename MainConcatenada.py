#Bibliotecas usadas:

#Nativas do Python:
import sys # vem do
import os # Conversa com o OS, usamos para navegar entre as pastas
import re
import html
import csv
from dataclasses import dataclass
from typing import Any
from collections import defaultdict

#Instaladas:
import dotenv
import httpx # Essencialmente uma versão nova da "requests"; Faz a mesma coisa, fala com a "web", mas suportant código assincrono, ou seja usamos para fazer varias requisições ao mesmo tempo sem esperar a anterior finalizar;

from bs4 import BeautifulSoup

#====================================================================================================================================================================================================
#CONFIG_LOADER - from src.utils.config_loader
#====================================================================================================================================================================================================
def loadConfig():
    """
    Carrega e valida as configurações de ambiente necessárias.
    
    Por diretrizes de segurança da informação e boas práticas de Engenharia de Software, as credenciais de acesso e tokens da API do GLPI não são fixados (hardcoded) no código-fonte.
    O sistema realiza a leitura dinâmica a partir de um arquivo externo local (.env), garantindo a proteção de dados sensíveis e facilitando a portabilidade do software.

    Retorno:
        dict: Dicionário contendo as chaves validadas, ou None em caso de ausência de dados.
    """

    # Localizando o arquivo de configuração, ou seja as chaves, dentro do arquivo .env
    caminhoEnv = os.path.join(raizProjeto, "config", ".env") 
    
    # Checa se o arquivo de variáveis de ambiente existe.
    # Caso negativo, interrompe o fluxo e instrui sobre a parametrização necessária.
    if not os.path.exists(caminhoEnv):
        print(f"AVISO: Arquivo .env não encontrado em {caminhoEnv}")
        print(f"Crie {caminhoEnv} com:")
        print("GLPI_API_URL")
        print("GLPI_APP_TOKEN")
        print("GLPI_USER_TOKEN")
        return None 

    # Carrega as variáveis do .env para o contexto de execução do sistema.
    load_dotenv(dotcaminhoEnv=caminhoEnv) 
    
    # Estrutura em um dicionário as credenciais extraídas do ambiente do sistema operacional.
    chaves = {"GLPI_API_URL": os.getenv("GLPI_API_URL"), "GLPI_APP_TOKEN": os.getenv("GLPI_APP_TOKEN"), "GLPI_USER_TOKEN": os.getenv("GLPI_USER_TOKEN"),}
    
    # Verifica se todas as chaves possuem valores válidos (truth).
    # Caso negativo, previne que o sistema tente realizar requisições à API caso algum token esteja em branco.
    if not all(chaves.values()):
        print("AVISO: Uma ou mais variáveis (API_URL, APP_TOKEN, USER_TOKEN) não estão definidas.")
        return None
    return chaves
# Inicializa as configurações globais de integração para serem consumidas pelos demais módulos de automação.
chaves = loadConfig()
#====================================================================================================================================================================================================
#SESION - from src.auth.session
#====================================================================================================================================================================================================
def autenticarGlpi(api_url, app_token, user_token):
    """
    Realiza a autenticação na API REST do GLPI e estabelece uma sessão de comunicação.
    
    Constrói os cabeçalhos HTTP (headers) necessários conforme a documentação oficial da API do GLPI. 
    O objetivo é trocar os tokens estáticos (App-Token e User-Token) por um Session-Token dinâmico, que autorizará as requisições subsequentes do sistema.
    
    Args:
        api_url (str): URL base de integração com a API do GLPI.
        app_token (str): Token de aplicação para identificar o cliente (ITXAutoNTI).
        user_token (str): Token de usuário para validar os privilégios de acesso.
        
    Returns:
        str: Token de sessão (session_token) em caso de sucesso, ou None em caso de falha.
    """
    
    # Monta os cabeçalhos da requisição, atuando como a "credencial de apresentação" da aplicação.
    cartaoVisita = {
        'App-Token': app_token,
        'Authorization': f'user_token {user_token}', #formata para "user_token xxxxxxxxx" - PADRÃO EXIGIDO PELO GLPI
        'Content-Type': 'application/json', # converte para JSON
    }

    try:
        # Efetua a requisição GET para o endpoint de inicialização de sessão (/initSession).
        response = httpx.get(f"{api_url}/initSession", headers=cartaoVisita, verify=False)
        # Valida a integridade da resposta. Se o status HTTP indicar erro (ex: 401 Não Autorizado, 500 Erro de Servidor),
        response.raise_for_status()
        # Converte a resposta em JSON e pega só o token de sessão que está ativo.
        session_token = response.json().get('session_token')

        print("✅ Autenticação bem-sucedida.\n")
        return session_token
    # Tratamento específico para falhas de protocolo HTTP
    except httpx.HTTPStatusError as e:
        print(f"Erro HTTP: {e.response.status_code} - {e.response.text}")
    # Camada de segurança para interceptar falhas inesperadas (ex: queda de rede, timeout de conexão).
    except Exception as e:
        print(f"Erro inesperado: {e}")     
    # Retorna nulo garantindo que a aplicação chamadora saiba que a sessão falhou e possa abortar a execução com segurança.
    return None
#====================================================================================================================================================================================================
#READER - from src.data.reader
#=========================================================================================================================================================================================================================================================================================
def userName(api_url, app_token, user_token, session_token):
    """
    Consulta as informações de perfil de um usuário específico na base de dados do GLPI.
    
    Esta função dá continuidade ao fluxo de comunicação segura. 
    Ela utiliza o Session-Token ativo (obtido na etapa de autenticação) para provar à API que a aplicação tem autorização vigente para realizar consultas.
    
    Args:
        api_url (str): URL base da API REST do GLPI.
        app_token (str): Token de identificação da aplicação.
        user_token (str): Token estático do usuário de serviço.
        session_token (str): Token dinâmico da sessão ativa atual.
    """
    # Constrói os cabeçalhos da requisição injetando o Session-Token.
    # Esta é a assinatura digital que autoriza a transação sem precisar reenviar senhas.
    headers = {
        'App-Token': app_token,
        'Authorization': f'user_token {user_token}',
        'Content-Type': 'application/json',
        'Session-Token': session_token
    }

    # Utiliza um gerenciador de contexto (with) para instanciar o cliente HTTP. 
    # Garantindo que as conexões de rede sejam fechadas e a memória liberada automaticamente no final do bloco, evitando vazamento de recursos do servidor.
    with httpx.Client(verify=False) as client: 
        # Realiza uma requisição GET direcionada ao endpoint do usuário alvo (ID: 41411, do ITXAutoNTI).
        response = client.get(f"{api_url}/user/41411", headers=headers)
        # Desserializa a resposta JSON e extrai apenas o primeiro nome ('firstname') do payload.
        if response.status_code == 200:
            usuario = response.json().get('firstname')
        else:
            print("Erro:", response.status_code, response.text)
#=========================================================================================================================================================================================================================================================================================
#TASK_RETRIEVER - from src.data.task_retriever
#=========================================================================================================================================================================================================================================================================================
def getItxTasks(sessionToken: str, appToken: str, apiUrl: str) -> list[dict]:
    """
    O que faz? 
    - Busca e mapeia tarefas que contém o ITX e estão pendentes no GLPI.
    
    A função constrói uma query complexa utilizando a sintaxe nativa da API de Busca do GLPI, filtrando os chamados diretamente no servidor.
    Em seguida, mapeia as sub-tarefas específicas delegadas ao sistema ITXAutoNTI.
    
    Args:
        sessionToken (str): Token de sessão ativa.
        appToken (str): Token da aplicação.
        apiUrl (str): URL base da API REST.
        
    Returns:
        list[dict]: Lista de dicionários contendo os metadados das tarefas pendentes ("A fazer").
    """
    # Cabeçalhos de autorização utilizando o token de sessão previamente negociado
    headers = {
        "Content-Type": "application/json",
        "Session-Token": sessionToken,
        "App-Token": appToken
    }

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Parte 1. BUSCA DOS CHAMADOS
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    urlPesquisa = f"{apiUrl.rstrip('/')}/search/Ticket"
    # Dicionário de parâmetros de pesquisa (Criteria) estruturado conforme documentação do GLPI.
    parametrosPesquisa = {
        # Filtro de Status do Chamado: Aberto, Em andamento, Em atendimento, Pendente:
        "criteria[2][link]": "AND",

        "criteria[2][criteria][0][link]": "AND",
        "criteria[2][criteria][0][field]": "12",
        "criteria[2][criteria][0][searchtype]": "equals",
        "criteria[2][criteria][0][value]": "1", #aberto

        "criteria[2][criteria][1][link]": "OR",
        "criteria[2][criteria][1][field]": "12",
        "criteria[2][criteria][1][searchtype]": "equals",
        "criteria[2][criteria][1][value]": "2", #em andamento

        "criteria[2][criteria][2][link]": "OR",
        "criteria[2][criteria][2][field]": "12",
        "criteria[2][criteria][2][searchtype]": "equals",
        "criteria[2][criteria][2][value]": "3", #em atendimento

        "criteria[2][criteria][3][link]": "OR",
        "criteria[2][criteria][3][field]": "12",
        "criteria[2][criteria][3][searchtype]": "equals",
        "criteria[2][criteria][3][value]": "4", #pendente

        # Filtro do Contexto: Apenas chamados que citem o ITXAutoNTI dento das tarefas naquele chamado
        "criteria[3][link]": "AND",
        "criteria[3][field]": "26",
        "criteria[3][searchtype]": "contains",
        "criteria[3][value]": "itxautonti",
    }
    # Requisição HTTP com timeout explícito para evitar bloqueio de thread. Isso para caso haja alguma instabilidade ou lentidão no banco de dados do GLPI.
    resp = httpx.get(urlPesquisa, headers = headers, params = parametrosPesquisa, verify = False, timeout = 10.0)
    resp.raise_for_status()
    #Extrai a listagem principal de chamados
    data = resp.json()
    tickets = data.get("data", [])
    
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Parte 2. MAPEAMENTO DE ESTADOS
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Tradução dos identificadores numéricos do banco de dados para o jargão operacional de TI
    statusMap = {"1": "Aberto","2": "Em andamento","3": "Em atendimento","4": "Pendente","5": "Solucionado","6": "Fechado"}

    statusCheckbox = {"0": "Informação","1": "A fazer","2": "Feito"}

    # Palavras chaves que idenficam que a tarefa é do bot ITXAutoNTI, username e ID
    keywords = ['itxautonti', '41441']
    foundTasks = []
    doneTasksLog = []

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Parte 3. EXTRAÇÃO DE TAREFAS E ANALISE DE IDEMPOTÊNCIA
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    for ticket in tickets:
        ticketId = ticket.get("2")
        ticketStatusId = ticket.get("12")
        ticketStatusName = statusMap.get(str(ticketStatusId), "Desconhecido")
        # No GLPI cada chamado (ticket) tem seu próprio ID e cada tarefa (Task) tem o seu também, devido a isso, é necessário uma segunda requisição. 
        taskUrl = f"{apiUrl.rstrip('/')}/Ticket/{ticketId}/TicketTask"
        taskResponse = httpx.get(taskUrl, headers = headers, verify = False, timeout = 10.0)
        taskResponse.raise_for_status()
        tasks = taskResponse.json() or []

        hasItxTask = False
        # Varredura do conteúdo de cada tarefa do chamado
        for task in tasks:
            taskId = task.get("id")
            rawContent = task.get("content") or ""
            contentLower = rawContent.lower()
            taskState = task.get("state")
            stateLabel = statusCheckbox.get(str(taskState), "Desconhecido")
            # Verifica se a tarefa dentro do chamado X, está citando o ITXAutoNTI.
            if any(keyword in contentLower for keyword in keywords):
                hasItxTask = True
                # Garantia de Idempotência, serve para separar as tarefas 'A fazer' das já concluídas ('Feito').
                if taskState == 1:  # A fazer
                    foundTasks.append({
                        "ticketId": ticketId,
                        "taskId": taskId,
                        "ticketStatus": ticketStatusName,
                        "state": taskState,
                        "stateLabel": stateLabel,
                        "content": rawContent,
                        "taskState": "A fazer"
                    })

                elif taskState == 2:  # Feito
                    doneTasksLog.append({
                        "ticketId": ticketId,
                        "taskId": taskId,
                        "ticketStatus": ticketStatusName,
                        "state": taskState,
                        "stateLabel": stateLabel,
                    })
        if not hasItxTask:
            print(" ❌ Nenhuma task cita o ITX")

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Parte 4. FEEDBACK VISUAL (CLI DASHBOARD)
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Gera uma interface baseada em texto no console do servidor para que os analistas da equipe possam monitorar as tarefas extraídas em tempo real.
    widths = [12, 10, 14]
    totalWidth = 60
    separatorWidth = sum(widths) + 6  # 12+10+14+6=42

    header = (
        f"{'🧩 Task':^{widths[0]}}│"
        f"{'🎫 Chamado':^{widths[1]}}│"
        f"{'⌛ Status':^{widths[2]}}"
    )
    print(header.center(totalWidth))

    separatorStr = "─" * separatorWidth
    print(separatorStr.center(totalWidth))

    for task in foundTasks:
        line = (
            f"{str(task['taskId']):>10}│"
            f"{str(task['ticketId']):>8}│"
            f"{task['taskState']:<12}"
        )
        print(line.center(totalWidth))
    print(separatorStr.center(totalWidth))

    chamados = len(set(t['ticketId'] for t in foundTasks))
    taskCount = len(foundTasks)
    print(f"📦 Chamados: {chamados} │ 🍧 Tasks: {taskCount}".center(totalWidth))

    return foundTasks
#====================================================================================================================================================================================================
#TASK_PARSER - from src.logic.task_parser
#====================================================================================================================================================================================================

@dataclass
class Instruction:
    """
    Estrutura de Dados (Data Class): Define o modelo de objeto para cada instrução de inventário.
    Encapsula metadados do ativo, do chamado e a ação a ser executada, garantindo tipagem forte
    e integridade dos dados durante o fluxo de automação.
    """
    itemId: str                 # Identificador interno único no banco de dados dos equipamentos/itens do GLPI
    patrimonioItem: str         # Identificador visual/institucional padrão UFABC (Ex: UF000000)
    statusItem: str             # Estado operacional (Ativo, Manutenção, etc)
    acaoItem: str               # Operação lógica (Inserir ou Remover)
    localItem: str              # Localização extraída do texto bruto
    localFuzzyNome: str         # Localização normalizada via algoritmo Fuzzy
    localFuzzyCodigo: str       # Código de localização compatível com o banco de dados
    tipoItem: str               # Categoria do hardware (Computer, Monitor, etc)
    chamadoId: str              # Referência ao Ticket de origem
    tarefaId: str               # Referência à Task de origem

    def __str__(self) -> str:
        return (
            f"Instruction("
            f"chamadoId={self.chamadoId}, "
            f"tarefaId={self.tarefaId}, "
            f"tipoItem={self.tipoItem}, "
            f"itemId={self.itemId}, "
            f"patrimonioItem={self.patrimonioItem}, "
            f"acaoItem={self.acaoItem}, "
            f"localItem={self.localItem}, "
            f"statusItem={self.statusItem}"
            f")"
        )

# MAPEAMENTO: Dicionario para normalização de categorias de hardware
tipoMap = {
    "computador": "Computer",
    "computadores": "Computer",
    "computer": "Computer",
    "monitor": "Monitor",
    "monitores": "Monitor",
    "impressora": "Printer",
    "impressoras": "Printer",
    "dispositivos": "peripheral",  
    "dispositivo": "peripheral",
}
def normalizarNumero(n):
    """
    Garante a integridade numerica removendo os zeros à esquerda ou formatações inconsistentes.
    """
    return str(int(n))

def extrairCamposTask(textoHtml: str) -> dict:
    """
    Motor de Extração de Dados (Parsing): Analisa o conteúdo HTML das tarefas.
    Utiliza Expressões Regulares (Regex) e análise de DOM para interpretar a marcação (X) feita por humanos em campos de formulário dentro do GLPI.
    """
    if not textoHtml: return {}

    
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Parte 1. LIMPEZA DE CONTEÚDO
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # FILTRO: Converte entidades (como &nbsp;) e remove ruídos visuais/estruturas de layout que podem poluir (tabelas)
    textoHtml = html.unescape(textoHtml)
    soup = BeautifulSoup(textoHtml, "html.parser")
    for tabela in soup.find_all("table"):
        tabela.decompose()
    texto = soup.get_text("\n", strip=True)
    linhas = [l for l in texto.split("\n") if "* dica:" not in l.lower()]
    textoLimpo = "\n".join(linhas)

    # FILTRO: Regex que aceita qualquer caractere (ou espaço) dentro dos parênteses
    regexMarcador = r'\(\s*[^)\s]+\s*\)'

    # EXTRAÇÃO: Extrai a ação preenchida (inserir/remover)
    matchAcao = re.search(r'ação\s*:\s*(.+?)(?=status do ativo:|localiza[çc][aã]o do ativo:|$)',textoLimpo, re.IGNORECASE | re.DOTALL)
    valorAcao = None
    if matchAcao:
        blocoAcao = matchAcao.group(1)
        marcacoes = re.findall(regexMarcador, blocoAcao)
        if len(marcacoes) > 1:
            raise ValueError(f"Múltiplas ações marcadas {marcacoes}")
        if re.search(rf'{regexMarcador}\s*inserir', blocoAcao, re.IGNORECASE):
            valorAcao = "inserir"
        elif re.search(rf'{regexMarcador}\s*remover', blocoAcao, re.IGNORECASE):
            valorAcao = "remover"

    if not valorAcao:
        raise ValueError("Nenhuma ação marcada! Use (X) Inserir ou (X) Remover")

    # EXTRAÇÃO: Extrai o status desejado (Opcional)
    matchStatus = re.search(r'status do ativo\s*:\s*(.+?)(?=localiza[çc][aã]o do ativo:|$)', textoLimpo, re.IGNORECASE | re.DOTALL)
    valorStatus = None
    if matchStatus:
        blocoStatus = matchStatus.group(1).replace('\n', ' ') # Remove quebras de linha para a regex não falhar
        opcoesStatus = ["em estoque", "ativo", "desfeito", "irrecuperável", "obsoleto", "disponível para empréstimo", "emprestado", "manutenção", "ocioso"]
        for opcao in opcoesStatus:
            if re.search(rf'{regexMarcador}\s*{re.escape(opcao)}', blocoStatus, re.IGNORECASE):
                valorStatus = opcao
                break

    # EXTRAÇÃO: Extrai a localização desejada (Opcional)
    matchLocal = re.search(
        r'localiza[çc][aã]o do ativo\s*:\s*(.+)', 
        textoLimpo, re.IGNORECASE
    )
    local = matchLocal.group(1).strip() if matchLocal else None

    return {"acao": valorAcao,"statusAtivo": valorStatus, "localizacao": local}

def extrairPatrimoniosPorTipo(textoHtml: str) -> dict:
    """
    Análise de Tabela de Dados: Varre o HTML em busca de tabelas de inventário, agrupando números de patrimônio por suas respectivas categorias (computador, monitor, etc).
    """
    if not textoHtml: return {}

    textoHtml = html.unescape(textoHtml)
    soup = BeautifulSoup(textoHtml, "html.parser")
    resultado = defaultdict(list)

    for row in soup.find_all("tr")[1:]:  # pula cabeçalho
        cols = row.find_all("td")
        if len(cols) < 2: continue
        tipo = cols[0].get_text(strip=True).lower()
        celula = cols[1].get_text(" ", strip=True)
        # Extração numérica via Regex para isolar o patrimônio de qualquer texto adjacente
        numeros = re.findall(r'\d+', celula)
        for n in numeros:
            resultado[tipo].append(normalizarNumero(n))

    # Contra a duplicação de dados: Garante que o mesmo item não seja processado mais de uma vez no mesmo lote.
    for tipo in resultado:
        resultado[tipo] = sorted(set(resultado[tipo]), key=int)

    return dict(resultado)

def findItemId(sessionToken: str, appToken: str, apiUrl: str, itemType: str, patrimonioItem: str) -> tuple[str, str] | None:
    """
    Verificador de Existência (Service Discovery): Consulta a API do GLPI para validar se o número de patrimônio extraído do texto existe no inventário oficial e recupera seu ID único global.
    """
    if not itemType or itemType == "None":
        print(f"⚠️ Pulando busca: itemType inválido '{itemType}' para patrimônio {patrimonioItem}")
        return None
    
    headers = {"Content-Type": "application/json", "Session-Token": sessionToken, "App-Token": appToken}
    urlPesquisa = f"{apiUrl.rstrip('/')}/search/{itemType}"

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Parte 1. BUSCA DOS CHAMADOS
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    parametros = {
        "criteria[0][field]": "1",
        "criteria[0][searchtype]": "contains",
        "criteria[0][value]": patrimonioItem, 
        "forcedisplay[0]": "2",                 # Retorna o ID interno 
        "forcedisplay[1]": "1",                 # Retorna o nome oficial (patrimonio)
    }
    
    resp = httpx.get(urlPesquisa, headers=headers, params=parametros, verify=False)
    resp.raise_for_status()
    data = resp.json()
    resultado = data.get("data", [])
    
    if not resultado: return None

    primeiraColuna = resultado[0]
    itemId = primeiraColuna.get("2")  # id interno
    itemNome = primeiraColuna.get("1")  # nome (ex: UF038380)

    if not itemId or not itemNome:
        return None

    return str(itemId), str(itemNome)

def parseTaskInstruction(dadosTarefa: Dict[str, Any], sessionToken: str, appToken: str, apiUrl: str) -> List[Instruction]:
    """
    Orquestrador de Parsing: Coordena as funções de extração e validação para gerar 
    uma lista de objetos de instrução executáveis.
    """
    chamadoId = str(dadosTarefa.get("ticketId") or dadosTarefa.get("ticket_id") or "")
    tarefaId = str(dadosTarefa.get("taskId") or dadosTarefa.get("task_id") or "")
    content = dadosTarefa.get("content")

    if not content:
        print(f"❌ Task {tarefaId}: sem content")
        return []
    
    try:
        # Decompõe todo o conteúdo dentro da tarefa (task)
        campos = extrairCamposTask(content)
        patrimoniosPorTipo = extrairPatrimoniosPorTipo(content)
        
        acaoItem = campos.get("acao")
        statusAtivo = campos.get("statusAtivo")
        localItem = campos.get("localizacao")
        
        # Validações (Status e Local são opcionais e não quebram o código)
        if not acaoItem:
            raise ValueError("Nenhuma ação marcada!")
        if not patrimoniosPorTipo:
            raise ValueError("Nenhum patrimônio na tabela!")
        
        print(f"✅ Task {tarefaId}: Ação: {acaoItem} / Status: {statusAtivo} / Local: {localItem}")
    # Descarta a tarefa por algum erro de invalidação    
    except ValueError as e:
        print(f"❌ Task {tarefaId} inválida: {e}")
        return []
    
    instructions: List[Instruction] = []
    
    for tipo, listaIds in patrimoniosPorTipo.items():
        tipoGlpi = tipoMap.get(tipo.lower())
        if not tipoGlpi:
            print(f"⚠️ Tipo '{tipo}' não mapeado")
            continue
        
        for equipamentoId in listaIds:
            equipamentoIdStr = str(equipamentoId)
            
            # Normalização de localização via algoritmo Fuzzy (Mapeamento aproximado de strings)
            matchLocal = getLocalizacaoFuzzy(localItem) if localItem else None
            fuzzyNome = matchLocal["Nome"] if matchLocal else ""
            fuzzyCodigo = matchLocal["Codigo"] if matchLocal else ""
            # Validação cruzada com o banco de dados do GLPI
            itemData = findItemId(sessionToken, appToken, apiUrl, tipoGlpi, equipamentoIdStr)
            
            # TRATAMENTO DE ERRO: Caso o item não seja encontrado no GLPI, a instrução é gerada com itemId vazio para tratamento de erro e log no executor
            if not itemData:
                instructions.append(Instruction(
                    itemId="",                          # Fica vazio, pois se não encontrou, logo não existe ID
                    patrimonioItem=equipamentoIdStr,
                    chamadoId=chamadoId,
                    tarefaId=tarefaId,
                    acaoItem=acaoItem,
                    localItem=localItem or "",
                    localFuzzyNome=fuzzyNome,
                    localFuzzyCodigo=fuzzyCodigo,
                    statusItem=statusAtivo or "",
                    tipoItem=tipoGlpi,
                ))
                continue 

            itemId, itemNome = itemData
            
            instructions.append(Instruction(
                itemId=itemId,
                patrimonioItem=itemNome,
                chamadoId=chamadoId,
                tarefaId=tarefaId,
                acaoItem=acaoItem,
                localItem=localItem or "",
                localFuzzyNome=fuzzyNome,
                localFuzzyCodigo=fuzzyCodigo,
                statusItem=statusAtivo or "",
                tipoItem=tipoGlpi,
            ))
    
    return instructions


#====================================================================================================================================================================================================
#TASK_EXECUTOR - from src.logic.task_executor
#====================================================================================================================================================================================================

def getStatusELocalItem(apiUrl: str, headers: Dict[str, str], itemType: str, itemId: str) -> tuple[str, str]:
    """
    Monitoramento de Estado (Snapshot): Consulta o GLPI para capturar o status e a localização atuais de um item antes ou depois de uma transação.
    """
    url = f"{apiUrl.rstrip('/')}/{itemType}/{itemId}"
    # O parâmetro "expand_dropdowns=true" instrui a API a retornar os "nomes amigáveis" dos campos
    params = {"expand_dropdowns": "true"}
    resp = httpx.get(url, headers=headers, params=params, verify=False)

    if resp.status_code != 200: return f"ERRO_{resp.status_code}", "N/A"

    data = resp.json()
    
    # EXTRAÇÃO: Extração dinâmica de chaves de localização e estado conforme a estrutura de dados do GLPI
    statusName = str(data.get("states_id") or data.get("status") or "?")
    localName = str(data.get("locations_id") or data.get("location") or "?")
    
    return statusName, localName

@dataclass
class Result:
    """
    Data Transfer Object (DTO): Consolida os resultados da execução para geração de relatórios de conformidade e fechamento de tarefas.
    """
    success: bool
    patrimonio: str
    itemId: str
    chamadoId: str
    tarefaId: str
    tipoItem: str
    lancStatusamento: str        # String estruturada contendo o histórico da transação (Pipeline de estados)
    action: str
    erro: Optional[str] = None

    def __str__(self) -> str:
        return (f"Result(success={self.success}, patrimonio={self.patrimonio}, "f"status={self.lancStatusamento})")

def getLocationIdByCode(apiUrl: str, headers: dict, codigo: str, nome: str) -> str:
    """
    Resolução de Entidades: Busca o ID interno da localização no GLPI utilizando uma estratégia de busca por Código (ex: SS15) e Nome.
    """
    url = f"{apiUrl.rstrip('/')}/search/Location"
    tentativas = [codigo, nome]
    
    for termo in tentativas:
        if not termo: continue
        # Testa no campo 1 (Nome) e 200 (Nome Completo)
        for field in ["1", "200"]:
            params = {
                "criteria[0][field]": field,
                "criteria[0][searchtype]": "contains",
                "criteria[0][value]": termo,
                "forcedisplay[0]": "2"                   # Retorna o ID numérico
            }
            try:
                resp = httpx.get(url, headers=headers, params=params, verify=False)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("data") and len(data["data"]) > 0:
                        idInterno = str(data["data"][0].get("2"))
                        if idInterno and idInterno != "None": return idInterno
            except Exception: continue
                
    return None

def getEstadoAtualItem(apiUrl: str, headers: Dict[str, str], itemType: str, itemId: int) -> str:
    """
    Módulo de Auditoria e Transparência: Gera um arquivo CSV detalhando cada ação realizada pelo robô. 
    Este arquivo é utilizado como evidência técnica anexada ao chamado original, garantindo a rastreabilidade da automação.
    """
    url = f"{apiUrl.rstrip('/')}/{itemType}/{itemId}"
    resp = httpx.get(url, headers=headers, verify=False)

    if resp.status_code != 200:
        return f"ERRO_GET_{resp.status_code}"

    data = resp.json()
    stateId = data.get("statusId") or "?"
    stateName = data.get("statusId_name") or "?"
    return f"{stateName} (ID:{stateId})"


def gerarHistoricoCsv(results: List[Result], chamadoId: str, tarefaId: str) -> str:
    """
    Módulo de Persistência e Auditoria: Gera arquivo CSV com a trilha 
    de auditoria de todas as movimentações realizadas pela automação.
    """
    
    # 1. Cria a pasta 'relatorios' automaticamente na raiz do projeto
    projectRoot = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    reportsDir = os.path.join(projectRoot, "relatorios")
    
    currentDir = os.getcwd()
    
    # 2. Cria o caminho exato para a pasta relatorios e cria ela se não existir
    reportsDir = os.path.join(currentDir, "relatorios")
    os.makedirs(reportsDir, exist_ok=True)
    
    # 3. Gera arquivo com nome único expressando timestamp para evitar sobrescrita
    fileName = f"historico_chamado_{chamadoId}_task_{tarefaId}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filePath = os.path.join(reportsDir, fileName)

    with open(filePath, "w", newline="", encoding="utf-8") as csvFileObj:
        writer = csv.writer(csvFileObj)

        # Cabeçalho
        writer.writerow(
            [
                "Patrimônio",
                "Item ID",
                "Tipo",
                "Ação Solicitada",
                "Status Anterior",
                "Status Atual",
                "Localização Anterior",
                "Localização Depois",
                "Sucesso",
                "Erro (se houver)",
            ]
        )

        for result in results:
            statusAntes = statusDepois = localAntes = localDepois = ""

            # Quebra o lancStatusamento estruturado
            parts = result.lancStatusamento.split("|")
            for part in parts:
                if part.startswith("STATUS_ANTES:"):
                    statusAntes = part.split(":", 1)[1].strip()
                elif part.startswith("STATUS_DEPOIS:"):
                    statusDepois = part.split(":", 1)[1].strip()
                elif part.startswith("LOCAL_ANTES:"):
                    localAntes = part.split(":", 1)[1].strip()
                elif part.startswith("LOCAL_DEPOIS:"):
                    localDepois = part.split(":", 1)[1].strip()

            writer.writerow(
                [
                    result.patrimonio,              # UF060553
                    result.itemId,                  # 3758
                    result.tipoItem,                # Computer
                    result.action.upper(),          # INSERIR
                    statusAntes,                    # Ativo
                    statusDepois,                   # Em estoque
                    localAntes,                     # CNS
                    localDepois,                    # Devel
                    "OK" if result.success else "FALHOU",
                    result.erro or "",
                ]
            )

    print(f"📊 Histórico salvo: {fileName}")
    return filePath


def associarItemAoChamado(
    apiUrl: str,
    headers: Dict[str, str],
    instruction: Instruction,
) -> str:
    """
    Cria vínculo na tabela Item_Ticket.
    Equivalente a clicar em 'Adicionar um item' dentro do chamado.
    """
    ticketId = int(instruction.chamadoId)
    itemId = int(instruction.itemId)
    itemTypeStr = instruction.tipoItem

    url = f"{apiUrl.rstrip('/')}/Item_Ticket"
    payload = {
        "input": {
            "tickets_id": ticketId,
            "items_id": itemId,
            "itemtype": itemTypeStr,
        }
    }

    resp = httpx.post(url, headers=headers, json=payload, verify=False)

    return f"Assoc:{resp.status_code}"


def removerItemDoChamado(
    apiUrl: str,
    headers: Dict[str, str],
    instruction: Instruction,
) -> str:
    """
    Remove a associação item <-> ticket na tabela Item_Ticket,
    buscando pelos vínculos do próprio chamado.
    """
    ticketId = instruction.chamadoId
    itemId = int(instruction.itemId)
    itemTypeStr = instruction.tipoItem

    urlList = f"{apiUrl.rstrip('/')}/Ticket/{ticketId}/Item_Ticket"
    resp = httpx.get(urlList, headers=headers, verify=False)
    if resp.status_code not in (200, 206):
        return f"List ERRO {resp.status_code}: {resp.text}"

    data = resp.json() or []

    vinculos = [
        r
        for r in data
        if int(r.get("items_id", 0)) == itemId and r.get("itemtype") == itemTypeStr
    ]

    if not vinculos:
        return "Nenhum vínculo encontrado para remover"

    for v in vinculos:
        vincId = v.get("id")
        if not vincId:
            continue
        urlDel = f"{apiUrl.rstrip('/')}/Item_Ticket/{vincId}"
        httpx.delete(urlDel, headers=headers, verify=False)

    return f"Removidos {len(vinculos)} vínculos"


def executeFromParsedTask(
    sessionToken: str,
    appToken: str,
    apiUrl: str,
    taskInstructions: List[Instruction],
) -> tuple[List[Result], Optional[str]]:
    """
    Recebe a lista de Instruction gerada pelo parser e executa
    as ações no GLPI para cada uma, gerando também o CSV de histórico.
    """
    results: List[Result] = []

    headers = {
        "Content-Type": "application/json",
        "Session-Token": sessionToken,
        "App-Token": appToken,
    }

    sucessos = 0
    total = len(taskInstructions)
    print(f"🚀 Executando {total} instructions...")

    for i, instruction in enumerate(taskInstructions, 1):
        print(f"  {i:2d}/{total} {instruction.patrimonioItem} ({instruction.tipoItem})...")
        result = processSingleAsset(apiUrl, headers, instruction)
        results.append(result)

        if result.success:
            sucessos += 1
        else:
            print(f"    ❌ {result.erro}")

    print(f"✅ {sucessos}/{total} executados com sucesso")

    if results:
        csvFile = gerarHistoricoCsv(
            results,
            results[0].chamadoId,
            results[0].tarefaId,
        )
        print(f"📊 {csvFile}")
        return results, csvFile

    return results, None


def processSingleAsset(
    apiUrl: str,
    headers: Dict[str, str],
    instruction: Instruction,
) -> Result:
    
    if not instruction.itemId:
        return Result(
            success=False,
            patrimonio=instruction.patrimonioItem, # Vai salvar "12345"
            itemId="N/A",
            chamadoId=instruction.chamadoId,
            tarefaId=instruction.tarefaId,
            tipoItem=instruction.tipoItem,
            lancStatusamento="STATUS_ANTES:N/A|STATUS_DEPOIS:N/A|LOCAL_ANTES:N/A|LOCAL_DEPOIS:N/A|UPDATE:N/A|ASSOC:N/A",
            action=instruction.acaoItem,
            erro="NOK - Item não cadastrado no GLPI" # Vai aparecer na coluna J
        )
    
    patrimonio = instruction.patrimonioItem
    ticketId = instruction.chamadoId
    tarefaId = instruction.tarefaId
    itemId = int(instruction.itemId)
    itemType = instruction.tipoItem
    action = (instruction.acaoItem or "").lower()           # "inserir" / "remover"
    textoStatus = (instruction.statusItem or "").lower()    # "ativo", "em estoque", etc.
    novaLocal = instruction.localItem or ""                 # "Devel" vindo da task

    # Lê STATUS e LOCALIZAÇÃO ANTES da alteração
    statusAntes, localAntes = getStatusELocalItem(apiUrl, headers, itemType, str(itemId))

    # Mapeia texto → ID numérico do GLPI
    mapStatus = {
        "ativo": 7,
        "desfeito": 13,
        "irrecuperável": 1,
        "obsoleto": 2,
        "ocioso": 12,
        "recuperavel": 11,
        "disponível para empréstimo": 8,
        "disponivel para emprestimo": 8,
        "em estoque": 5,
        "emprestado": 9,
        "manutenção": 3,
        "manutencao": 3,
    }
    realStatus = mapStatus.get(textoStatus)

    fields: Dict[str, Any] = {}
    fields["id"] = itemId # IMPORTANTE: O GLPI exige o ID do item dentro do payload no PUT

    if realStatus is not None:
        # ajuste para o nome do campo de status numérico no seu GLPI
        fields["states_id"] = realStatus

    # --- INÍCIO DA MÁGICA DA LOCALIZAÇÃO ---
    if getattr(instruction, "localFuzzyCodigo", None):
        locId = getLocationIdByCode(apiUrl, headers, instruction.localFuzzyCodigo, instruction.localFuzzyNome)
        if locId:
            fields["locations_id"] = int(locId)
        else:
            print(f"⚠️ Aviso: ID numérico não encontrado no GLPI para o código {instruction.localFuzzyCodigo}")
    # --- FIM DA MÁGICA ---

    msgUpdate = "Sem alterações"
    msgAssoc = "Sem associação"

    try:
        # Atualiza STATUS e/ou LOCALIZAÇÃO se houver algo além do próprio 'id' no fields
        if len(fields) > 1: 
            itemUrl = f"{apiUrl.rstrip('/')}/{itemType}/{itemId}"
            rUpdate = httpx.put(
                itemUrl,
                headers=headers,
                json={"input": fields},
                verify=False,
            )
            msgUpdate = f"Upd:{rUpdate.status_code}"

        # Associa / remove item do chamado
        if action == "inserir":
            msgAssoc = associarItemAoChamado(apiUrl, headers, instruction)
        elif action == "remover":
            msgAssoc = removerItemDoChamado(apiUrl, headers, instruction)
        else:
            msgAssoc = f"Ação desconhecida: {instruction.acaoItem}"

        # Lê STATUS depois (local depois vamos considerar o da task)
        statusDepois, _ = getStatusELocalItem(apiUrl, headers, itemType, str(itemId))
        localDepois = novaLocal or localAntes

        # String estruturada para o CSV
        lancStatus = (
            f"STATUS_ANTES:{statusAntes}"
            f"|STATUS_DEPOIS:{statusDepois}"
            f"|LOCAL_ANTES:{localAntes}"
            f"|LOCAL_DEPOIS:{localDepois}"
            f"|UPDATE:{msgUpdate}"
            f"|ASSOC:{msgAssoc}"
        )

        return Result(
            success=True,
            patrimonio=patrimonio,
            itemId=str(itemId),
            chamadoId=ticketId,
            tarefaId=tarefaId,
            tipoItem=itemType,
            lancStatusamento=lancStatus,
            action=action,
        )

    except Exception as e:
        lancStatus = (
            f"STATUS_ANTES:{statusAntes}"
            f"|STATUS_DEPOIS:ERRO"
            f"|LOCAL_ANTES:{localAntes}"
            f"|LOCAL_DEPOIS:{novaLocal or localAntes}"
            f"|UPDATE:ERRO"
            f"|ASSOC:ERRO"
        )
        return Result(
            success=False,
            patrimonio=patrimonio,
            itemId=str(itemId),
            chamadoId=ticketId,
            tarefaId=tarefaId,
            tipoItem=itemType,
            lancStatusamento=lancStatus,
            action=action,
            erro=str(e),
        )


































def main():
    print("\n\n" + "-" * 60)
    print("🚀 ====== ITXConexão =====")
    print("-" * 60)

    print("\n🔍 1. Carregando configurações...")
    apiUrl = chaves.get("GLPI_API_URL")
    appToken = chaves.get("GLPI_APP_TOKEN")
    userToken = chaves.get("GLPI_USER_TOKEN")

    if not all([apiUrl, appToken, userToken]):
        print("❌ Erro: Configurações da API não encontradas no .env. Abortando.")
        return 

    print(f"✅ Configurações OK.")
#------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Autenticação
    print("\n🔐 2. Autenticando no GLPI...")
    sessionToken = autenticarGlpi(apiUrl, appToken, userToken)

    if sessionToken:
        userNome = userName(apiUrl, appToken, userToken, sessionToken)
    else:
        print("❌ Erro: Autenticação falhou! Verifique tokens no .env")
        return 1
    print("\n" + "-" * 60)
    print("🎉 === ITXConexão - CONCLUIDO ===")
    print("-" * 60)

#------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Tasks 
    print("\n\n\n" + "-" * 60)
    print("👾⋆˚===== Task Retriever + Task Parser + Task Action =====˖°👾")
    print("-" * 60)
    print("Pesquisa dos chamados e das tasks que citam o ITXAutoNTI.\n")

    tasks = getItxTasks(sessionToken, appToken, apiUrl)

    for task in tasks:
        ticketId = str(task.get("ticketId") or "")
        taskId = str(task.get("taskId") or "")

        taskInstructions = parseTaskInstruction(task, sessionToken, appToken, apiUrl)

        for i, instr in enumerate(taskInstructions, 1):
            print(f"  {i}. {instr}")

        if taskInstructions:
            # Desempacotar a tupla (resultados, csvFile)
            resultados, csvFile = executeFromParsedTask(sessionToken, appToken, apiUrl, taskInstructions)

            sucessos = 0
            total = len(resultados)
            for r in resultados:
                if isinstance(r, dict) and r.get("success") is True:
                    sucessos += 1
                elif hasattr(r, "success") and r.success:
                    sucessos += 1

            print(f"✅ {sucessos}/{total} executados com sucesso")

            # Closer passando a lista de resultados e usando os parâmetros em camelCase
            closeResp = closeTask(
                apiUrl=apiUrl,
                appToken=appToken,
                sessionToken=sessionToken,
                taskId=taskId,
                ticketId=ticketId,
                resultados=resultados,
                csvFile=csvFile
            )

            print("📎 Closer:", closeResp.get("success"))
            
    print("\n" + "-" * 60)
    print("👾⋆˚===== Task Retriever + Task Parser - CONCLUÍDO =====˖°👾")
    print("-" * 60)

if __name__ == "__main__":
    exit(main())
