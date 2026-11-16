FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=America/Santiago

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Usuario sin privilegios en el grupo adm (GID 4): los logs de Apache son root:adm 640
RUN useradd --uid 10001 --gid 4 --no-create-home appuser \
    && mkdir -p /data && chown appuser:adm /data
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
