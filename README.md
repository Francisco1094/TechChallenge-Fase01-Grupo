# Tech Challenge - Fase 01

Projeto de web scraping com API REST para coleta e análise de dados de livros.

## Executando o projeto

### Preparação do ambiente

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### Execução

```bash
uvicorn api.main:app --reload
```

A API estará disponível em: http://127.0.0.1:8000

Documentação interativa: http://127.0.0.1:8000/docs

## Autenticação

Para endpoints que requerem autenticação:
- Usuario: user1
- Senha: password1

## Principais endpoints

- `/api/v1/health` - Verificar status da API
- `/api/v1/books` - Listar livros
- `/api/v1/books/search` - Buscar por título ou categoria
- `/api/v1/books/{id}` - Buscar livro específico
- `/api/v1/category` - Listar categorias disponíveis
- `/api/v1/scrape` - Executar scraping (requer autenticação)
- `/api/v1/auth/login` - Realizar login
- `/api/v1/stats/overview` - Estatísticas dos dados

## Funcionalidades de Machine Learning

O sistema possui endpoints para análise preditiva baseada nos dados coletados:
- `/api/v1/ml/features` - Gerar features para ML
- `/api/v1/ml/training-data` - Obter dados de treinamento
- `/api/v1/ml/predictions` - Fazer predições

## Sistema de Monitoramento

A aplicação possui monitoramento completo com logs estruturados e métricas de performance.

### Endpoints de monitoramento

- `/api/v1/monitoring/metrics` - Métricas no formato Prometheus
- `/api/v1/monitoring/dashboard` - Dados para dashboard (JSON)

### Tipos de logs

O sistema registra 4 tipos de eventos em logs estruturados JSON:

**1. HTTP Request Logs**
- Todas as requisições HTTP (método, endpoint, status, tempo de resposta)
- User-agent, IP, duração em ms
- Exemplo: `GET /api/v1/books - 200 - 45.2ms`

**2. Business Event Logs** 
- Eventos importantes do negócio (login, scraping, ML predictions)
- Contexto específico de cada evento
- Exemplo: `user_login_attempt`, `scraping_started`, `ml_prediction_made`

**3. Error Logs**
- Erros e exceções da aplicação
- Stack trace e contexto do erro
- Exemplo: `AttributeError: module has no attribute 'method'`

**4. System Metrics**
- Métricas de sistema (CPU, memória, disco)
- Coletadas automaticamente via Prometheus
- Atualizadas em tempo real

### Arquivos de log

- `logs/app.log` - Logs estruturados em formato JSON
- Rotação automática por tamanho e data
- Logs organizados por timestamp para análise histórica

### Métricas disponíveis

- Request rate e response time (percentis P50, P95, P99)
- Error rate (4xx, 5xx)
- Taxa de sucesso de logins
- Usuários ativos
- Métricas de sistema (CPU, memória, disco)
- Eventos de negócio (scraping, ML, autenticação)

## Tecnologias utilizadas

- FastAPI para API REST
- SQLAlchemy para ORM
- SQLite como banco de dados
- BeautifulSoup para web scraping
- Pandas e Scikit-learn para análise de dados
- JWT para autenticação
- Prometheus Client para métricas
- Loguru para logs estruturados

## Estrutura do projeto

```
api/           - Endpoints da API
database/      - Configuração do banco de dados
models/        - Modelos de dados
scripts/       - Scripts de scraping
data/          - Arquivos CSV gerados
```