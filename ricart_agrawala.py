# Authors
# Daniel Liberato de Jesus - 552127
# Gustavo Eda - 620114
from random import *
import socket
import string
import thread
import pickle
import sys
import signal
import time

class Processo:

    def __init__(self, incremento_clock, id):
        self.clock_processo = incremento_clock
        self.id = id
        self.incremento_clock = incremento_clock
        self.ok = 0
        self.vetor_msg = []
        self.usando_recurso = False
        self.requisitando_recurso = False

    def incrementa_clock(self):
        self.clock_processo += self.incremento_clock

    def recebe_msg(self, msg):

        # Valida clock
        if msg.clock_msg > self.clock_processo:
            self.clock_processo = msg.clock_msg + 1

        # Se o processo atual nao pretend usar OU nao estiver usando entao envia OK ao remetente
        if not (self.usando_recurso | self.requisitando_recurso):
			self.envia_ok(msg.id_processo, True)

        # Senao se o processo estiver usando o recurso, insere a mensagem no vetor e ordena pelo ID e pelo Clock
        elif self.usando_recurso:
            self.vetor_msg.insert(len(self.vetor_msg), msg)
            self.vetor_msg = sorted(self.vetor_msg, key = Mensagem.get_id)
            self.vetor_msg = sorted(self.vetor_msg, key = Mensagem.get_clock)
            self.envia_ok(msg.id_processo, False)

        # Senao se o processo estiver requisitando o recurso 
        elif self.requisitando_recurso:

            # Se a requisicao for do proprio processo, insere a propria requisicao
            if not self.vetor_msg:
                self.vetor_msg.insert(len(self.vetor_msg), msg)

			# senao, envia os OK para quem requisitou
            elif msg.clock_msg < self.vetor_msg[0].clock_msg:
                self.envia_ok(msg.id_processo, True)
            else:
                self.envia_ok(msg.id_processo, False)

                self.vetor_msg.insert(len(self.vetor_msg), msg)

                self.vetor_msg = sorted(self.vetor_msg, key = Mensagem.get_id)
                self.vetor_msg = sorted(self.vetor_msg, key = Mensagem.get_clock)

	# recebe os OK, se tiver 3 OKs permite o uso do recurso
    def recebe_ok(self, msg):

        if msg.resposta:

            self.ok += 1

            if self.ok == 3:
                self.usa_recurso()
                self.remove_msg()


    # Definicao do metodo que requisita o recurso
    def requisita_recurso(self):

        print 'Clock:',self.clock_processo,'\tProcesso', self.id, 'requisita o recurso'
        self.requisitando_recurso = True
        self.ok = 1
        self.envia_msg()

    # Remove a propria requisicao e envia OK para todas as requisicoes do vetor
    def remove_msg(self):

        del self.vetor_msg[0]
        self.ok = 0

        while len(self.vetor_msg) != 0:
            self.envia_ok(self.vetor_msg[0].id_processo, True)
            del self.vetor_msg[0]


    def usa_recurso(self):
        print 'Clock:',self.clock_processo,'\tProcesso', self.id, 'esta usando o recurso!'
        self.usando_recurso = True

        time.sleep(5)

        print 'Clock:',self.clock_processo,'\tProcesso', self.id, 'liberou o recurso!'
        self.usando_recurso = False
        self.requisitando_recurso = False

    def cria_msg(self):
        clock_msg = self.clock_processo 
        mensagem = Mensagem(clock_msg, str(self.clock_processo) + str(self.id), self.id)

        return mensagem

    # Envia OK ao remetente
    def envia_ok(self, id, recurso):

        if not recurso:
            print 'Clock:',self.clock_processo,'\tPermissao negada ao processo', id
        else:
            print 'Clock:',self.clock_processo,'\tEnviando OK para o processo:', id

        meu_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = ('localhost', 3000 + id)
        meu_socket.connect(server_address)

        ok = Ok(recurso, id)
        ok_codificado = pickle.dumps(ok)
        meu_socket.send(ok_codificado)
        meu_socket.close()

    # Gera uma mensagem aleatoria e envia para todas as portas
    def envia_msg(self):

        mensagem = self.cria_msg()

        for i in range(0,3):

            meu_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_address = ('localhost', 3000 + i)
            meu_socket.connect(server_address)


            mensagem_codificada = pickle.dumps(mensagem)
            meu_socket.send(mensagem_codificada)
            meu_socket.close()

class Mensagem:
    def __init__(self, clock_msg, id, id_processo):
        self.clock_msg = clock_msg
        self.id = id
        self.id_processo = id_processo

    def get_clock(self):
        return self.clock_msg

    def get_id(self):
        return self.id

class Ok:
    def __init__(self, resposta, id):
        self.resposta = resposta
        self.id = id

#cria o socket de server, e fica ouvindo o meio
def thread_recebe():
    global processo

    while True:
        serverPort = int(sys.argv[1])

        serverSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

        try:

            serverSocket.bind(('',serverPort))
            serverSocket.listen(1)

            while True:

                connectionSocket, addr = serverSocket.accept()

                try:

                    data = connectionSocket.recv(1024)
                    decodificada = pickle.loads(data)

                    if isinstance(decodificada, (Mensagem)):
                        processo.recebe_msg(decodificada)

                    elif isinstance(decodificada, (Ok)):
                        processo.recebe_ok(decodificada)

                except Exception as e:
                    print 'Erro ao receber:', e

        except Exception as e:
            print 'Erro ao abrir o socket:', e
            time.sleep(5)

# Requisita recurso m intervalos aleatorios
def thread_gera():
    global processo

    while True:

        time.sleep(randint(1,3))

        try:
            if not (processo.requisitando_recurso | processo.usando_recurso):
                processo.requisita_recurso()

        except Exception as e:
        	print 'Erro ao enviar', e
        
def thread_clock():
    global processo

    while True:
        processo.incrementa_clock()

        time.sleep(2)

processo = Processo(randint(0,9), int(sys.argv[2]))
print 'Processo:', sys.argv[2]

def main():
    PORT = sys.argv[1]
    thread.start_new_thread(thread_recebe, ())
    time.sleep(5)
    thread.start_new_thread(thread_gera, ())
    thread.start_new_thread(thread_clock, ())

    signal.pause()

if __name__ == "__main__":
    sys.exit(main())
