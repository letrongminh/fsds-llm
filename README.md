# Store Assistant

An AI-powered chatbot for managing store orders, built with LangChain, PGVector, OpenAI and Streamlit.

## Changelog

### v2.0.0
- Migrated from AWS Bedrock to OpenAI API
- Updated conversation flow handling
- Added better error handling and Vietnamese language support
- Improved response streaming
- Enhanced conversation memory management

## Features

- 🔍 Order lookup by email
- ❌ Order cancellation for pending orders  
- 💬 Natural language processing with OpenAI
- 🔄 Real-time streaming responses
- 📝 FAQ system with vector search
- 💾 Enhanced conversation memory
- 🌏 Multilingual support (English & Vietnamese)

## Prerequisites

- Python 3.12+
- Docker and Docker Compose
- PostgreSQL 
- OpenAI API key

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd fsds-llm
```

2. **Install uv for python manage package**
Install uv following the instruction from [uv](https://docs.astral.sh/uv/getting-started/installation/)

3. **Install dependencies**
Run `uv sync` it will automatically install all the dependencies and create a virtual environment
```bash
uv sync
```

4. **Set up PostgreSQL**
- Move to the `src/vectordb` directory and run `docker-compose up -d` to start the PostgreSQL and PGVector database
- Then move to utils directory, in faq folder, run `uv run enrich_faq.py` with faq.json path as argument (if you want to modify the faq.json, you can do it in the file or base on the schema in the file)
- Then run `uv run add_document_to_pgvector.py` to add the enriched faq to the database
- Then move to database folder, run `uv run orders_insert.py` to create sample orders in the database

5. **OpenAI API Key Configuration**
- Set up your OpenAI API key by exporting it as an environment variable:
```bash
export OPENAI_API_KEY='your-openai-api-key'
```

6. **Run the application**
Run `streamlit run main.py` to start the application

7. **Access the application**
Open your browser and navigate to:
```
http://localhost:8501/
```

## Usage

1. **Check Orders**
   - Ask "Show me my orders"
   - Provide your email when asked
   - View order details

2. **Cancel Orders**
   - Request "Cancel my order #ORD-123"
   - Provide email if not already given
   - Only pending orders can be cancelled

3. **FAQ**
   - Ask general questions about faq
   - Get instant answers from the knowledge base

## Project Structure

```
fsds-llm/
├── src/
│   ├── core/
│   │   ├── openai_client.py     # OpenAI API client
│   │   ├── tools.py             # Core chatbot logic
│   │   ├── embedding.py         # Embedding utilities
│   │   └── pgvector.py          # Vector database client
│   ├── utils/
│   │   ├── database/           # Database utilities
│   │   └── faq/                # FAQ management
│   └── vectordb/
│       ├── docker-compose.yml
│       └── init.sql
├── ui/
│   └── bot_ui.py               # Streamlit interface
└── requirements.txt
```

## Troubleshooting

1. **Database Connection Issues**
   - Ensure Docker containers are running: `docker ps`
   - Check PostgreSQL logs: `docker logs vectordb-postgres-1`
   - Verify database credentials in connection strings

2. **OpenAI API Access**
   - Confirm OpenAI API key is set correctly
   - Check OpenAI API usage limits and quotas

3. **Application Errors**
   - Check console logs for error messages
   - Verify all dependencies are installed
   - Ensure Python version compatibility

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Environment Variables

Set the following environment variables in your `.env` file:

```
OPENAI_API_KEY=your_api_key_here
POSTGRES_PASSWORD=your_db_password
POSTGRES_USER=your_db_user
POSTGRES_DB=your_db_name
```
