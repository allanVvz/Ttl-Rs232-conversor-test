import time
import serial
import random
import threading
import sys
from datetime import datetime

# Variáveis globais para contagem de erros
error_count0 = 0
error_count1 = 0
# Variáveis globais para controle de início e pausa
start_event = threading.Event()
exit_event = threading.Event()  # Evento para controlar a saída do programa

class LogRedirector:
    def __init__(self, file_name, baudrate, num_bytes_to_send):
        self.file = open(file_name, 'w')
        self.terminal = sys.stdout

        # Adiciona um cabeçalho ao arquivo de log
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = (
            f"{'=' * 50}\n"
            f"Log File: {file_name}\n"
            f"Baudrate: {baudrate}\n"
            f"Start Date: {timestamp}\n"
            f"pkg size: {num_bytes_to_send}\n"
            f"{'='*50}\n"
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

def log_with_timestamp(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"{timestamp} - {message}"
    print(log_message)

def receive_and_validate(ser, num_bytes_to_receive):
    global error_count0, error_count1

    try:
        received_data = list(ser.read(num_bytes_to_receive))
        print(f"Dados recebidos em {ser.portstr}: ", end="")
        print(", ".join(f"{byte}" for byte in received_data))

        # Verificar se a quantidade correta de bytes foi recebida
        if len(received_data) != num_bytes_to_receive:
            if ser.portstr == '/dev/ttyUSB0':
                error_count0 += 1
            else:
                error_count1 += 1
            print(f"Erro em {ser.portstr}: Esperado {num_bytes_to_receive} bytes, mas recebido {len(received_data)} bytes.")
            return b'\x00'

        # Separar o checksum dos dados
        data = received_data[:-4]
        received_checksum = int.from_bytes(received_data[-4:], byteorder='big')

        calculated_checksum = sum(data)

        # Validar o checksum
        if calculated_checksum != received_checksum:
            if ser.portstr == '/dev/ttyUSB0':
                error_count0 += 1
            else:
                error_count1 += 1
            print(f" \n\n Erro em {ser.portstr}: Checksum inválido. Calculado {calculated_checksum}, recebido {received_checksum}. \n\n ")
            return b'\x00'
        else:
            log_with_timestamp(f"Sucesso em {ser.portstr}: Calculado {calculated_checksum}, recebido {received_checksum}\n")
            return b'\x01'

    except serial.SerialException as e:
        log_with_timestamp(f"Erro ao receber dados de {ser.portstr}: {e}")
        return b'\x00'

def sync_ports(ser0, ser1):
    sync_message = b'\xAA\xBB\xCC\xDD'
    ack_message = b'\xDD\xCC\xBB\xAA'

    print("Sincronizando as portas...")

    try:
        # Porta 0 envia a sequência de sincronização para a Porta 1
        ser0.write(sync_message)
        print("Sequência de sincronização enviada pela Porta 0.")

        # Porta 1 espera e confirma a sequência de sincronização
        if ser1.read(len(sync_message)) == sync_message:
            print("Sequência de sincronização recebida na Porta 1. Enviando confirmação...")
            ser1.write(ack_message)

            # Porta 0 espera pela confirmação da Porta 1
            if ser0.read(len(ack_message)) == ack_message:
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

def send_data(ser, num_bytes_to_send):
    # Gerar dados aleatórios
    data = [random.randint(0, 31) for _ in range(num_bytes_to_send)]

    # Calcular o checksum
    checksum = sum(data)

    # Criar buffer com os dados e o checksum (4 bytes para checksum)
    buffer = list(bytearray(data) + checksum.to_bytes(4, byteorder='big'))

    # Exibir os dados e o checksum para debug
    print(f"Enviando bytes de {ser.portstr}: ", end="")
    print(", ".join(f"{byte}" for byte in buffer))
    #print(f"Checksum: {checksum}\n")

    # Enviar os dados pela porta serial
    ser.write(buffer)

def setup_serial_connection(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate)
        ser.timeout = 2  # Tempo de timeout para leitura, em segundos
        print(f"Conexão serial estabelecida na porta {port} com baudrate {baudrate}.")
        return ser
    except serial.SerialException as e:
        print(f"Erro ao abrir a porta serial {port}: {e}")
        return None

# Lock para controlar o envio de dados
send_lock = threading.Lock()

def process_port(send_ser, receive_ser, num_bytes_to_send, num_bytes_to_receive):
    while True:
        try:
            start_event.wait()
            with send_lock:
                send_data(send_ser, num_bytes_to_send)
                #print(f'Dados enviados na porta {send_ser.portstr}. Aguardando ACK...')

                # Recebe e valida os dados
                ack = receive_and_validate(receive_ser, num_bytes_to_receive)

                # Verifica se o ACK é válido
                while ack != b'\x01':
                    print(f'ACK inválido ou erro na porta {receive_ser.portstr}. Tentando novamente...')
                    send_data(send_ser, num_bytes_to_send)
                    ack = receive_and_validate(receive_ser, num_bytes_to_receive)

                #print(f'ACK recebido corretamente na porta {receive_ser.portstr}.')

            # Espera para o próximo ciclo
            time.sleep(0.01)

        except KeyboardInterrupt:
            print(f"\nPrograma interrompido pelo usuário na porta {send_ser.portstr}.")
            break

def control_loop(ser0, ser1, log_redirector):
    while not exit_event.is_set():
        command = input("Digite 's' para start, 'p' para pause, ou 'q' para sair: ").strip().lower()
        if command == 's':
            start_event.set()  # Permite que as threads continuem
        elif command == 'p':
            start_event.clear()  # Pausa as threads
        elif command == 'q':
            print("Encerrando o programa...")
            encerramento_de_programa(ser0, ser1, log_redirector)
        else:
            print(f"Comando '{command}' não reconhecido, pausando as threads.")
            start_event.clear()  # Pausa as threads se qualquer outro comando for inserido


def encerramento_de_programa(ser0, ser1, log_redirector):
    time.sleep(0.5)
    start_event.clear()  # Pausa as threads
    time.sleep(2)

    print(f'Total de erros identificados na porta {ser0.portstr}: {error_count0}')
    print(f'Total de erros identificados na porta {ser1.portstr}: {error_count1}')

    # Garante que todos os dados foram enviados antes de fechar
    ser0.flush()  # Garante que todos os dados foram enviados
    time.sleep(0.1)  # Espera um pouco após flush
    ser0.close()  # Fecha a porta serial
    print(f"Porta {ser0.portstr} fechada.")

    ser1.flush()  # Garante que todos os dados foram enviados
    time.sleep(0.1)  # Espera um pouco após flush
    ser1.close()  # Fecha a porta serial
    print(f"Porta {ser1.portstr} fechada.")

    sys.stdout = sys.__stdout__
    log_redirector.file.close()
    sys.exit(0)  # Força o encerramento do programa


def main():
    port0 = '/dev/ttyUSB0'  # Porta para comunicação 1
    port1 = '/dev/ttyUSB1'  # Porta para comunicação 2
    baudrate = 921600
    num_bytes_to_send = 3000
    num_bytes_to_receive = num_bytes_to_send + 4  # Ajuste para a quantidade total esperada (dados + checksum)
    current_date = datetime.now().strftime('%d-%m-%Y')
    log_file_name = f'OLD - conversor_log_test-{baudrate}-{current_date}.txt'
    log_redirector = LogRedirector(log_file_name, baudrate, num_bytes_to_send)
    sys.stdout = log_redirector

    # Configura as conexões seriais
    ser0 = setup_serial_connection(port0, baudrate)
    ser1 = setup_serial_connection(port1, baudrate)

    if ser0 is None or ser1 is None:
        print("Não foi possível estabelecer a conexão serial. Encerrando.")
        return

    try:
        if sync_ports(ser0, ser1):
            print("Comunicação sincronizada com sucesso.")

            # Cria threads para processar cada porta
            thread0 = threading.Thread(
                target=lambda: process_port(ser0, ser1, num_bytes_to_send, num_bytes_to_receive))
            thread1 = threading.Thread(
                target=lambda: process_port(ser1, ser0, num_bytes_to_send, num_bytes_to_receive))

            thread0.start()
            thread1.start()

            control_thread = threading.Thread(target=control_loop, args=(ser0, ser1, log_redirector))
            control_thread.start()

            thread0.join()
            thread1.join()
            control_thread.join()

        else:
            print("Falha na sincronização das portas.")
    except KeyboardInterrupt:
        time.sleep(2)
        print("\nPrograma interrompido pelo usuário.")



if __name__ == "__main__":
    main()

