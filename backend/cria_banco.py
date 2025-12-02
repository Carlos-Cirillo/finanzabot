import os
import sqlite3
from datetime import date

# --- CONFIGURAÇÃO GLOBAL ---
Pasta_ATUAL = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(Pasta_ATUAL, 'finanza.db')

# --- GERENCIADOR DE CONEXÃO ---

class GerenciadorBanco:
    """Classe para gereciar a conexão com o banco de dados SQLite.
    Ela cuida automaticamente de connect, commit, rollback e close."""

    def __init__(self, db_name):
        self.db_name = db_name
        self.conexao_banco = None
        self.executor = None

    def __enter__(self):
        """Abre a conexão com o banco de dados e retorna o cursor."""
        self.conexao_banco = sqlite3.connect(self.db_name)
        self.executor = self.conexao_banco.cursor()
        return self.executor
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Fecha a conexão com o banco de dados, fazendo commit ou rollback conforme necessário."""
        if exc_type is None:
            self.conexao_banco.commit()
        else:
            self.conexao_banco.rollback()
            print(f"Erro ocorrido: {exc_value}")

        self.conexao_banco.close()
        return False

# --- FUNÇÕES DE OPERAÇÃO DO BANCO (CRUD) ---

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

    if executor.rowcount == 0:
        print(f"Nenhuma transação encontrada com ID {id_para_deletar}.")
    else:
        print(f"Transação com ID {id_para_deletar} deletada com sucesso.")

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

# --- FUNÇÃO PRINCIPAL (MENU DA APLICAÇÃO) ---

def main():
    """Função principal que executa o menu interativo."""
    
    with GerenciadorBanco(DB_NAME) as executor:
        cria_banco(executor)

    while True:
        print("\n--- Menu Principal Finanza ---")
        print("1. Adicionar Transação")
        print("2. Listar Todas as Transações")
        print("3. Atualizar Transação (por ID)")
        print("4. Deletar Transação (por ID)")
        print("5. Ver saldo total")
        print("6. Calcular saldo por período")
        print("7. Limpar todas as transações")
        print("0. Sair")
        
        escolha = input("Digite sua escolha: ")

        if escolha == '0':
            print("\nSaindo... Até mais!")
            break

        elif escolha == '1':
            print("\n--- Adicionar Nova Transação ---")

            # --- MUDANÇA AQUI ---
            print("Selecione o tipo da transação:")
            print("1. Receita")
            print("2. Despesa")
            escolha_tipo = input("Digite 1 ou 2: ")

            if escolha_tipo == '1':
                tipo = 'receita'
            elif escolha_tipo == '2':
                tipo = 'despesa'
            else:
                print("Erro: Opção de tipo inválida. Transação cancelada.")
                input("\nPressione Enter para voltar ao menu...")
                continue # Volta ao menu principal
            # --- FIM DA MUDANÇA ---

            descricao = input(f"Descrição da {tipo}: ")
            
            # (O seu código da data automática vem aqui)
            data_hoje = date.today()
            data = data_hoje.strftime("%Y-%m-%d")
            print(f"Data registrada automaticamente: {data}")
            
            # (O seu código do valor vem aqui)
            try:
                valor = float(input(f"Valor da {tipo}: R$ "))
            except ValueError:
                print("Erro: Valor inválido. Deve ser um número. Transação cancelada.")
                input("\nPressione Enter para voltar ao menu...")
                continue 
            
            # (O resto do código 'try...with' para adicionar)
            try:
                with GerenciadorBanco(DB_NAME) as executor:
                    adiciona_transacao(executor, tipo, descricao, valor, data)
                print("\nSucesso! Transação adicionada.")
            
            except sqlite3.Error as e:
                print(f"\nErro ao adicionar transação: {e}")
            
            input("\nPressione Enter para voltar ao menu...")
        
        elif escolha == '2':
            print("\n--- Todas as Transações ---")
            
            with GerenciadorBanco(DB_NAME) as executor:
                transacoes = listar_transacoes(executor)
            
            if not transacoes:
                print("Nenhuma transação encontrada.")
            else:
                for t in transacoes:
                    print(f"ID: {t[0]} | Tipo: {t[1]} | Data: {t[4]} | Desc: {t[2]} | Valor: R$ {t[3]:.2f}")
            
            input("\nPressione Enter para voltar ao menu...")

        elif escolha == '3':
            print("\n--- Atualizar Transação ---")
            
            # 1. Pedir e validar o ID
            try:
                id_para_atualizar = int(input("Digite o ID da transação que deseja atualizar: "))
            except ValueError:
                print("Erro: ID inválido. Deve ser um número. Operação cancelada.")
                input("\nPressione Enter para voltar ao menu...")
                continue # Volta ao menu

            # 2. Mostrar o Sub-Menu
            print("\nO que você deseja atualizar nesta transação?")
            print("1. Descrição")
            print("2. Valor")
            print("3. Data")
            print("4. Tipo (receita/despesa)")
            print("0. Cancelar")
            
            sub_escolha = input("Digite sua escolha: ")

            # 3. Processar a sub-escolha
            
            if sub_escolha == '0':
                print("Operação cancelada.")
                continue # Volta ao menu principal

            elif sub_escolha == '1':
                nome_campo = 'descricao'
                novo_valor = input("Digite a NOVA descrição: ")
            
            elif sub_escolha == '2':
                nome_campo = 'valor'
                try:
                    novo_valor = float(input("Digite o NOVO valor: R$ "))
                except ValueError:
                    print("Erro: Valor inválido.")
                    input("\nPressione Enter para voltar ao menu...")
                    continue
            
            elif sub_escolha == '3':
                nome_campo = 'data'
                novo_valor = input("Digite a NOVA data (AAAA-MM-DD): ")
            
            elif sub_escolha == '4':
                nome_campo = 'tipo'
                print("Selecione o NOVO tipo:")
                print("1. Receita")
                print("2. Despesa")
                escolha_tipo_novo = input("Digite 1 ou 2: ")

                if escolha_tipo_novo == '1':
                    novo_valor = 'receita'
                elif escolha_tipo_novo == '2':
                    novo_valor = 'despesa'
                else:
                    print("Erro: Opção de tipo inválida. Operação cancelada.")
                    input("\nPressione Enter para voltar ao menu...")
                    continue
            
            else:
                print("Opção inválida. Operação cancelada.")
                input("\nPressione Enter para voltar ao menu...")
                continue

            # 4. Chamar a nova função do banco
            try:
                with GerenciadorBanco(DB_NAME) as executor:
                    atualizar_campo_transacao(executor, id_para_atualizar, nome_campo, novo_valor)
            
            except sqlite3.Error as e:
                print(f"\nErro ao atualizar transação: {e}")
            
            input("\nPressione Enter para voltar ao menu...")
        
        elif escolha == '4':
            print("\n--- Deletar Transação ---")

            try:
                id_para_deletar = int(input("ID da transação a ser deletada: "))
            except ValueError:
                print("Erro: ID inválido. Deve ser um número inteiro.")
                input("\nPressione Enter para voltar ao menu...")
                continue

            try:
                with GerenciadorBanco(DB_NAME) as executor:
                    deletar_transacao_por_id(executor, id_para_deletar)

            except sqlite3.Error as e:
                print(f"\nErro ao deletar transação: {e}")

            input("\nPressione Enter para voltar ao menu...")

        elif escolha == '5':
            print("\n--- Saldo Total ---")
            try:
                with GerenciadorBanco(DB_NAME) as executor:
                    total_receitas, total_despesas, saldo_liquido = calcular_saldo(executor)
                
                print(f"Total de Receitas: R$ {total_receitas:.2f}")
                print(f"Total de Despesas: R$ {total_despesas:.2f}")
                print(f"Saldo Líquido: R$ {saldo_liquido:.2f}")

            except sqlite3.Error as e:
                print(f"\nErro ao calcular saldo: {e}")

            input("\nPressione Enter para voltar ao menu...")

        elif escolha == '6':
            print("\n--- Calcular Saldo em Período ---")
            data_inicio = input("Data de Início (AAAA-MM-DD): ")
            data_fim = input("Data de Fim (AAAA-MM-DD): ")

            try:
                with GerenciadorBanco(DB_NAME) as executor:
                    total_receitas, total_despesas, saldo_liquido = calcular_saldo_periodo(executor, data_inicio, data_fim)
                print(f"Total de Receitas no Período: R$ {total_receitas:.2f}")
                print(f"Total de Despesas no Período: R$ {total_despesas:.2f}")
                print('-------------------------------------')
                print(f"Saldo Líquido no Período: R$ {saldo_liquido:.2f}")

            except sqlite3.Error as e:
                print(f"\nErro ao calcular saldo no período: {e}")

            input("\nPressione Enter para voltar ao menu...")

        elif escolha == '7':
            print("\n--- Limpar Todas as Transações ---")
            confirmacao = input("Tem certeza que deseja deletar todas as transações? (s/n): ").lower()
            if confirmacao == 's':
                try:
                    with GerenciadorBanco(DB_NAME) as executor:
                        limpar_todas_transacoes(executor)
                except sqlite3.Error as e:
                    print(f"\nErro ao limpar transações: {e}")
            else:
                print("Operação cancelada.")

            input("\nPressione Enter para voltar ao menu...")

        else:
            print("\nOpção inválida. Tente novamente.")

# --- PONTO DE ENTRADA DA APLICAÇÃO ---

if __name__ == '__main__':
    main()