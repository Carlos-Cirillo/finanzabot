
import sqlite3
import logging
import os  # <-- Import para o caminho do DB
from flask import Flask, request, jsonify
from pyngrok import ngrok  # <-- O "túnel"
import requests            # <-- Para falar com o Telegram
from datetime import date

# --- Configuração ---
ngrok.set_auth_token("35QnfqzIsqoPS4rC0wQmUFcPq7Z_2VzZqDBYa2ba3H3WWck8C")

TOKEN = '8588201244:AAENwNnp0GjAB0WReGZWT7aMoud7KvqLRSw' # <-- Token do Telegram

# Caminho dinâmico para o banco de dados
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(PASTA_ATUAL, 'finanzap.db') # <-- Banco salvo ao lado do app.py

# Configura o 'logging'
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
app = Flask(__name__)
# -----------------------------

# --- [1] LÓGICA DO BANCO DE DADOS (O "CÉREBRO") ---


class GerenciadorBanco:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conexao_banco = None
        self.executor = None

    def __enter__(self):
        self.conexao_banco = sqlite3.connect(self.db_name)
        self.executor = self.conexao_banco.cursor()
        return self.executor
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.conexao_banco.commit()
        else:
            self.conexao_banco.rollback()
            logging.error(f"Erro no banco: {exc_value}")
        self.conexao_banco.close()

