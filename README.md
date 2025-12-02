FinanzaBot: Sistema de Gestão Financeira via API + Telegram
Visão Geral do Projeto
O FinanzaBot é uma implementação completa de um sistema de controle financeiro pessoal (Receitas e Despesas). Seu objetivo primário é demonstrar proficiência na construção de um Backend robusto que se comunica via Webhooks, simulando uma arquitetura de microsserviços.
O usuário interage com o sistema exclusivamente através do Telegram, e o servidor Flask manipula a lógica de negócio e o banco de dados.

⚙️ Stack Tecnológico Principal
Linguagem: Python 3.x
Servidor/API: Flask
Comunicação: Telegram Bot API (Webhooks)
Gerenciamento de Dados: SQLite (persistência em arquivo .db)
Ferramentas: pyngrok (para exposição da API em ambiente local)

🧠 Destaques de Arquitetura
Arquitetura Webhook (API-Driven): O projeto utiliza o Flask para atuar como um Listener (Ouvinte) que recebe requisições POST diretamente do servidor do Telegram, eliminando a necessidade de "polling" (consultas ativas).
Gerenciamento de Estado (State Management): O comando /add é implementado com um sistema de memória (in-memory dictionary), permitindo que o bot mantenha o estado da conversa com o usuário (AGUARDANDO_TIPO, AGUARDANDO_VALOR, etc.), o que é essencial para interfaces conversacionais.
Transações Seguras: O gerenciamento da conexão com o SQLite é encapsulado na classe GerenciadorBanco (Context Manager), garantindo que as operações de COMMIT (salvar) e CLOSE (fechar) sejam executadas automaticamente, mesmo em caso de erro (ROLLBACK).
Separação de Preocupações: O código é modularizado. O Servidor (Flask) é separado das Funções de Banco (CRUD), o que facilita a manutenção e futura expansão (por exemplo, migrando para PostgreSQL).

📄 Descrição das Funcionalidades do Bot
O projeto FinanzaBot demonstra a capacidade de gerenciar um banco de dados de forma conversacional, com as seguintes funcionalidades ativas via Telegram:
Criação de Transações (Comando /add)
Função: Inicia um fluxo de conversa interativa para registrar novas receitas ou despesas.
Destaque Técnico: Utiliza Gerenciamento de Estado (State Management) para lembrar o que o usuário está digitando (primeiro o tipo, depois o valor, depois a descrição).
Consulta de Transações (Comando /listar)
Função: Busca e exibe todas as transações salvas no banco de dados, mostrando ID, data, descrição, valor e tipo.
Relatório de Saldo (Comando /saldo)
Função: Calcula e exibe o saldo líquido total do usuário (Soma de Receitas - Soma de Despesas).
Deleção de Transações (Comando /del [ID])
Função: Permite remover permanentemente uma transação específica do banco de dados, utilizando o ID como identificador único.
Gerenciamento de Erros e Conexão
Função: A classe GerenciadorBanco garante que a conexão com o SQLite seja fechada e que as alterações sejam salvas (COMMIT) ou desfeitas (ROLLBACK) automaticamente, mantendo a integridade dos dados sob todas as condições.
