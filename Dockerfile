FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY index_common.py llm.py guard.py rag_bot.py search_index.py eval_index.py ./
COPY index ./index
COPY index_attack ./index_attack

ENV PYTHONUTF8=1 \
    RAG_LLM=openai

CMD ["python", "rag_bot.py"]
