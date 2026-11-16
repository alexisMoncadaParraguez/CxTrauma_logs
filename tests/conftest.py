import gzip
import json
from pathlib import Path

import pytest

from app.config import Settings
from app.matcher import Matcher
from app.sources import AWS_BOT, PRIORIDAD_NUBE, BotRanges, parse_ipverse

FIXTURES = Path(__file__).parent / "fixtures"

LINEAS = [
    # 29/oct -03:00 (Chile en horario de verano es -03:00)
    '66.249.64.5 - - [29/Oct/2026:08:00:00 -0300] "GET /blog HTTP/1.1" 200 512 "-" "Googlebot/2.1"',
    '66.249.64.6 - - [29/Oct/2026:09:00:00 -0300] "GET / HTTP/1.1" 200 512 "-" "Googlebot/2.1"',
    '20.171.207.10 - - [29/Oct/2026:10:00:00 -0300] "GET /blog HTTP/1.1" 200 512 "-" "GPTBot"',
    '52.70.240.1 - - [29/Oct/2026:11:00:00 -0300] "GET / HTTP/1.1" 200 512 "-" "Amazonbot"',
    '52.0.0.1 - - [29/Oct/2026:11:30:00 -0300] "GET / HTTP/1.1" 200 512 "-" "curl"',
    '190.100.1.1 - - [29/Oct/2026:12:00:00 -0300] "GET / HTTP/1.1" 200 512 "-" "Mozilla"',
    '2001:4860:4801:10::1 - - [29/Oct/2026:13:00:00 -0300] "GET / HTTP/1.1" 200 1 "-" "Googlebot"',
    "linea basura",
    # otro día: no debe contarse
    '66.249.64.5 - - [28/Oct/2026:23:59:59 -0300] "GET / HTTP/1.1" 200 512 "-" "Googlebot"',
    # 30/oct 01:00 UTC = 29/oct 22:00 en Chile → sí cuenta
    '160.79.104.1 - - [30/Oct/2026:01:00:00 +0000] "GET /x HTTP/1.1" 200 1 "-" "ClaudeBot"',
]


@pytest.fixture
def bots():
    data = json.loads((FIXTURES / "crawlers.json").read_text())
    return parse_ipverse(data) + [BotRanges(AWS_BOT, ["52.0.0.0/10"], PRIORIDAD_NUBE)]


@pytest.fixture
def matcher(bots):
    return Matcher(bots)


@pytest.fixture
def settings(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    # Mitad en el log rotado comprimido, mitad en el actual
    with gzip.open(logs / "access.log.2.gz", "wt") as f:
        f.write("\n".join(LINEAS[:4]) + "\n")
    (logs / "access.log").write_text("\n".join(LINEAS[4:]) + "\n")
    return Settings(
        _env_file=None,
        api_token="secreto",
        apache_log_glob=str(logs / "access.log*"),
        data_dir=tmp_path / "data",
        ga4_property_id="123",
        ga4_measurement_id="G-TEST",
        scheduler_activo=False,
    )
