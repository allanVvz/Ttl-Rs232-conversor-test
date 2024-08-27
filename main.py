import time
import serial
import random
import threading
import sys
from datetime import datetime

# Bloco de variáveis globais
error_count0 = 0
error_count1 = 0
send_lock = threading.Lock()  # Lock para sincronizar o envio de dados
start_event = threading.Event()  # Evento para controlar o início e pausa do programa
exit_event = threading.Event()  # Evento para controlar a saída do programa
baudrate_list = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600, 2000000]
baudrate_index = 0
send_count = 0  # Contador de envios
thread0_event = threading.Event()  # Evento para sincronizar thread0
thread1_event = threading.Event()  # Evento para sincronizar thread1
consecutive_errors = 0
max_consecutive_errors = 5  # Limite de erros consecutivos antes de encerrar o programa

# Função para alterar o baudrate
def change_baudrate(send_ser, receive_ser):
    global baudrate_index, baudrate_list

    baudrate_index = (baudrate_index + 1) % len(baudrate_list)
    new_baudrate = baudrate_list[baudrate_index]

    send_ser.flush()
    receive_ser.flush()

    # Fecha e reabre as portas seriais com o novo baudrate
    send_ser.close()
    receive_ser.close()
    send_ser.baudrate = new_baudrate
    receive_ser.baudrate = new_baudrate
    time.sleep(0.3)
    send_ser.open()
    receive_ser.open()
    time.sleep(0.3)

    print(f"\n\nBaudrate alterado automaticamente para {new_baudrate}.\n\n")

# Função para redirecionar logs para arquivo
class LogRedirector:
    def __init__(self, file_name, baudrate, num_bytes_to_send):
        self.file = open(file_name, 'w')
        self.terminal = sys.stdout
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = (
            f"{'=' * 50}\n"
            f"Log File: {file_name}\n"
            f"Baudrate: {baudrate}\n"
            f"Start Date: {timestamp}\n"
            f"pkg size: {num_bytes_to_send}\n"
            f"{'=' * 50}\n"
        )
        self.file.write(header)
        self.file.flush()
        self.terminal.write(header)

    def write(self, message):
        self.file.write(message)
        self.file.flush()
        self.terminal.write(message)

    def flush(self):
        self.file.flush()

