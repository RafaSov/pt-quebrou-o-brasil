#!/usr/bin/env python3
"""Monta data/series.js a partir dos arquivos oficiais já baixados em data/raw."""

import csv
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"


def br(value, digits):
    number = Decimal(str(value)).quantize(Decimal("1." + "0" * digits), rounding=ROUND_HALF_UP)
    sign = "-" if number < 0 else ""
    number = abs(number)
    whole = int(number)
    text = f"{whole:,}".replace(",", ".")
    if digits:
        frac = format(number, f".{digits}f").split(".")[1]
        text += "," + frac
    return sign + text


def rows_html(name):
    text = (RAW / name).read_text("utf-8", "replace")
    found = re.findall(r'align="left"[^>]*>(\d{4})</td><td[^>]*>(.*?)</td>', text)
    points = []
    for year, raw in found:
        raw = re.sub(r"<[^>]+>", "", raw).replace("&nbsp;", "").strip()
        if not raw:
            continue
        points.append({"year": int(year), "value": float(raw.replace(".", "").replace(",", "."))})
    return [point for point in points if point["year"] >= 1995]


def sidra_points(name, year_key="D3N"):
    data = json.loads((RAW / name).read_text())
    points = []
    for row in data[1:]:
        if row.get("V") in (None, "", "..", "-"):
            continue
        points.append({"year": int(row[year_key]), "value": float(row["V"])})
    return points


def december(name):
    data = json.loads((RAW / name).read_text())
    points = []
    for row in data:
        if row["data"].startswith("01/12/"):
            points.append({"year": int(row["data"][-4:]), "value": float(row["valor"])})
    return points


