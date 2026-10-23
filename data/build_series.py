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
    growth = sorted(sidra_points("pib_var.json"), key=lambda point: point["year"])
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
    (2022, 1576662), (2023, 1721415), (2024, 1948681), (2025, 1997264),
], 2, Decimal("1000000"))

# 1ª dose da tríplice viral. 2002-2008: SI-PNI via DSSBR/Fiocruz. 2009-2023: SI-PNI via CNM. 2024: PNI/MS.
vacina = series_from([
    (2002, 96.9), (2003, 113.0), (2004, 105.0), (2005, 99.7), (2006, 102.2),
    (2007, 104.9), (2008, 101.3), (2009, 103.7), (2010, 99.9), (2011, 102.4),
    (2012, 99.5), (2013, 107.5), (2014, 112.8), (2015, 96.1), (2016, 95.4),
    (2017, 86.2), (2018, 92.6), (2019, 93.1), (2020, 80.9), (2021, 74.9),
    (2022, 80.7), (2023, 86.8), (2024, 95.7),
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

# FBSP, tabela nacional de vítimas de feminicídio, 2021–2025.
# 2025 no Anuário (1.571) difere desta tabela (1.568); o gráfico fica com uma fonte só.
feminicidios = series_from([
    (2021, 1347), (2022, 1455), (2023, 1475), (2024, 1492), (2025, 1568),
], 0)


site = {
    "chapters": [
        {
            "id": "fome",
            "index": "01",
            "nav": "Fome",
            "kind": "broke",
            "title": "O Brasil da fome",
            "leitura": [
                f"Houve um tempo em que a extrema pobreza atingia uma parcela muito maior da população. Na pesquisa antiga, essa fatia cai de {br(at(fome_pnad, 2002), 1)}% em 2002 para {br(at(fome_pnad, 2014), 1)}% em 2014. A fome não desapareceu, mas milhões de pessoas passaram a viver em outra condição.",
                f"As duas linhas não são a mesma pesquisa. A azul, de quem vive com menos de US$ 3 por dia, sobe depois de 2014, chega a 10,4% em 2021 e recua para {br(at(fome_pnadc, 2025), 1)}% em 2025. A melhora foi importante. O retrocesso mostra que ela não é irreversível. Pobreza monetária também não é o mapa da fome da FAO.",
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
                {"label": "Ipea, nota técnica 1995–2024", "href": "https://repositorio.ipea.gov.br/bitstreams/f7669f57-30f0-4ed5-9e5a-ddcd6a616381/download"},
            ],
        },
        {
            "id": "desigualdade",
            "index": "02",
            "nav": "Desigualdade",
            "kind": "broke",
            "title": "O Brasil dos poucos que tinham muito",
            "leitura": [
                f"A desigualdade brasileira sempre foi profunda. Na pesquisa antiga, o índice de Gini cai de {br(at(gini_pnad, 2002), 3)} em 2002 para {br(at(gini_pnad, 2014), 3)} em 2014, e a renda média por pessoa sobe de R$ {br(at(renda, 2002), 0)} para R$ {br(at(renda, 2014), 0)}, já sem a inflação. Quanto menor o Gini, menos concentrada está a renda.",
                f"O Brasil continua desigual, e a queda não foi contínua. A linha azul é outra pesquisa, a PNAD Contínua: vai de {br(at(gini_pnadc, 2012), 3)} em 2012 a {br(at(gini_pnadc, 2025), 3)} em 2025. As duas linhas não se emendam, e nenhum governo explica a trajetória inteira.",
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
            "title": "O Brasil de quem não conseguia trabalho",
            "leitura": [
                f"Ter trabalho é uma das principais formas de ter renda e autonomia. A taxa passou por melhora, uma piora forte na recessão e na pandemia — {br(at(desocup, 2020), 1)}% em 2020, nesta conta — e uma nova queda depois.",
                f"Em 2025, a taxa anual do IBGE foi de 5,6%, a menor da série anual desde 2012. O ponto do gráfico, {br(at(desocup, 2025), 1)}%, é outra medida: a média dos quatro trimestres. Informalidade e subutilização, de 14,5% em 2025, não entram na linha. Uma taxa menor não significa que o problema acabou.",
            ],
            "hint": "Cada ponto é a média dos quatro trimestres, não a taxa anual publicada pelo IBGE. 2026 ainda não fechou.",
            "unit": "% sem trabalho",
            "digits": 2,
            "axisZero": True,
            "series": [{"name": "Desemprego", "points": desocup}],
            "sources": [
                {"label": "IBGE, desocupação", "href": "https://sidra.ibge.gov.br/tabela/4099"},
                {"label": "IBGE, PNAD Contínua", "href": "https://www.ibge.gov.br/estatisticas/sociais/trabalho/9171-pesquisa-nacional-por-amostra-de-domicilios-continua-mensal.html"},
                {"label": "IBGE, taxa anual de 2025", "href": "https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/45759-pnad-continua-em-2025-taxa-anual-de-desocupacao-foi-de-5-6-enquanto-taxa-de-subutilizacao-foi-14-5"},
            ],
        },
        {
            "id": "inflacao",
            "index": "04",
            "nav": "Inflação",
            "kind": "broke",
            "title": "O Brasil em que o dinheiro perdia valor",
            "leitura": [
                f"Quando os preços sobem rápido, o salário compra menos. O IPCA fechou 2002 em {br(at(ipca, 2002), 1)}% e voltou a passar de 10% em 2015 ({br(at(ipca, 2015), 1)}%) e em 2021 ({br(at(ipca, 2021), 1)}%).",
                f"Em 2025, a inflação do ano ficou em {br(at(ipca, 2025), 1)}%. Isso quer dizer que os preços subiram mais devagar — não que tenham voltado a ser baratos. Cada ponto é a alta acumulada de janeiro a dezembro, não o preço dos alimentos nem o poder de compra da família.",
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
            "title": "O Brasil em que mais crianças morriam cedo",
            "leitura": [
                f"Menos crianças passaram a morrer antes de completar um ano. Nesta projeção do IBGE, a taxa cai de {br(at(mort, 2002), 1)} mortes por mil nascidos vivos em 2002 para {br(at(mort, 2016), 1)} em 2016.",
                "Vacinação, pré-natal, saneamento, alimentação e acesso à saúde entram nessa história. O gráfico não separa o peso de cada um. A linha para em 2016 porque é essa projeção. A tábua de 2024, outro cálculo, aponta 12,3 por mil e não entra aqui.",
            ],
            "hint": "A linha cobre 2000 a 2016. O 12,3 de 2024 vem de outra tábua e não entra no gráfico.",
            "unit": "mortes a cada mil nascidos",
            "digits": 1,
            "axisZero": False,
            "series": [{"name": "Mortalidade infantil", "points": mort}],
            "sources": [
                {"label": "IBGE, mortalidade infantil", "href": "https://sidra.ibge.gov.br/tabela/3834"},
                {"label": "IBGE, tábua de 2024", "href": "https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/noticias/45275-expectativa-de-vida-chega-a-76-6-anos-em-2024"},
            ],
        },
        {
            "id": "vacinacao",
            "index": "06",
            "nav": "Vacinação",
            "kind": "broke",
            "title": "O Brasil em que a vacinação não chegava a todos",
            "leitura": [
                "Vacinas protegem contra doenças que deixam sequelas e matam. A linha é só a primeira dose da tríplice viral, contra sarampo, caxumba e rubéola. Em parte dos anos 2000 ela ficou acima da meta de 95% e chegou a 112,8% em 2014. Acima de 100% significa mais doses do que a estimativa de crianças daquele ano, não que todas tenham sido vacinadas.",
                "Depois a cobertura caiu, foi a 74,9% em 2021 e voltou a 95,7% em 2024. Recuperar uma dose não regulariza o calendário. A segunda dose e a pólio são outras contas e não entram nesta linha. Os trechos da série também vêm de extrações diferentes.",
            ],
            "hint": "A linha é a 1ª dose da tríplice viral. De 2002 a 2008 os números vêm de uma tabulação antiga do SI-PNI. De 2009 a 2023, da extração da CNM. O ponto de 2024 vem do painel do PNI. Por isso as emendas não são perfeitas.",
            "unit": "% das crianças",
            "digits": 1,
            "axisZero": False,
            "series": [{"name": "1ª dose da tríplice viral", "points": vacina}],
            "sources": [
                {"label": "Ministério da Saúde, PNI", "href": "https://datasus.saude.gov.br/acesso-a-informacao/imunizacoes-desde-1994/"},
                {"label": "Fiocruz, cobertura 2000–2009", "href": "https://dssbr.ensp.fiocruz.br/wp-content/uploads/2012/03/Ind030203-20120130.pdf"},
                {"label": "CNM, coberturas 2014–2023", "href": "https://cnm.org.br/storage/biblioteca/2024/Estudos_tecnicos/202407_ET_SAU_Avaliacao_coberturas_vacinais_municipios_criancas_cinco_anos.pdf"},
                {"label": "Ministério da Saúde, cobertura 2024", "href": "https://www.gov.br/saude/pt-br/assuntos/saude-com-ciencia/noticias/2024/dezembro/brasil-amplia-cobertura-vacinal-de-15-das-16-vacinas-do-calendario-infantil"},
                {"label": "Ministério da Saúde, nota 368/2025", "href": "https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/notas-tecnicas/2025/nota-tecnica-conjunta-no-368-2025-cgvdi-dpni-svsa-ms.pdf"},
                {"label": "Ministério da Saúde, painel PNI", "href": "https://infoms.saude.gov.br/extensions/SEIDIGI_DEMAS_VACINACAO_CALENDARIO_NACIONAL_COBERTURA_OCORRENCIA/SEIDIGI_DEMAS_VACINACAO_CALENDARIO_NACIONAL_COBERTURA_OCORRENCIA.html"},
            ],
        },
        {
            "id": "mulheres",
            "index": "07",
            "nav": "Mulheres",
            "kind": "broke",
            "title": "O Brasil em que mulheres viviam sob violência",
            "leitura": [
                "A violência contra a mulher não cabe em um único número. O gráfico mostra só os feminicídios registrados pelas polícias civis, na tabela do Fórum Brasileiro de Segurança Pública: 1.347 vítimas em 2021 e 1.568 em 2025. A curva sobe. Isso não significa que o problema tenha sido resolvido, nem que um governo explique a variação.",
                "O número depende de como o delegado classifica a morte, e a lei mudou em 2015 e de novo em 2024. Parte da alta pode ser reconhecimento do crime, não só mais casos. O Anuário de 2026 cita 1.571 vítimas em 2025 — a mesma família de dados, com outra consolidação. Estupro e agressão são outras séries e não entram nesta linha.",
            ],
            "hint": "Vítimas em boletins de ocorrência, 2021 a 2025. Os anos anteriores não entram: esta tabela não fecha uma série nacional comparável antes disso.",
            "unit": "vítimas registradas",
            "digits": 0,
            "axisZero": True,
            "series": [{"name": "Feminicídios registrados", "points": feminicidios}],
            "sources": [
                {"label": "Fórum Brasileiro de Segurança Pública, feminicídios", "href": "https://publicacoes.forumseguranca.org.br/server/api/core/bitstreams/3b78fed5-6500-4c8e-b64e-d6d9c81f0f92/content"},
                {"label": "Anuário de Segurança Pública 2026", "href": "https://forumseguranca.org.br/wp-content/uploads/2026/07/anuario-2026.pdf"},
            ],
        },
        {
            "id": "pib",
            "index": "08",
            "nav": "PIB",
            "kind": "built",
            "title": "O Brasil que precisava voltar a crescer",
            "leitura": [
                f"O tamanho da economia mudou. Se 2002 vale 100, o índice — já sem a inflação — chega a {br(at(pib, 2014), 0)} em 2014. A recessão de 2015 e 2016 derruba esse índice para {br(at(pib, 2016), 0)}. Depois a economia volta a crescer, em ritmos diferentes.",
                f"Em 2024 o PIB cresceu 3,4%; em 2025, 2,3%. O índice fecha 2025 em {br(at(pib, 2025), 0)}. Produzir mais não mostra, sozinho, como a renda foi dividida nem quantos empregos surgiram.",
            ],
            "hint": "Não é o PIB em reais. É um índice de volume, com 2002 valendo 100. Se o número sobe, a economia realmente cresceu, não só os preços. Os anos de 2024 e 2025 entram pela Contas Nacionais Trimestrais do IBGE.",
            "unit": "tamanho da economia, 2002 = 100",
            "digits": 1,
            "axisZero": False,
            "series": [{"name": "PIB real", "points": pib}],
            "sources": [
                {"label": "IBGE, Contas Nacionais", "href": "https://www.ibge.gov.br/estatisticas/economicas/contas-nacionais.html"},
                {"label": "IBGE, tabela 6784", "href": "https://sidra.ibge.gov.br/tabela/6784"},
                {"label": "IBGE, PIB 2024", "href": "https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/noticias/42775-pib-fecha-2024-em-3-4-e-registra-maior-taxa-desde-2021"},
                {"label": "IBGE, PIB 2025", "href": "https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/noticias/45969-pib-cresce-2-3-em-2025"},
            ],
        },
        {
            "id": "reservas",
            "index": "09",
            "nav": "Reservas",
            "kind": "built",
            "title": "O Brasil sem proteção contra crises externas",
            "leitura": [
                f"As reservas são uma proteção em dólar diante de um choque externo. No fim de 2002 o Banco Central tinha US$ {br(at(reservas, 2002), 0)} bilhões. Em 2012, US$ {br(at(reservas, 2012), 0)} bilhões. Em dezembro de 2025, US$ {br(at(reservas, 2025), 0)} bilhões.",
                f"Esse colchão aumenta e diminui, e não elimina os riscos. O preço do dólar é outra conta: R$ {br(ptax[2002], 2)} em dezembro de 2002 e R$ {br(ptax[2025], 2)} em dezembro de 2025. Ele não entra no gráfico.",
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
            "title": "O Brasil que vendia pouco ao mundo",
            "leitura": [
                f"No início dos anos 2000 o Brasil vendia bem menos ao exterior. Em 2002, as mercadorias exportadas somaram US$ {br(at(exp, 2002), 0)} bilhões. Em 2025, US$ {br(at(exp, 2025), 0)} bilhões. Houve quedas no caminho, como em 2009 e 2015.",
                "Exportar mais não conta quais produtos saíram, quanto valor ficou no país nem se a indústria se fortaleceu. O gráfico é o valor anual em dólar, no critério FOB, só de mercadorias.",
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
                f"Durante muito tempo, um carro novo esteve fora do alcance de muitas famílias. Em 2002 o Brasil emplacou {br(at(carros, 2002), 2)} milhão de automóveis zero-quilômetro. O pico é {pico_carro['year']}, com {br(pico_carro['value'], 2)} milhões. Em 2025, {br(at(carros, 2025), 2)} milhões.",
                "Emplacar mais carros novos não significa que todas as famílias passaram a ter um, nem que comprar e manter o veículo tenha ficado fácil. A linha começa em 2002, quando a conta passa a ser o emplacamento, não a venda no atacado.",
            ],
            "hint": "Só automóveis 0 km, nacionais e importados. Não inclui motos nem a frota usada.",
            "unit": "milhões de carros novos",
            "digits": 2,
            "axisZero": True,
            "series": [{"name": "Carros 0 km", "points": carros}],
            "sources": [
                {"label": "Anfavea, anuário 2026", "href": "https://anfavea.com.br/site/wp-content/uploads/2026/07/BOOK-ANUARIO-ANFAVEA-2026BAIXA.pdf"},
                {"label": "Anfavea, anuários", "href": "https://anfavea.com.br/site/conteudos/anuarios/"},
            ],
        },
        {
            "id": "universidade",
            "index": "12",
            "nav": "Universidade",
            "kind": "built",
            "title": "O Brasil de portas fechadas à universidade",
            "leitura": [
                f"Nos anos 2000, mais pessoas chegaram à graduação presencial: {br(at(uni_presencial, 2002), 2)} milhões de matrículas em 2002 e {br(at(uni_presencial, 2014), 2)} milhões em 2014. A rede federal de ensino técnico saiu de cerca de 140 escolas em 2002 para 644 campi em 2016, segundo o MEC.",
                f"Matrícula não é conclusão nem aprendizagem. A linha azul, desde 2014, soma o ensino a distância e chega a {br(at(uni_total, 2024), 2)} milhões em 2024. A presencial recua depois de 2015 porque parte da expansão foi para o EaD, não porque as duas contas sejam a mesma coisa.",
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
            "title": "O Brasil sem luz no campo",
            "leitura": [
                f"Ter energia em casa muda o estudo, o trabalho e a conservação da comida. Entre as casas permanentes no campo, {br(at(luz, 2002), 1)}% tinham luz em 2002 e {br(at(luz, 2014), 1)}% em 2014.",
                "O Luz para Todos, de 2003, fez parte desse processo — mais de 3 milhões de ligações até 2014, segundo o Ministério de Minas e Energia. Essa conta de ligações não é a linha do gráfico, que é a proporção de domicílios. Água e esgoto são outros serviços e não entram aqui.",
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
            "title": "O Brasil preso à dívida",
            "leitura": [
                f"A dívida acompanha arrecadação, gastos, juros, crescimento e crises. Nesta série, ela começa em 2006, em {br(at(divida, 2006), 1)}% do PIB, recua até {br(at(divida, 2011), 1)}% em 2011, sobe e chega a {br(at(divida, 2020), 1)}% em 2020. Em 2025 está em {br(at(divida, 2025), 1)}%.",
                "O tamanho da dívida, sozinho, não diz se um governo deu certo. O gráfico é o estoque em relação à economia, não o gasto do ano. Não há ponto em 2002 porque esta série não publica esse ano. Juros e amortização são outras contas: em 2024, a amortização foi de R$ 1,645 trilhão e os juros, de R$ 384,7 bilhões.",
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
