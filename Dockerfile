FROM python:3.12-slim

# Install PostgreSQL client tools
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy entire project directory
COPY . .

# Install Python dependencies and set script permissions
RUN pip install -r requirements.txt && \
    chmod +x /app/*.sh

ENTRYPOINT ["/app/combined_entrypoint.sh"]
