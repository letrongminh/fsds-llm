# Gundam Store Assistant

An AI-powered chatbot for managing Gundam store orders, built with LangChain, PGVector, and Streamlit.

## Features

- 🔍 Order lookup by email
- ❌ Order cancellation for pending orders
- 💬 Natural language processing
- 🔄 Real-time streaming responses
- 📝 FAQ system with vector search
- 💾 Conversation memory

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- PostgreSQL
- AWS Account with Bedrock access

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd ai-agents-cs
```

2. **Create and activate virtual environment**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# For Windows
venv\Scripts\activate
# For macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
Create a `.env` file in the root directory:
```env
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=ap-northeast-1
```

## Database Setup

1. **Start PostgreSQL and PGVector database**
```bash
cd src/vectordb
docker-compose up -d
```

2. **Initialize the database**
```bash
# Wait for a few seconds for the database to be ready
psql -h localhost -U postgres -d postgres -f init.sql
```

3. **Load FAQ data**
```bash
# Add FAQ documents to vector database
python src/utils/faq/add_document_to_pgvector.py
```

4. **Create sample orders (optional)**
```bash
# Create sample orders in the database
python src/utils/database/orders_insert.py
```

## Running the Application

1. **Start the Streamlit application**
```bash
streamlit run ui/bot_ui.py
```

2. **Access the application**
Open your browser and navigate to:
```
http://localhost:8501
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
   - Ask general questions about products and policies
   - Get instant answers from the knowledge base

## Project Structure

```
ai-agents-cs/
├── src/
│   ├── core/
│   │   ├── agents.py         # Main agent logic
│   │   ├── tools.py          # Tool implementations
│   │   ├── embedding.py      # Embedding utilities
│   │   └── pgvector.py       # Vector database client
│   ├── utils/
│   │   ├── database/         # Database utilities
│   │   └── faq/             # FAQ management
│   └── vectordb/
│       ├── docker-compose.yml
│       └── init.sql
├── ui/
│   └── bot_ui.py            # Streamlit interface
└── requirements.txt
```

## Troubleshooting

1. **Database Connection Issues**
   - Ensure Docker containers are running: `docker ps`
   - Check PostgreSQL logs: `docker logs vectordb-postgres-1`
   - Verify database credentials in connection strings

2. **AWS Bedrock Access**
   - Confirm AWS credentials are set correctly
   - Ensure you have access to Claude model in Bedrock
   - Check region settings match your Bedrock endpoint

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
