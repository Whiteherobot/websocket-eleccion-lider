# Una imagen para todos los nodos; cada uno recibe su ID y su POSICION por entorno.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY anillo ./anillo
USER nobody
EXPOSE 8000
CMD ["python", "-m", "anillo.nodo"]