# Função para registrar logs com timestamp
def log_with_timestamp(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"{timestamp} - {message}"
    print(log_message)

# Função para receber e validar dados na porta serial
def receive_and_validate(ser, num_bytes_to_receive):
    global error_count0, error_count1, consecutive_errors

    try:
        if ser.is_open:  # Verifica se a porta serial está aberta
            received_data = ser.read(num_bytes_to_receive)
        else:
            raise serial.SerialException("Porta serial está fechada.")

        print(f"Dados recebidos em {ser.portstr}: ")

        # Verifica se a quantidade correta de bytes foi recebida
        if len(received_data) != num_bytes_to_receive:
            if ser.portstr == '/dev/ttyUSB0':
                error_count0 += 1
            else:
                error_count1 += 1

            print(f"Erro em {ser.portstr}: Esperado {num_bytes_to_receive} bytes, mas recebido {len(received_data)} bytes.")
            consecutive_errors += 1
            check_and_handle_errors(ser)
            return b'\x00'

        # Validação do checksum
        data = received_data[:-4]
        received_checksum = int.from_bytes(received_data[-4:], byteorder='big')
        calculated_checksum = sum(data)

        if calculated_checksum != received_checksum:
            if ser.portstr == '/dev/ttyUSB0':
                error_count0 += 1
            else:
                error_count1 += 1

            print(f"Erro em {ser.portstr}: Checksum inválido. Calculado {calculated_checksum}, recebido {received_checksum}.")
            consecutive_errors += 1
            check_and_handle_errors(ser)
            return b'\x00'
        else:
            consecutive_errors = 0  # Resetar contador de erros se a validação for bem-sucedida
            log_with_timestamp(f"Sucesso em {ser.portstr}: Calculado {calculated_checksum}, recebido {received_checksum}")
            return b'\x01'

    except serial.SerialException as e:
        log_with_timestamp(f"Erro ao receber dados de {ser.portstr}: {e}")
        consecutive_errors += 1
        check_and_handle_errors(ser)
        return b'\x00'

# Função para sincronizar as portas seriais
def sync_ports(send_ser, receive_ser):
    sync_message = b'\xAA\xBB\xCC\xDD'
    ack_message = b'\xDD\xCC\xBB\xAA'

    print("Sincronizando as portas...")

    try:
        send_ser.write(sync_message)
        print("Sequência de sincronização enviada pela Porta 0.")

        if receive_ser.read(len(sync_message)) == sync_message:
            print("Sequência de sincronização recebida na Porta 1. Enviando confirmação...")
            receive_ser.write(ack_message)

            if send_ser.read(len(ack_message)) == ack_message:
                print("Confirmação recebida na Porta 0. Sincronização completa.")
                return True
            else:
                print("Falha ao receber a confirmação na Porta 0.")
                return False
        else:
            print("Sequência de sincronização incorreta recebida na Porta 1.")
            return False

    except serial.SerialException as e:
        print(f"Erro ao sincronizar as portas seriais: {e}")
        return False

# Função para enviar dados pela porta serial
def send_data(ser, num_bytes_to_send):
    global send_count
    data = [random.randint(0, 31) for _ in range(num_bytes_to_send)]
    checksum = sum(data)
    buffer = list(bytearray(data) + checksum.to_bytes(4, byteorder='big'))

    print(f"Enviando bytes de {ser.portstr} ")
    ser.write(buffer)

# Função para configurar a conexão serial
def setup_serial_connection(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate)
        ser.timeout = 2  # Tempo de timeout para leitura, em segundos
        print(f"Conexão serial estabelecida na porta {port} com baudrate {baudrate}.")
        return ser
    except serial.SerialException as e:
        print(f"Erro ao abrir a porta serial {port}: {e}")
        return None

# Função principal da thread para processar envio e recebimento de dados
def process_port(send_ser, receive_ser, num_bytes_to_send, num_bytes_to_receive, max_data_count, my_event, next_event):
    global send_count
    while True:
        try:
            start_event.wait()  # Espera o sinal de início do programa
            my_event.wait()  # Espera o sinal para esta thread executar
            with send_lock:
                while True:
                    send_data(send_ser, num_bytes_to_send)
                    ack = receive_and_validate(receive_ser, num_bytes_to_receive)

                    if ack == b'\x01':
                        send_count += 1
                        if send_count >= max_data_count:
                            change_baudrate(send_ser, receive_ser)
                            send_count = 0  # Reseta o contador de envios
                        time.sleep(0.1)
                        break  # Sai do loop se o ACK for válido
                    else:
                        print(f'ACK inválido ou erro na porta {receive_ser.portstr}. Tentando novamente...')

                my_event.clear()
                next_event.set()  # Sinaliza a outra thread para executar

        except KeyboardInterrupt:
            print(f"\nPrograma interrompido pelo usuário na porta {send_ser.portstr}.")
            break

# Função para controlar o fluxo principal do programa (start, pause, quit)
def control_loop(send_ser, receive_ser, log_redirector):
    while not exit_event.is_set():
        command = input("Digite 's' para start, 'p' para pause, ou 'q' para sair: \n").strip().lower()
        if command == 's':
            start_event.set()  # Permite que as threads continuem
        elif command == 'p':
            start_event.clear()  # Pausa as threads
        elif command == 'q':
            print("Encerrando o programa...")
            encerramento_de_programa(send_ser, receive_ser, log_redirector)
        else:
            print(f"Comando '{command}' não reconhecido, pausando as threads.")
            start_event.clear()  # Pausa as threads se qualquer outro comando for inserido

# Função para verificar e lidar com erros consecutivos
def check_and_handle_errors(ser):
    global consecutive_errors, max_consecutive_errors

    if consecutive_errors >= max_consecutive_errors:
        print(f"Limite de erros consecutivos atingido ({consecutive_errors}). Encerrando o programa.")
        encerramento_de_programa(ser, None, None)  # Chama o encerramento do programa

# Função para encerrar o programa
def encerramento_de_programa(send_ser, receive_ser, log_redirector):
    time.sleep(0.5)
    start_event.clear()  # Pausa as threads
    time.sleep(2)

    if send_ser:
        print(f'Total de erros identificados na porta {send_ser.portstr}: {error_count0}')
        send_ser.flush()
        time.sleep(0.1)
        send_ser.close()
        print(f"Porta {send_ser.portstr} fechada.")

    if receive_ser:
        print(f'Total de erros identificados na porta {receive_ser.portstr}: {error_count1}')
        receive_ser.flush()
        time.sleep(0.1)
        receive_ser.close()
        print(f"Porta {receive_ser.portstr} fechada.")

    if log_redirector:
        sys.stdout = sys.__stdout__
        log_redirector.file.close()

    sys.exit(0)  # Força o encerramento do programa

# Função principal para configuração e execução do programa
def main():
    port0 = '/dev/ttyUSB0'  # Porta para comunicação 1
    port1 = '/dev/ttyUSB1'  # Porta para comunicação 2
    baudrate = 19200
    num_bytes_to_send = 3000
    num_bytes_to_receive = num_bytes_to_send + 4  # Ajuste para a quantidade total esperada (dados + checksum)
    current_date = datetime.now().strftime('%d-%m-%Y')
    max_data_count = 64  # Define o limite para alterar o baudrate
    log_file_name = f'32-conversor_log_test-{baudrate}-{current_date}.txt'
    log_redirector = LogRedirector(log_file_name, baudrate, num_bytes_to_send)
    sys.stdout = log_redirector

    # Configura as conexões seriais
    send_ser = setup_serial_connection(port0, baudrate)
    receive_ser = setup_serial_connection(port1, baudrate)

    if send_ser is None or receive_ser is None:
        print("Não foi possível estabelecer a conexão serial. Encerrando.")
        return

    try:
        if sync_ports(send_ser, receive_ser):
            print("Comunicação sincronizada com sucesso.")

            # Cria threads para processar cada porta
            thread0 = threading.Thread(
                target=process_port, args=(send_ser, receive_ser, num_bytes_to_send, num_bytes_to_receive, max_data_count, thread0_event, thread1_event))
            thread1 = threading.Thread(
                target=process_port, args=(receive_ser, send_ser, num_bytes_to_send, num_bytes_to_receive, max_data_count, thread1_event, thread0_event))

            thread0_event.set()  # Sinaliza a primeira thread para iniciar

            thread0.start()
            thread1.start()

            control_thread = threading.Thread(target=control_loop, args=(send_ser, receive_ser, log_redirector))
            control_thread.start()

            thread0.join()
            thread1.join()
            control_thread.join()

        else:
            print("Falha na sincronização das portas.")
    except KeyboardInterrupt:
        time.sleep(1)
        print("\nPrograma interrompido pelo usuário.")

if __name__ == "__main__":
    main()