def cria_banco(executor):
    """Cria o banco de dados e a tabela transacoes, se não existirem."""
    executor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            data TEXT NOT NULL
        )
    ''')

def adiciona_transacao(executor, tipo, descricao, valor, data):
    """Adiciona uma nova transação ao banco de dados."""
    comando_sql = '''
        INSERT INTO transacoes (tipo, descricao, valor, data)
        VALUES (?, ?, ?, ?)
    '''
    dados_transacao = (tipo, descricao, valor, data)
    executor.execute(comando_sql, dados_transacao)

    return executor.lastrowid # Retorna o ID da nova transação

def listar_transacoes(executor):
    """Retorna todas as transações do banco de dados."""
    comando_sql = 'SELECT * FROM transacoes'
    executor.execute(comando_sql)
    return executor.fetchall()

def listar_transacoes_por_tipo(executor, tipo_procurado):
    """Retorna todas as transações do tipo especificado."""
    comando_sql = 'SELECT * FROM transacoes WHERE tipo = ?'
    executor.execute(comando_sql, (tipo_procurado,))
    return executor.fetchall()

def deletar_transacao_por_id(executor, id_para_deletar):
    """Deleta uma transação do banco de dados pelo seu ID."""
    comando_sql = 'DELETE FROM transacoes WHERE id = ?'
    executor.execute(comando_sql, (id_para_deletar,))
    
    # Retorna o número de linhas afetadas (0 se não achou, 1 se deletou)
    return executor.rowcount

def atualizar_campo_transacao(executor, id_para_atualizar, nome_campo, novo_valor):
    """
    Atualiza um campo específico (ex: 'descricao', 'valor', 'data') 
    de uma transação com base no ID.
    """
    
    if nome_campo not in ['descricao', 'valor', 'data', 'tipo']:
        print(f"Erro: Campo '{nome_campo}' não é permitido para atualização.")
        return
    
    comando_sql = f"UPDATE transacoes SET {nome_campo} = ? WHERE id = ?"
    
    executor.execute(comando_sql, (novo_valor, id_para_atualizar))
    
    if executor.rowcount == 0:
        print(f"Aviso: Nenhuma transação encontrada com o ID {id_para_atualizar}.")
    else:
        print(f"Sucesso: Campo '{nome_campo}' da transação ID {id_para_atualizar} atualizado.")

def limpar_todas_transacoes(executor):
    """Deleta todas as transações do banco de dados e reseta o ID."""
    comando_sql = 'DELETE FROM transacoes'
    executor.execute(comando_sql)
    executor.execute("DELETE FROM sqlite_sequence WHERE name='transacoes'")
    print("Todas as transações foram deletadas e o ID resetado.")

# --- FUNÇÕES DE CÁLCULO E LÓGICA ---

def calcular_saldo(executor):
    """Calcula e retorna o saldo total de receitas, despesas e o saldo líquido."""
    
    #1. Calcular total de receitas
    executor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo = ?", ('receita',))
    resultado_receitas = executor.fetchone()[0]
    total_receitas = resultado_receitas if resultado_receitas is not None else 0.0

    #2. Calcular total de despesas
    executor.execute("SELECT SUM(valor) FROM transacoes WHERE tipo = ?", ('despesa',))
    resultado_despesas = executor.fetchone()[0]
    total_despesas = resultado_despesas if resultado_despesas is not None else 0.0

    #3. Calcular saldo líquido
    saldo_liquido = total_receitas - total_despesas
    return total_receitas, total_despesas, saldo_liquido

def calcular_saldo_periodo(executor, data_inicio, data_fim):
    """Calcula o saldo total de receitas, despesas e o saldo líquido em um período específico."""
    
    #1. Calcular total de receitas no período
    sql_receitas = '''SELECT SUM(valor) FROM transacoes WHERE tipo = 'receita' AND data BETWEEN ? AND ?'''
    executor.execute(sql_receitas, (data_inicio, data_fim))
    resultado_receitas = executor.fetchone()[0]
    total_receitas = resultado_receitas if resultado_receitas is not None else 0.0

    #2. Calcular total de despesas no período
    sql_despesas = '''SELECT SUM(valor) FROM transacoes WHERE tipo = 'despesa' AND data BETWEEN ? AND ?'''
    executor.execute(sql_despesas, (data_inicio, data_fim))
    resultado_despesas = executor.fetchone()[0]
    total_despesas = resultado_despesas if resultado_despesas is not None else 0.0

    #3. Calcular saldo líquido no período
    saldo_liquido = total_receitas - total_despesas
    return total_receitas, total_despesas, saldo_liquido

# -----------------------------

# --- [2] O "OUVINTE" (API / WEBHOOK) ---

# Rota de teste 
@app.route('/')
def home():
    return "API do Bot Finanza está no ar!"


@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def telegram_webhook():
    if request.json:
        update = request.json
        logging.info("Mensagem recebida do Telegram!")
        
        try:
            # 1. Filtra qualquer coisa que não seja uma mensagem de texto
            if 'message' not in update or 'text' not in update['message']:
                logging.info("Update ignorado (não é mensagem de texto).")
                return jsonify({"status": "ok"}), 200 # Avisa ao Telegram que está OK

            # 2. Se chegou aqui, é seguro ler
            chat_id = update['message']['chat']['id']
            texto = update['message']['text'].strip()
            logging.info(f"Chat ID: {chat_id} | Texto: {texto}")
            
        except Exception as e:
            logging.error(f"Erro inesperado ao ler a mensagem: {e}")
            return jsonify({"status": "erro"}), 400

        # --- LÓGICA PRINCIPAL DO BOT ---
        
        resposta = "Desculpe, não entendi. Envie /ajuda para ver os comandos."
        
        if texto == '/start' or texto == '/ajuda':
            resposta = (
                "Olá! 👋 Bem-vindo ao seu Bot de Finanças.\n"
                "Aqui estão os comandos:\n"
                "/listar - Lista todas as transações\n"
                "/saldo - Mostra o saldo total\n"
                "/add [tipo] [valor] [desc] (ex: /add despesa 50 mercado)"
                "\n/del [ID] - Deleta a transação pelo ID"
            )

        elif texto == '/listar':
            try:
                with GerenciadorBanco(DB_NAME) as executor:
                    transacoes = listar_transacoes(executor)
                if not transacoes:
                    resposta = "Nenhuma transação encontrada."
                else:
                    resposta = "--- Suas Transações ---\n"
                    for t in transacoes:
                        resposta += f"ID {t[0]}: {t[4]} | {t[2]} | R$ {t[3]:.2f} ({t[1]})\n"
            except Exception as e:
                resposta = f"Erro ao buscar transações: {e}"
        
        elif texto.startswith('/del'):
            try:
                # Pega o ID (ex: "/del 1" -> "1")
                id_para_deletar = int(texto.split(' ')[1])
                
                with GerenciadorBanco(DB_NAME) as executor:
                    linhas_afetadas = deletar_transacao_por_id(executor, id_para_deletar)
                
                if linhas_afetadas == 0:
                    resposta = f"⚠️ Erro: Nenhuma transação encontrada com o ID {id_para_deletar}."
                else:
                    resposta = f"🗑️ Sucesso! Transação ID {id_para_deletar} foi deletada."
            
            except Exception as e:
                logging.error(f"Erro ao deletar: {e}")
                resposta = (
                    "Erro ao deletar. 😥\n"
                    "Verifique o formato: /del [ID]\n"
                    "Exemplo: /del 1"
                )

        elif texto == '/saldo':
            try:
                with GerenciadorBanco(DB_NAME) as executor:
                    r, d, s = calcular_saldo(executor)
                resposta = (
                    f"--- Balanço Total ---\n"
                    f"✅ Receitas: R$ {r:.2f}\n"
                    f"❌ Despesas: R$ {d:.2f}\n"
                    f"-----------------------\n"
                    f"💰 Saldo: R$ {s:.2f}"
                )
            except Exception as e:
                resposta = f"Erro ao calcular saldo: {e}"
        
        elif texto.startswith('/add'):
            # Exemplo de comando: /add despesa 50 mercado
            try:
                partes = texto.split(' ', 3) # Quebra o comando em 4 partes
                tipo = partes[1].lower()     # 'despesa'
                valor = float(partes[2])   # 50
                descricao = partes[3]      # 'mercado'
                data_hoje = date.today().strftime("%Y-%m-%d")

                if tipo not in ['receita', 'despesa']:
                    resposta = "Erro: tipo inválido. Use 'receita' ou 'despesa'."
                else:
                    with GerenciadorBanco(DB_NAME) as executor:
                        novo_id = adiciona_transacao(executor, tipo, descricao, valor, data_hoje)
                    resposta = f"✅ Sucesso! {tipo.capitalize()}: {descricao} (R$ {valor:.2f}). Adicionado!"
            
            except Exception as e:
                resposta = (
                    "Erro ao adicionar. 😥\n"
                    "Verifique o formato: /add [tipo] [valor] [descrição]\n"
                    "Exemplo: /add despesa 50 mercado"
                )

        # Envia a resposta de volta para o usuário
        enviar_mensagem_telegram(chat_id, resposta)

        
        
    return jsonify({"status": "ok"}), 200


# Função helper para enviar a mensagem de volta
def enviar_mensagem_telegram(chat_id, texto):
    """Envia uma mensagem de volta ao chat do Telegram."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto
    }
    try:
        requests.post(url, json=payload)
        logging.info("Resposta enviada ao Telegram.")
    except Exception as e:
        logging.error(f"Erro ao enviar resposta: {e}")

# -----------------------------

# --- [3] O (MAIN) ---

def main():
    # 0. Garante que o banco exista antes de tudo
    logging.info("Verificando banco de dados...")
    with GerenciadorBanco(DB_NAME) as executor:
        cria_banco(executor)
    logging.info("Banco de dados OK.")

    # 1. Inicia o 'ngrok' e pega a URL pública
    logging.info("Iniciando ngrok...")
    
    # --- A CORREÇÃO ESTÁ AQUI ---
    # Primeiro, criamos o túnel (o objeto)
    tunnel = ngrok.connect(5000)
    # Agora, pegamos SÓ o link (a string) de dentro dele
    public_url = tunnel.public_url 
    # --- FIM DA CORREÇÃO ---
    
    logging.info(f"URL Pública (ngrok): {public_url}") # Agora o log vai mostrar só o link

    # 2. Registra o Webhook no Telegram
    webhook_url = f"{public_url}/webhook/{TOKEN}"
    set_webhook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    
    response = requests.get(set_webhook_url)
    if response.json().get('ok'):
        logging.info("Webhook registrado com sucesso no Telegram!")
    else:
        logging.error(f"Falha ao registrar webhook: {response.json()}")

    # 3. Roda o servidor Flask
    logging.info("Iniciando servidor Flask...")
    app.run(host="0.0.0.0", port=5000)
if __name__ == '__main__':
    main()