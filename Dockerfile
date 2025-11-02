FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY agent_server.py ./
EXPOSE 3001
CMD ["gunicorn", "-b", "0.0.0.0:3001", "agent_server:app", "--workers", "1", "--threads", "4"]