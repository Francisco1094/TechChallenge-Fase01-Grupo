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

## Tecnologias utilizadas

- FastAPI para API REST
- SQLAlchemy para ORM
- SQLite como banco de dados
- BeautifulSoup para web scraping
- Pandas e Scikit-learn para análise de dados
- JWT para autenticação

## Estrutura do projeto

```
api/           - Endpoints da API
database/      - Configuração do banco de dados
models/        - Modelos de dados
scripts/       - Scripts de scraping
data/          - Arquivos CSV gerados
```