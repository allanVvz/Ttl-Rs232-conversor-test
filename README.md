Explicação das Funções do Algoritmo para Teste de Conversor TTL para RS232
Este documento detalha as funções do algoritmo usado para testar um conversor TTL para RS232. O objetivo principal é avaliar o desempenho e os limites do conversor, enviando e recebendo dados através das portas seriais e monitorando erros e desempenho.
1. Função mudar_baudrate
Descrição: Altera a taxa de transmissão (baudrate) da comunicação serial e reinicia os contadores de pacotes enviados e recebidos. O método também fecha e reabre as portas seriais com o novo baudrate e atualiza o arquivo de log.
Parâmetros:
    • ser_envio: Objeto de comunicação serial usado para enviar dados.
    • ser_recebimento: Objeto de comunicação serial usado para receber dados.
    • num_bytes_para_enviar: Número de bytes a serem enviados em cada pacote.
Exemplo de Uso:
mudar_baudrate(ser_envio, ser_recebimento, 3000)
Esta chamada altera o baudrate para testar a capacidade do conversor em diferentes taxas de transmissão e reinicia os contadores de pacotes.
2. Classe RedirecionadorLog
Descrição: Gerencia a gravação de logs em um arquivo, redirecionando a saída padrão (sys.stdout) para o arquivo de log. Inclui métodos para adicionar cabeçalhos e rodapés com informações de teste, além de escrever e fechar o arquivo de log.
Métodos:
    • __init__(self, nome_arquivo, baudrate, num_bytes_para_enviar): Inicializa o redirecionador com o nome do arquivo e detalhes do teste.
    • write(self, mensagem): Escreve uma mensagem no arquivo de log.
    • flush(self): Garante que o buffer de escrita seja despejado.
    • fechar(self): Fecha o arquivo de log e adiciona um rodapé com o resumo do teste.
    • adicionar_rodape(self): Adiciona um rodapé ao arquivo de log com informações de tempo e contagem de pacotes.
Exemplo de Uso:
redirecionador = RedirecionadorLog("log.txt", 9600, 3000)
redirecionador.write("Início do teste.")
redirecionador.fechar()
3. Função log_com_timestamp
Descrição: Adiciona um timestamp à mensagem e a imprime no log para registro das atividades e eventos do teste.
Parâmetros:
    • mensagem: Mensagem a ser registrada no log com timestamp.
Exemplo de Uso:
python
Copiar código
log_com_timestamp("Início do envio de dados.")
Essa chamada imprime a mensagem com a data e hora atuais, ajudando a rastrear eventos durante o teste.
4. Função receber_e_validar
Descrição: Recebe dados da porta serial e valida o checksum para verificar a integridade dos dados. Conta e reporta erros se a validação falhar.
Parâmetros:
    • ser: Objeto de comunicação serial usado para receber dados.
    • num_bytes_para_receber: Número total de bytes esperados (dados + checksum).
Retorno:
    • b'\x01': Indica que os dados foram recebidos e validados com sucesso.
    • b'\x00': Indica falha na validação dos dados.
Exemplo de Uso:
python
Copiar código
ack = receber_e_validar(ser_recebimento, 3004)
if ack == b'\x01':
    print("Dados recebidos e validados com sucesso.")
else:
    print("Erro na recepção ou validação dos dados.")
5. Função sincronizar_portas
Descrição: Sincroniza as portas seriais enviando e recebendo uma sequência de sincronização. Garante que ambas as portas estejam configuradas corretamente para comunicação.
Parâmetros:
    • ser_envio: Objeto de comunicação serial usado para enviar a sequência de sincronização.
    • ser_recebimento: Objeto de comunicação serial usado para receber a sequência de sincronização.
Retorno:
    • True: Sincronização bem-sucedida.
    • False: Falha na sincronização.
Exemplo de Uso:
python
Copiar código
if sincronizar_portas(ser_envio, ser_recebimento):
    print("Portas sincronizadas com sucesso.")
