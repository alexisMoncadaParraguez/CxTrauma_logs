from app.sources import AWS_BOT, parse_aws, parser_prefixes


def test_ipv4_e_ipv6(matcher):
    assert matcher.buscar("66.249.64.31").bot == "Googlebot"
    assert matcher.buscar("66.249.64.32") is None  # fuera del /27
    assert matcher.buscar("2001:4860:4801:10::abcd").empresa == "Google"
    assert matcher.buscar("::ffff:20.171.207.1").bot == "GPTBot"


def test_bot_especifico_gana_a_nube(matcher):
    # 52.70.240.1 está en Amazonbot y en el rango AWS genérico
    assert matcher.buscar("52.70.240.1").bot == "Amazonbot"
    assert matcher.buscar("52.0.0.1").bot == AWS_BOT
    assert matcher.buscar("52.0.0.1").empresa == "Amazon"


def test_ip_invalida(matcher):
    assert matcher.buscar("no-es-ip") is None


def test_parsers_oficiales():
    data = {"prefixes": [{"ipv4Prefix": "1.2.3.0/24"}, {"ipv6Prefix": "2001:db8::/32"}]}
    [b] = parser_prefixes("GPTBot")(data)
    assert b.cidrs == ["1.2.3.0/24", "2001:db8::/32"] and b.empresa == "OpenAI"
    aws = {"prefixes": [{"ip_prefix": "3.0.0.0/8"}], "ipv6_prefixes": [{"ipv6_prefix": "2600::/16"}]}
    assert parse_aws(aws)[0].cidrs == ["2600::/16", "3.0.0.0/8"]