def unemployment():
    data = json.loads((RAW / "desocup_pnadc.json").read_text())
    buckets = {}
    for row in data[1:]:
        year = int(row["D3N"].split()[-1])
        buckets.setdefault(year, []).append(Decimal(row["V"]))
    points = []
    for year in sorted(buckets):
        values = buckets[year]
        if len(values) != 4:
            continue
        average = (sum(values) / Decimal(4)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        points.append({"year": year, "value": float(average)})
    return points


def gdp_index():
    growth = sidra_points("pib_var.json")
    level = {1995: Decimal("100")}
    for point in growth:
        level[point["year"]] = level[point["year"] - 1] * (Decimal("1") + Decimal(str(point["value"])) / Decimal("100"))
    base = level[2002]
    return [
        {"year": year, "value": float((level[year] / base * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))}
        for year in sorted(level)
    ]


def exports():
    points = []
    with (RAW / "exp_totais.csv").open(encoding="latin-1", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            year = int(row["CO_ANO"])
            if year >= 2026:
                continue
            billions = (Decimal(row["VL_FOB"]) / Decimal("1000000000")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            points.append({"year": year, "value": float(billions)})
    return points


def series_from(pairs, digits=2, scale=Decimal("1")):
    points = []
    for year, raw in pairs:
        value = (Decimal(str(raw)) / scale).quantize(Decimal("1." + "0" * digits), rounding=ROUND_HALF_UP)
        points.append({"year": year, "value": float(value)})
    return points


def at(points, year):
    return next(point["value"] for point in points if point["year"] == year)


fome_pnad = rows_html("ipea_37816.html")
fome_pnadc = rows_html("extra_38605733.html")
gini_pnad = rows_html("ipea_37818.html")
renda = rows_html("ipea_37820.html")
gini_pnadc = sidra_points("gini_pnadc.json")
desocup = unemployment()
ipca = december("ipca_13522.json")
reservas_mi = december("reservas_3546.json")
reservas = [
    {"year": point["year"], "value": float((Decimal(str(point["value"])) / Decimal("1000")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))}
    for point in reservas_mi
]
ptax = {point["year"]: point["value"] for point in december("ptax_3698.json")}
divida = december("divida_13762.json")
pib = gdp_index()
exp = exports()
mort = sidra_points("mort_3834.json")
homic = series_from([
    (2014, 30.2), (2015, 29.3), (2016, 30.8), (2017, 32.1), (2018, 28.2),
    (2019, 22.0), (2020, 23.9), (2021, 22.8), (2022, 22.1), (2023, 21.7), (2024, 20.1),
], 1)

# Anfavea / Renavam-Senatran: automóveis novos. Até 2001, venda no atacado; daqui, só 2002+.
carros = series_from([
    (2002, 1243467), (2003, 1215549), (2004, 1315358), (2005, 1439822),
    (2006, 1632947), (2007, 2085706), (2008, 2341304), (2009, 2643862),
    (2010, 2856540), (2011, 2901647), (2012, 3115223), (2013, 3040783),
    (2014, 2794687), (2015, 2123009), (2016, 1688289), (2017, 1856584),
    (2018, 2102114), (2019, 2262073), (2020, 1615942), (2021, 1558467),
    (2022, 1576662), (2023, 1721400),
], 2, Decimal("1000000"))

# 1ª dose da tríplice viral. 2002-2008: SI-PNI via DSSBR/Fiocruz. 2009-2023: SI-PNI via CNM.
vacina = series_from([
    (2002, 96.9), (2003, 113.0), (2004, 105.0), (2005, 99.7), (2006, 102.2),
    (2007, 104.9), (2008, 101.3), (2009, 103.7), (2010, 99.9), (2011, 102.4),
    (2012, 99.5), (2013, 107.5), (2014, 112.8), (2015, 96.1), (2016, 95.4),
    (2017, 86.2), (2018, 92.6), (2019, 93.1), (2020, 80.9), (2021, 74.9),
    (2022, 80.7), (2023, 86.8),
], 1)

# PNAD/IBGE, domicílios rurais permanentes sem iluminação, invertido para % com luz.
luz_sem = [
    (2001, 22.37), (2002, 19.81), (2003, 18.08), (2004, 18.49), (2005, 16.53),
    (2006, 13.93), (2007, 10.93), (2008, 8.60), (2009, 6.67), (2011, 4.22),
    (2012, 2.98), (2013, 2.63), (2014, 2.16),
]
luz = [
    {"year": year, "value": float((Decimal("100") - Decimal(str(value))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))}
    for year, value in luz_sem
]

# Inep/MCTI: matrículas presenciais, em milhões.
uni_presencial = series_from([
    (2000, 2694245), (2001, 3030754), (2002, 3478599), (2003, 3887771),
    (2004, 4163733), (2005, 4453156), (2006, 4676646), (2007, 4880381),
    (2008, 5113403), (2009, 5115896), (2010, 5449120), (2011, 5746762),
    (2012, 5923838), (2013, 6152405), (2014, 6486171), (2015, 6633545),
    (2016, 6554283), (2017, 6529681), (2018, 6394244), (2019, 6153560),
    (2020, 5574551), (2021, 5270184), (2022, 5112663), (2023, 5063501),
    (2024, 5037482),
], 2, Decimal("1000000"))

# Inep, notas estatísticas 2024: total de matrículas (presencial + EaD).
uni_total = series_from([
    (2014, 7839765), (2015, 8033574), (2016, 8052254), (2017, 8290911),
    (2018, 8451748), (2019, 8604526), (2020, 8680945), (2021, 8987120),
    (2022, 9444116), (2023, 9977217), (2024, 10227266),
], 2, Decimal("1000000"))

pico_reserva = max(reservas, key=lambda point: point["value"])
pico_carro = max(carros, key=lambda point: point["value"])


site = {
    "chapters": [
        {
            "id": "fome",
            "index": "01",
            "nav": "Fome",
            "kind": "broke",
            "title": "O Brasil da fome",
            "leitura": [
                f"Em 2002, {br(at(fome_pnad, 2002), 1)}% da população vivia em extrema pobreza. Em 2014, essa parcela havia caído para {br(at(fome_pnad, 2014), 1)}%. Em doze anos, o número ficou abaixo de um terço do que era.",
                "O gráfico reúne duas pesquisas. A linha clara vem da PNAD anual, do IBGE, e termina em 2014. A linha azul vem da PNAD Contínua e usa outro critério: viver com menos de US$ 3 por dia. Por isso as duas linhas não se conectam. Nessa segunda conta, a extrema pobreza volta a subir depois de 2015, chega a 10,4% em 2021 e recua para 5,5% em 2025.",
                "A FAO, da ONU, usa ainda um terceiro indicador. No mapa da fome, o Brasil saiu dessa lista em 2014, quando a subalimentação ficou abaixo de 2,5%. Voltou a aparecer no triênio 2019–2021.",
            ],
            "hint": "Há um intervalo em 2000 e em 2010 porque, em ano de Censo, a PNAD anual não foi a campo.",
            "unit": "% da população",
            "digits": 2,
            "axisZero": True,
            "series": [
                {"name": "Pesquisa antiga", "points": fome_pnad},
                {"name": "Pesquisa nova, US$ 3/dia", "points": fome_pnadc},
            ],
            "sources": [
                {"label": "Ipea, extrema pobreza", "href": "https://www.ipeadata.gov.br/ExibeSerie.aspx?module=M&serid=37816"},
                {"label": "Ipea, linha de US$ 3/dia", "href": "https://www.ipeadata.gov.br/ExibeSerie.aspx?serid=2096727544"},
                {"label": "FAO, Estado da Insegurança Alimentar 2024", "href": "https://www.fao.org/publications/sofi"},
            ],
        },
        {
            "id": "desigualdade",
            "index": "02",
            "nav": "Desigualdade",
            "kind": "broke",
            "title": "O Brasil da desigualdade",
            "leitura": [
                f"O índice de Gini mostra o quanto a renda está concentrada. Quanto mais perto de zero, menos desigual é o país. Na pesquisa antiga, o índice cai de {br(at(gini_pnad, 2002), 3)} em 2002 para {br(at(gini_pnad, 2014), 3)} em 2014.",
                f"A PNAD Contínua é outra pesquisa, com outra conta. Nela, o Gini vai de {br(at(gini_pnadc, 2012), 3)} em 2012 a {br(at(gini_pnadc, 2024), 3)} em 2024. Há uma queda na pandemia e uma pequena alta em 2025.",
                f"No mesmo período da série antiga, a renda média por pessoa no domicílio subiu de R$ {br(at(renda, 2002), 0)} para R$ {br(at(renda, 2014), 0)}, já descontada a inflação.",
            ],
            "hint": "A linha clara e a linha azul não são o mesmo índice. Cada uma vem de uma pesquisa. Por isso os números de 2012 não coincidem.",
            "unit": "índice de Gini",
            "digits": 3,
            "axisZero": False,
            "series": [
                {"name": "Pesquisa antiga", "points": gini_pnad},
                {"name": "Pesquisa nova", "points": gini_pnadc},
            ],
            "sources": [
                {"label": "Ipea, Gini", "href": "https://www.ipeadata.gov.br/ExibeSerie.aspx?module=M&serid=37818"},
                {"label": "Ipea, renda por pessoa", "href": "https://www.ipeadata.gov.br/ExibeSerie.aspx?module=M&serid=37820"},
                {"label": "IBGE, Gini da PNAD Contínua", "href": "https://sidra.ibge.gov.br/tabela/7435"},
            ],
        },
        {
            "id": "desemprego",
            "index": "03",
            "nav": "Desemprego",
            "kind": "broke",
            "title": "O Brasil do desemprego",
            "leitura": [
                f"A pesquisa contínua, válida para o país inteiro o ano todo, começa em 2012. Em 2014, a média do desemprego ficou em {br(at(desocup, 2014), 1)}%. Em 2020, no auge da pandemia, chegou a {br(at(desocup, 2020), 1)}%. Em 2025, recuou para {br(at(desocup, 2025), 1)}% — o menor valor desta série.",
                "A pesquisa anterior media apenas uma semana de setembro, com outro método. Por isso ela não entra no gráfico: misturar as duas séries seria comparar medidas diferentes.",
            ],
            "hint": "Cada ponto é a média dos quatro trimestres. O ano de 2026 ainda não fechou, e por isso não aparece.",
            "unit": "% sem trabalho",
            "digits": 2,
            "axisZero": True,
            "series": [{"name": "Desemprego", "points": desocup}],
            "sources": [
                {"label": "IBGE, desocupação", "href": "https://sidra.ibge.gov.br/tabela/4099"},
                {"label": "IBGE, PNAD Contínua", "href": "https://www.ibge.gov.br/estatisticas/sociais/trabalho/9171-pesquisa-nacional-por-amostra-de-domicilios-continua-mensal.html"},
            ],
        },
        {
            "id": "inflacao",
            "index": "04",
            "nav": "Inflação",
            "kind": "broke",
            "title": "O Brasil da inflação",
            "leitura": [
                f"O IPCA encerrou 2002 em {br(at(ipca, 2002), 1)}%. Nos anos seguintes, a inflação ficou, na maior parte do tempo, abaixo desse patamar. Voltou aos dois dígitos em 2015, com {br(at(ipca, 2015), 1)}%, e outra vez em 2021, com {br(at(ipca, 2021), 1)}%.",
                f"Em 2025, o ano fechou em {br(at(ipca, 2025), 1)}%. Cada ponto do gráfico é o acumulado de janeiro a dezembro, não a média dos meses.",
            ],
            "hint": "Um ponto por ano, sempre o fechamento de dezembro. O ano de 2026 ainda não terminou.",
            "unit": "% no ano",
            "digits": 2,
            "axisZero": True,
            "series": [{"name": "IPCA", "points": ipca}],
            "sources": [
                {"label": "IBGE, IPCA", "href": "https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9256-indice-nacional-de-precos-ao-consumidor-amplo.html"},
                {"label": "Banco Central, séries", "href": "https://www3.bcb.gov.br/sgspub/"},
            ],
        },
        {
            "id": "mortalidade",
            "index": "05",
            "nav": "Mortalidade",
            "kind": "broke",
            "title": "O Brasil da mortalidade infantil",
            "leitura": [
                f"Em 2002, {br(at(mort, 2002), 1)} bebês morriam antes de completar um ano, a cada mil nascidos vivos. Em 2016, eram {br(at(mort, 2016), 1)}. A linha cai de ponta a ponta.",
                "Esta tabela do IBGE termina em 2016 porque é a projeção revisada em 2013. A tábua de mortalidade de 2023, do mesmo instituto, aponta 12,5 mortes por mil nascidos. É outro cálculo, e por isso esse número fica só no texto.",
            ],
            "hint": "A linha cobre 2000 a 2016. O 12,5 de 2023 vem de outra tábua e não entra no gráfico.",
            "unit": "mortes a cada mil nascidos",
            "digits": 1,
            "axisZero": False,
            "series": [{"name": "Mortalidade infantil", "points": mort}],
            "sources": [
                {"label": "IBGE, mortalidade infantil", "href": "https://sidra.ibge.gov.br/tabela/3834"},
                {"label": "IBGE, tábua de 2023", "href": "https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/noticias/41984-em-2023-expectativa-de-vida-chega-aos-76-4-anos-e-supera-patamar-pre-pandemia"},
            ],
        },
        {
            "id": "vacinacao",
            "index": "06",
            "nav": "Vacinação",
            "kind": "broke",
            "title": "O Brasil da vacinação baixa",
            "leitura": [
                "A primeira dose da tríplice viral — sarampo, caxumba e rubéola — ficou, na maior parte dos anos 2000, acima da meta de 95%. Em 2014 chegou a 112,8%. Valores acima de 100% aparecem quando se aplicam mais doses do que a estimativa de crianças daquele ano.",
                "A queda vem depois. Em 2021 a cobertura foi a 74,9%. Em 2023 subiu para 86,8%, ainda abaixo da meta. A pólio fez o mesmo caminho: 96,8% em 2014, 71% em 2021 e 84,6% em 2023.",
            ],
            "hint": "A linha é a 1ª dose da tríplice viral. De 2002 a 2008 os números vêm de uma tabulação antiga do SI-PNI. De 2009 em diante, da extração de 2024. Por isso 2009 não é a emenda perfeita de 2008.",
            "unit": "% das crianças",
            "digits": 1,
            "axisZero": False,
            "series": [{"name": "1ª dose da tríplice viral", "points": vacina}],
            "sources": [
                {"label": "Ministério da Saúde, PNI", "href": "https://datasus.saude.gov.br/acesso-a-informacao/imunizacoes-desde-1994/"},
                {"label": "Fiocruz, cobertura 2000–2009", "href": "https://dssbr.ensp.fiocruz.br/wp-content/uploads/2012/03/Ind030203-20120130.pdf"},
                {"label": "CNM, coberturas 2014–2023", "href": "https://cnm.org.br/storage/biblioteca/2024/Estudos_tecnicos/202407_ET_SAU_Avaliacao_coberturas_vacinais_municipios_criancas_cinco_anos.pdf"},
            ],
        },
        {
            "id": "homicidios",
            "index": "07",
            "nav": "Homicídios",
            "kind": "broke",
            "title": "O Brasil dos homicídios",
            "leitura": [
                "A série nacional do Atlas da Violência começa em 2014, com 30,2 mortes a cada 100 mil habitantes. O pico é 2017, com 32,1. Em 2024 a taxa está em 20,1 — cerca de um terço a menos do que em 2014.",
                "O próprio Atlas alerta: nos anos mais recentes cresceram as mortes violentas sem causa definida, o que dificulta a leitura. Por isso o texto não vai além do que a série registra.",
            ],
            "hint": "Uma linha, uma fonte, de 2014 a 2024. Não há série nacional conferida aqui para os anos anteriores.",
            "unit": "mortes a cada 100 mil",
            "digits": 1,
            "axisZero": False,
            "series": [{"name": "Homicídios registrados", "points": homic}],
            "sources": [
                {"label": "Atlas da Violência 2026", "href": "https://forumseguranca.org.br/publicacoes/atlas-da-violencia/"},
                {"label": "Relatório completo, PDF", "href": "https://forumseguranca.org.br/wp-content/uploads/2026/05/atlas-violencia-2026-relatorio-completo.pdf"},
            ],
        },
        {
            "id": "pib",
            "index": "08",
            "nav": "PIB",
            "kind": "built",
            "title": "O Brasil do PIB parado",
            "leitura": [
                f"Se 2002 vale 100, em 2010 a economia já estava em {br(at(pib, 2010), 0)}. Em 2014, em {br(at(pib, 2014), 0)}. Em volume — já descontada a inflação — o país cresceu cerca de metade em doze anos.",
                f"A recessão de 2015 e 2016 derrubou o índice para {br(at(pib, 2016), 0)}. Em 2023, último ano desta tabela anual do IBGE, o índice estava em {br(at(pib, 2023), 0)}.",
            ],
            "hint": "Não é o PIB em reais. É um índice de volume, com 2002 valendo 100. Se o número sobe, a economia realmente cresceu, não só os preços.",
            "unit": "tamanho da economia, 2002 = 100",
            "digits": 1,
            "axisZero": False,
            "series": [{"name": "PIB real", "points": pib}],
            "sources": [
                {"label": "IBGE, Contas Nacionais", "href": "https://www.ibge.gov.br/estatisticas/economicas/contas-nacionais.html"},
                {"label": "IBGE, tabela 6784", "href": "https://sidra.ibge.gov.br/tabela/6784"},
            ],
        },
        {
            "id": "reservas",
            "index": "09",
            "nav": "Reservas",
            "kind": "built",
            "title": "O Brasil sem reservas",
            "leitura": [
                f"No fim de 2002 o Banco Central tinha US$ {br(at(reservas, 2002), 0)} bilhões em reservas. O pico desta série é {pico_reserva['year']}, com US$ {br(pico_reserva['value'], 0)} bilhões. Em dezembro de 2025, as reservas estavam em US$ {br(at(reservas, 2025), 0)} bilhões.",
                f"O dólar de venda, na média de dezembro, foi de R$ {br(ptax[2002], 2)} em 2002 e R$ {br(ptax[2025], 2)} em 2025. O preço do dólar segue outro caminho e, por isso, fica nesta frase, não no gráfico.",
            ],
            "hint": "Posição de dezembro, conceito liquidez. É o colchão em dólar do Banco Central, não o preço do câmbio.",
            "unit": "US$ bilhões",
            "digits": 1,
            "axisZero": True,
            "series": [{"name": "Reservas", "points": reservas}],
            "sources": [
                {"label": "Banco Central, reservas", "href": "https://www.bcb.gov.br/estatisticas/reservasinternacionais"},
                {"label": "Banco Central", "href": "https://www.bcb.gov.br"},
            ],
        },
        {
            "id": "exportacoes",
            "index": "10",
            "nav": "Exportações",
            "kind": "built",
            "title": "O Brasil que exportava pouco",
            "leitura": [
                f"Em 2002 o país vendeu US$ {br(at(exp, 2002), 0)} bilhões ao exterior. Em 2025, US$ {br(at(exp, 2025), 0)} bilhões. Há quedas no caminho — 2009 e 2015 — mas a linha longa sobe.",
                "O número é o valor em dólar das mercadorias na saída, na conta FOB do Ministério do Desenvolvimento. Não inclui serviços nem o preço em reais.",
            ],
            "hint": "Soma anual em dólar. 2026 ainda está incompleto na base, então ficou de fora.",
            "unit": "US$ bilhões",
            "digits": 1,
            "axisZero": True,
            "series": [{"name": "Exportações", "points": exp}],
            "sources": [
                {"label": "MDIC, Comex Stat", "href": "https://comexstat.mdic.gov.br"},
                {"label": "MDIC, base da balança", "href": "https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta"},
            ],
        },
        {
            "id": "carros",
            "index": "11",
            "nav": "Carros",
            "kind": "built",
            "title": "O Brasil do carro velho",
            "leitura": [
                f"Em 2002 o Brasil emplacou {br(at(carros, 2002), 2)} milhão de carros novos. Em {pico_carro['year']}, {br(pico_carro['value'], 2)} milhões. O mercado mais que dobrou.",
                "Até 2001 a Anfavea media a venda no atacado. A partir de 2002, o emplacamento no Detran. Por isso o gráfico começa em 2002: é a série que se pode ler inteira. A frota estimada saiu de 22 milhões de veículos em 2002 para 43 milhões em 2014.",
            ],
            "hint": "Só automóveis 0 km, nacionais e importados. Não inclui motos nem a frota usada.",
            "unit": "milhões de carros novos",
            "digits": 2,
            "axisZero": True,
            "series": [{"name": "Carros 0 km", "points": carros}],
            "sources": [
                {"label": "Anfavea, anuário 2024", "href": "https://anfavea.com.br/site/wp-content/uploads/2024/04/ANFAVEA-ANUARIO-DIGITAL-2024_compressed.pdf"},
                {"label": "Anfavea, central de dados", "href": "https://anfavea.com.br/site/central-de-dados/"},
            ],
        },
        {
            "id": "universidade",
            "index": "12",
            "nav": "Universidade",
            "kind": "built",
            "title": "O Brasil sem faculdade",
            "leitura": [
                f"Em 2002 havia {br(at(uni_presencial, 2002), 2)} milhões de matrículas em cursos presenciais de graduação. Em 2014, {br(at(uni_presencial, 2014), 2)} milhões. A sala de aula física quase dobrou.",
                f"A linha azul entra em 2014 e soma o ensino a distância. O total chega a {br(at(uni_total, 2024), 2)} milhões em 2024 — a primeira vez que o Inep passa de 10 milhões. A presencial recua depois de 2015 porque parte da expansão foi para o EaD, não porque a universidade tenha encolhido.",
                "No mesmo período a Rede Federal saiu de cerca de 140 escolas técnicas em 2002 para 644 campi em 2016, segundo o MEC.",
            ],
            "hint": "A linha clara é só o curso presencial. A azul é o total, presencial mais EaD. Por isso a azul começa mais alto em 2014.",
            "unit": "milhões de matrículas",
            "digits": 2,
            "axisZero": True,
            "series": [
                {"name": "Presencial", "points": uni_presencial},
                {"name": "Total, com EaD", "points": uni_total},
            ],
            "sources": [
                {"label": "MCTI/Inep, matrículas presenciais", "href": "https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/indicadores/paginas/recursos-humanos/indicadores-sobre-o-ensino-de-graduacao/indicadores-sobre-o-ensino-de-graduacao-1"},
                {"label": "Inep, Censo 2024", "href": "https://download.inep.gov.br/educacao_superior/censo_superior/documentos/2024/apresentacao_censo_da_educacao_superior_2024.pdf"},
                {"label": "Inep, notas estatísticas 2024", "href": "https://download.inep.gov.br/publicacoes/institucionais/estatisticas_e_indicadores/notas_estatisticas_censo_escolar_da_educacao_superior_2024.pdf"},
            ],
        },
        {
            "id": "luz",
            "index": "13",
            "nav": "Luz",
            "kind": "built",
            "title": "O Brasil sem luz",
            "leitura": [
                f"Em 2002, {br(at(luz, 2002), 1)}% das casas permanentes no campo tinham energia elétrica. Em 2014, {br(at(luz, 2014), 1)}%. A falta de luz no campo quase acabou.",
                "O Luz para Todos, criado em 2003, fez mais de 3 milhões de ligações até 2014 e chegou a cerca de 15 milhões de pessoas, segundo o Ministério de Minas e Energia. Os anos de Censo, 2000 e 2010, ficam em branco porque a PNAD não foi a campo.",
            ],
            "hint": "A linha é o inverso da PNAD: 100 menos o percentual de casas rurais ainda sem luz. Não é a conta das ligações do programa, é a conta das casas.",
            "unit": "% das casas no campo",
            "digits": 2,
            "axisZero": False,
            "series": [{"name": "Casas rurais com luz", "points": luz}],
            "sources": [
                {"label": "MME/Eletrobras, Luz para Todos", "href": "https://www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-permanentes/cme/apresentacoes-em-eventos/2015/02_12_2015/ELETROBRAS.pdf"},
                {"label": "Ipea, 10 anos do programa", "href": "https://catalogo.ipea.gov.br/uploads/198_2.pdf"},
                {"label": "MME, dados abertos", "href": "https://dadosabertos.mme.gov.br/dataset/luz-para-todos"},
            ],
        },
        {
            "id": "divida",
            "index": "14",
            "nav": "Dívida",
            "kind": "plain",
            "title": "A dívida pública",
            "leitura": [
                f"A série oficial começa em 2006, em {br(at(divida, 2006), 1)}% do PIB. Recua até {br(at(divida, 2011), 1)}% em 2011. Depois sobe. Em 2020, no ano da pandemia, chega a {br(at(divida, 2020), 1)}%. Fecha 2025 em {br(at(divida, 2025), 1)}%.",
                "O gráfico mostra o tamanho da dívida bruta do governo em relação à economia, na metodologia do Banco Central. Não é uma queda: é o estoque, medido em percentual do PIB.",
                "O maior gasto ligado à dívida não é pagamento de dividendos. No orçamento, o serviço da dívida se divide em duas contas: a amortização — o principal que vence — e os juros. Em 2024, segundo estudo da Câmara dos Deputados com dados do Tesouro, a amortização ficou em R$ 1,645 trilhão. Boa parte disso é rolagem: o país quita um título e emite outro. Os juros e encargos, o custo que de fato pesa no caixa, somaram R$ 384,7 bilhões.",
            ],
            "hint": "Posição de dezembro. O primeiro ponto publicado é 2006. Não há dado oficial nesta série para 2002.",
            "unit": "% do PIB",
            "digits": 2,
            "axisZero": False,
            "series": [{"name": "Dívida bruta", "points": divida}],
            "sources": [
                {"label": "Tesouro Transparente", "href": "https://www.tesourotransparente.gov.br"},
                {"label": "Banco Central, estatísticas fiscais", "href": "https://www.bcb.gov.br/estatisticas/estatisticasfiscais"},
                {"label": "Câmara, estudo 16/2025", "href": "https://www2.camara.leg.br/orcamento-da-uniao/estudos/2025/Estudon16_2025DividaPublicaConciliacaoLOA_EstatisiticasDepMauroBenevides.pdf"},
            ],
        },
    ],
}

(ROOT / "series.js").write_text(
    "window.SITE = " + json.dumps(site, ensure_ascii=False, indent=2) + ";\n",
    encoding="utf-8",
)
print("chapters", len(site["chapters"]))