else:
    print("Falha na sincronização das portas.")
6. Função enviar_dados
Descrição: Envia um pacote de dados pela porta serial, incluindo o checksum calculado para verificar a integridade. Esta função é usada para testar a capacidade de envio de dados do conversor.
Parâmetros:
    • ser: Objeto de comunicação serial usado para enviar dados.
    • num_bytes_para_enviar: Número de bytes a serem enviados em cada pacote.
Exemplo de Uso:
python
Copiar código
enviar_dados(ser_envio, 3000)
print("Dados enviados com sucesso.")
7. Função configurar_conexao_serial
Descrição: Configura uma conexão serial com a porta especificada e a taxa de transmissão (baudrate). Esta função é usada para iniciar a comunicação com o conversor.
Parâmetros:
    • porta: Nome da porta serial (e.g., '/dev/ttyUSB0').
    • baudrate: Taxa de transmissão em bauds.
Retorno:
    • Objeto serial.Serial configurado.
Exemplo de Uso:
python
Copiar código
ser = configurar_conexao_serial('/dev/ttyUSB0', 9600)
if ser:
    print("Conexão estabelecida com sucesso.")
else:
    print("Falha na conexão serial.")
8. Função processar_porta
Descrição: Processa o envio e recebimento de dados para uma porta específica em uma thread separada. Garante que os dados sejam enviados e recebidos conforme o teste é executado.
Parâmetros:
    • ser_envio: Objeto de comunicação serial usado para enviar dados.
    • ser_recebimento: Objeto de comunicação serial usado para receber dados.
    • num_bytes_para_enviar: Número de bytes a serem enviados em cada pacote.
    • num_bytes_para_receber: Número total de bytes esperados na recepção.
    • max_data_count: Número máximo de pacotes antes de mudar o baudrate para testar o conversor em diferentes velocidades.
    • meu_evento: Evento para sincronizar a thread.
    • proximo_evento: Evento para sinalizar a próxima thread.
Exemplo de Uso:
python
Copiar código
processar_porta(ser_envio, ser_recebimento, 3000, 3004, 32, evento_thread0, evento_thread1)
9. Função loop_de_controle
Descrição: Gerencia o fluxo principal do programa, permitindo iniciar, pausar ou sair do teste. Controla a execução das threads e o encerramento do programa.
Parâmetros:
    • ser_envio: Objeto de comunicação serial para envio de dados.
    • ser_recebimento: Objeto de comunicação serial para recepção de dados.
    • redirecionador_log: Objeto RedirecionadorLog para manipulação de logs.
Exemplo de Uso:
python
Copiar código
loop_de_controle(ser_envio, ser_recebimento, redirecionador_log)
10. Função verificar_e_lidar_com_erros
Descrição: Verifica se o número de erros consecutivos atingiu o limite máximo permitido e encerra o programa se necessário. Ajuda a monitorar a estabilidade do conversor.
Parâmetros:
    • ser: Objeto de comunicação serial para verificação de erros.
Exemplo de Uso:
python
Copiar código
verificar_e_lidar_com_erros(ser_envio)
11. Função encerrar_programa
Descrição: Encerra o programa suavemente, fechando as portas seriais e o arquivo de log, e imprimindo um resumo final do teste. Garante que todos os recursos sejam liberados corretamente.
Parâmetros:
    • ser_envio: Objeto de comunicação serial usado para envio de dados.
    • ser_recebimento: Objeto de comunicação serial usado para recepção de dados.
    • redirecionador_log: Objeto RedirecionadorLog para manipulação de logs.
Exemplo de Uso:
python
Copiar código
encerrar_programa(ser_envio, ser_recebimento, redirecionador_log)

Este documento oferece uma visão geral detalhada das funções do algoritmo, ajudando a entender como testar e avaliar a performance de um conversor TTL para RS232, incluindo como lidar com dados, erros e resultados de teste.
