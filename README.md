# CxTrauma Logs — detector de bots por IP

API FastAPI que lee el access log de Apache del servidor de **cx-trauma**, identifica los ingresos
de crawlers/bots (Google, OpenAI, Anthropic, Amazon, Microsoft, Perplexity, etc.) comparando la IP
con los rangos que publican esas empresas, y **todos los días a las 11:00 (Chile)** envía a
**Google Analytics 4**, vía **Google Data Manager API**, los ingresos del día anterior por bot y empresa.

## Fuentes de IP

| Fuente | Contenido |
|---|---|
| [ipverse/bot-ip-blocks `crawlers.json`](https://github.com/ipverse/bot-ip-blocks) | Principal: Googlebot, GPTBot, ChatGPT-User, OAI-SearchBot, ClaudeBot, Amazonbot, Bingbot, Applebot, PerplexityBot, Meta, Common Crawl… |
| Google `googlebot.json`, `special-crawlers.json`, `user-triggered-fetchers.json` | Oficiales (se fusionan con ipverse) |
| OpenAI `gptbot.json`, `searchbot.json`, `chatgpt-user.json` | Oficiales |
| AWS `ip-ranges.json` (opcional, `INCLUIR_AWS=true`) | Toda la nube AWS como "Amazon AWS (nube, no verificado)"; prioridad más baja que cualquier bot específico |

Las listas se guardan en caché en `/data/sources/`, se refrescan en cada job diario y con
`POST /fuentes/actualizar`. Si una descarga falla se usa la última caché.

## Endpoints

Todos salvo `/health` requieren el header `X-API-Token`.

| Método | Ruta | Acción |
|---|---|---|
| GET | `/health` | healthcheck |
| GET | `/reporte?fecha=YYYY-MM-DD` | (default: ayer) totales, por bot, por empresa, top IPs y rutas |
| GET | `/fuentes` | bots y estado de cada fuente |
| POST | `/fuentes/actualizar` | descarga de nuevo las listas |
| POST | `/enviar?fecha=&validate_only=&force=` | envío manual a GA4 |

Documentación interactiva en `/docs`.

## Qué llega a GA4

Un evento `bot_traffic_daily` por bot y día, con parámetros `bot_name`, `bot_company`, `bot_hits`
y `fecha_log` (`transactionId = {fecha}-{bot}` para deduplicar). **No se envían IPs ni datos de
visitantes.** GA4 acepta eventos de hasta 72 h atrás, así que el día anterior entra sin problema.

Configuración manual en GA4 (una vez):

1. *Administrar → Definiciones personalizadas*: dimensiones de evento `bot_name` y `bot_company`;
   métrica `bot_hits`.
2. Dar a la service account rol **Editor** en la propiedad GA4.
3. Crear una exploración con evento `bot_traffic_daily`, filas `bot_company` / `bot_name`, valor `bot_hits`.

En Google Cloud: habilitar **Data Manager API** y crear una service account con clave JSON.

## Despliegue (Docker, en el servidor de producción)

```bash
cp .env.example .env            # completar API_TOKEN, GA4_PROPERTY_ID, GA4_MEASUREMENT_ID
mkdir -p data secrets
sudo chown 10001:4 data         # usuario del contenedor (grupo adm)
cp /ruta/service-account.json secrets/
docker compose up -d --build
```

- Verificar el nombre real del log del vhost (`ls /var/log/apache2/`) y ajustar `APACHE_LOG_GLOB`.
- Primero probar con `DM_VALIDATE_ONLY=true`:
  `curl -X POST -H "X-API-Token: $API_TOKEN" "http://127.0.0.1:8001/enviar?validate_only=true"`
  y luego pasar a `false`.
- Registro de envíos en `data/envios.json` (el job no reenvía un día ya enviado salvo `force=true`).
- Logs del job: `docker logs cxtrauma-logs`.

## Desarrollo

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements-dev.txt
pytest
```
