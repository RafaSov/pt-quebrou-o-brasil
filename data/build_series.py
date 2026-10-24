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
# Taxa anual oficial da retrospectiva da PNAD Contínua. Não é a média dos trimestres.
# 2012–2024: IBGE, retrospectiva (7,4 … 6,6). 2014 é 7,0, não 6,9. 2025: 5,6 (release de 30/01/2026).
desocup = series_from([
    (2012, 7.4), (2013, 7.3), (2014, 7.0), (2015, 8.9), (2016, 11.7),
    (2017, 12.6), (2018, 12.2), (2019, 11.8), (2020, 13.8), (2021, 14.0),
    (2022, 9.6), (2023, 7.8), (2024, 6.6), (2025, 5.6),
], 1)
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

# FBSP, Retrato dos feminicídios 2026, série revisada 2015–2025.
# Edições anteriores do Anuário trazem outros totais para os mesmos anos; o gráfico usa só esta.
feminicidios = series_from([
    (2015, 449), (2016, 929), (2017, 1075), (2018, 1229), (2019, 1330),
    (2020, 1354), (2021, 1347), (2022, 1455), (2023, 1475), (2024, 1492),
    (2025, 1568),
], 0)


site = {
    "chapters": [
        {
            "id": "mapa-fome",
            "index": "01",
            "nav": "Fome",
            "kind": "broke",
            "title": "O Brasil da fome",
            "leitura": [
                "Durante muito tempo, milhões de brasileiros não sabiam se teriam comida na mesa. Muitas vezes o problema não era faltar alimento no país. Era faltar dinheiro para comprar.",
                "Em 2014, o Brasil saiu do Mapa da Fome da ONU. Anos depois voltou a aparecer. Saiu de novo no período de 2022 a 2024, e o relatório de 2026 manteve o país fora, olhando 2023 a 2025. O avanço existiu. Ele também pode voltar atrás.",
                "Bolsa Família, Fome Zero e a compra de comida produzida por agricultores familiares ajudaram famílias sem dinheiro. Nenhuma dessas medidas, sozinha, explica o mapa. Este bloco não tem gráfico: a ONU junta três anos de cada vez. O próximo mostra outra coisa, quantas pessoas viviam com muito pouco.",
            ],
            "hint": "Não há linha aqui. O mapa da ONU não é a mesma conta da pobreza do bloco seguinte.",
            "sources": [
                {"label": "FAO, saída do mapa em 2025", "href": "https://www.fao.org/brasil/news/detail/Brasil-voltou-a-sair-do-Mapa-da-Fome"},
                {"label": "FAO e MDS, relatório de 2026", "href": "https://www.gov.br/mds/pt-br/noticias/relatorio-da-onu-confirma-que-brasil-permanece-fora-do-mapa-da-fome-e-aponta-melhora-em-indicadores"},
                {"label": "Lei do PNAE, 2009", "href": "https://planalto.gov.br/ccivil_03/_ato2007-2010/2009/lei/l11947.htm"},
            ],
        },
        {
            "id": "fome",
            "index": "02",
            "nav": "Pobreza",
            "kind": "broke",
            "title": "O Brasil da pobreza extrema",
            "leitura": [
                "Imagine ter de escolher entre comida, a conta de luz e um remédio. Era a vida de muita gente que vivia com muito pouco.",
                f"Na pesquisa antiga, essa parcela cai de {br(at(fome_pnad, 2002), 1)}% em 2002 para {br(at(fome_pnad, 2014), 1)}% em 2014. Depois, em outra pesquisa, sobe e chega a 10,4% em 2021. Em 2025 está em {br(at(fome_pnadc, 2025), 1)}%. Parte do avanço se perdeu.",
                "O gráfico mostra quantas pessoas viviam com uma renda tão baixa que mal cobria o básico. As duas linhas são pesquisas diferentes e não se juntam. Bolsa Família, o salário mínimo e mais empregos ajudaram. Nenhum deles, sozinho, explica a curva.",
            ],
            "hint": "Em 2000 e em 2010 a pesquisa antiga não foi a campo. Por isso a linha clara tem um buraco.",
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
            "id": "salario",
            "index": "03",
            "nav": "Salário",
            "kind": "broke",
            "title": "O Brasil em que o salário rendia menos",
            "leitura": [
                "Receber um aumento não quer dizer que dá para comprar mais. Se os preços sobem junto, o dinheiro continua comprando quase a mesma coisa.",
                "Entre 2002 e janeiro de 2014, o salário mínimo passou a comprar 72,31% a mais, já descontada a inflação. A conta é do DIEESE. Isso ajudou quem recebia o piso e também aposentadorias e benefícios ligados a ele.",
                "Ainda assim, aluguel e comida podem apertar o mês. Este bloco não tem gráfico ano a ano: o número conferido é esse ganho acumulado, não uma linha completa até hoje.",
            ],
            "hint": "Não há série anual desenhada aqui. O 72,31% é o ganho acumulado calculado pelo DIEESE até janeiro de 2014.",
            "sources": [
                {"label": "DIEESE, salário mínimo até 2014", "href": "https://www.dieese.org.br/notatecnica/2013/notaTec132SalarioMinimo2014.pdf"},
                {"label": "Lei da valorização do salário mínimo, 2011", "href": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12382.htm"},
            ],
        },
        {
            "id": "desigualdade",
            "index": "04",
            "nav": "Desigualdade",
            "kind": "broke",
            "title": "O Brasil dos poucos que tinham muito",
            "leitura": [
                "O Brasil sempre teve uma distância grande entre quem ganha muito e quem ganha pouco. Em parte dos anos 2000, essa distância diminuiu.",
                f"O gráfico usa um número chamado Gini. Quanto menor, menos a renda fica na mão de poucos. Na pesquisa antiga, ele cai de {br(at(gini_pnad, 2002), 3)} em 2002 para {br(at(gini_pnad, 2014), 3)} em 2014. No mesmo período, a renda média por pessoa sobe de R$ {br(at(renda, 2002), 0)} para R$ {br(at(renda, 2014), 0)}, já sem a alta dos preços.",
                f"A linha azul é outra pesquisa e não continua a primeira. Nela, o número vai de {br(at(gini_pnadc, 2012), 3)} em 2012 a {br(at(gini_pnadc, 2025), 3)} em 2025. Salário mínimo, emprego e Bolsa Família ajudaram quem ganhava menos. O país continuou desigual.",
            ],
            "hint": "As duas linhas não se juntam. Cada uma vem de uma pesquisa.",
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
            "index": "05",
            "nav": "Desemprego",
            "kind": "broke",
            "title": "O Brasil de quem não conseguia trabalho",
            "leitura": [
                "Ficar sem emprego é não ter como pagar as contas nem planejar o mês seguinte. O desemprego caiu no começo dos anos 2010, subiu na crise e na pandemia e depois voltou a cair.",
                f"O gráfico mostra a parcela de quem procurava trabalho e não achava. Era {br(at(desocup, 2012), 1)}% em 2012, {br(at(desocup, 2014), 1)}% em 2014 e {br(at(desocup, 2021), 1)}% em 2021. Em 2025 chegou a {br(at(desocup, 2025), 1)}%, o menor valor desta conta do IBGE, que começa em 2012.",
                "Isso não quer dizer que todo mundo tenha um emprego estável. Ainda há gente sem carteira assinada, ganhando pouco ou querendo mais horas. Em 2025, 14,5% estavam nessa situação mais ampla, chamada de subutilização. Crescimento, obras e pequenos negócios ajudam a abrir vaga. Uma crise pode fechar a porta de novo.",
            ],
            "hint": "Cada ponto é a taxa do ano inteiro. Não é a média dos quatro trimestres. 2026 ainda não fechou.",
            "unit": "% sem trabalho",
            "digits": 1,
            "axisZero": True,
            "series": [{"name": "Desemprego anual", "points": desocup}],
            "sources": [
                {"label": "IBGE, retrospectiva 2012–2024", "href": "https://agenciadenoticias.ibge.gov.br/media/com_mediaibge/arquivos/7ecb563572f6812906c83177b53335ef.pdf"},
                {"label": "IBGE, retrospectiva 2012–2025", "href": "https://ftp.ibge.gov.br/Trabalho_e_Rendimento/Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/Principais_destaques_PNAD_continua/2012_2025/PNAD_continua_retrospectiva_2012_2025.pdf"},
                {"label": "IBGE, taxa anual de 2025", "href": "https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/45759-pnad-continua-em-2025-taxa-anual-de-desocupacao-foi-de-5-6-enquanto-taxa-de-subutilizacao-foi-14-5"},
            ],
        },
        {
            "id": "inflacao",
            "index": "06",
            "nav": "Inflação",
            "kind": "broke",
            "title": "O Brasil em que os preços disparavam",
            "leitura": [
                "Quando a comida, a gasolina e a conta de luz sobem muito, o salário parece encolher. A pessoa continua recebendo o mesmo e compra menos.",
                f"Inflação é esse aumento dos preços. O gráfico mostra quanto eles subiram em cada ano, de janeiro a dezembro. Em 2002, a alta foi de {br(at(ipca, 2002), 1)}%. Passou de 10% em 2015 ({br(at(ipca, 2015), 1)}%) e em 2021 ({br(at(ipca, 2021), 1)}%). Em 2025 ficou em {br(at(ipca, 2025), 1)}%.",
                "Quando a inflação cai, os preços não voltam a ser baratos. Só sobem mais devagar. Dólar, juros, safra, energia e as decisões do Banco Central entram nessa conta. Não dá para pôr a alta, ou a queda, na conta de um governo só.",
            ],
            "hint": "Cada ponto é o aumento dos preços naquele ano. 2026 ainda não terminou.",
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
            "index": "07",
            "nav": "Mortalidade",
            "kind": "broke",
            "title": "O Brasil em que mais crianças morriam cedo",
            "leitura": [
                "Perder um bebê é uma das dores mais difíceis de uma família. Por muito tempo, muitas crianças brasileiras morriam antes de completar um ano, por falta de cuidado, comida ou condições de vida.",
                f"O gráfico mostra quantas crianças morrem antes de um ano para cada mil que nascem vivas. Nesta conta do IBGE, o número cai de {br(at(mort, 2002), 1)} em 2002 para {br(at(mort, 2016), 1)} em 2016.",
                "Médico perto de casa, vacina, acompanhamento da gravidez e renda ajudam juntos. O posto de saúde da família já existia antes de 2003 e foi ampliado. O SAMU é de 2003. O Mais Médicos é de 2013. A linha para em 2016. Em 2024, outra conta do mesmo instituto aponta 12,3 por mil. Esse número fica só no texto.",
            ],
            "hint": "A linha vai de 2000 a 2016. O 12,3 de 2024 é outra conta e não entra no desenho.",
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
            "index": "08",
            "nav": "Vacinação",
            "kind": "broke",
            "title": "O Brasil em que a vacinação não chegava a todos",
            "leitura": [
                "Vacina protege contra doenças que deixam sequela ou matam. Para funcionar, ela precisa chegar na criança e a família precisa confiar.",
                "O gráfico é só a primeira dose da vacina contra sarampo, caxumba e rubéola. Nos anos 2000 ela passou da meta de 95% e chegou a 112,8% em 2014. Acima de 100% quer dizer que aplicaram mais doses do que o número estimado de crianças, não que todas foram vacinadas.",
                "Depois caiu, foi a 74,9% em 2021 e voltou a 95,7% em 2024. Recuperar uma dose não arruma o calendário inteiro. O programa nacional de vacinação é mais antigo que os governos do PT. O que muda é campanha, posto de saúde e a busca de quem ficou para trás.",
            ],
            "hint": "Só a primeira dose. Os trechos da linha vêm de bases diferentes, por isso a emenda não é perfeita.",
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
            "index": "09",
            "nav": "Mulheres",
            "kind": "broke",
            "title": "O Brasil em que mulheres não estavam seguras",
            "leitura": [
                "Toda mulher deveria viver sem medo de ser agredida ou morta. Leis e serviços de proteção avançaram. A violência não acabou.",
                "O gráfico mostra só os assassinatos que a polícia classificou como feminicídio, crime que ganhou esse nome em 2015. Foram 449 registros naquele ano e 1.568 em 2025. A linha sobe. Parte disso pode ser a polícia passando a reconhecer o crime, não só mais mortes.",
                "A Lei Maria da Penha é de 2006 e o telefone 180 é de 2005. São proteção, não a prova de que a violência caiu. Outra pesquisa, do Senado, ouviu as próprias mulheres: 7% disseram ter sofrido violência em casa nos 12 meses anteriores a 2023, e 4% em 2025. Essa pesquisa não entra na linha.",
            ],
            "hint": "Só feminicídios registrados. Não é tapa, ameaça nem estupro. Edições antigas do anuário trazem outros totais para os mesmos anos.",
            "unit": "vítimas registradas",
            "digits": 0,
            "axisZero": True,
            "series": [{"name": "Feminicídios registrados", "points": feminicidios}],
            "sources": [
                {"label": "Fórum Brasileiro de Segurança Pública, feminicídios", "href": "https://publicacoes.forumseguranca.org.br/server/api/core/bitstreams/3b78fed5-6500-4c8e-b64e-d6d9c81f0f92/content"},
                {"label": "Anuário de Segurança Pública 2026", "href": "https://forumseguranca.org.br/wp-content/uploads/2026/07/anuario-2026.pdf"},
                {"label": "DataSenado, pesquisa de violência contra a mulher", "href": "https://www12.senado.leg.br/institucional/omv/pesquisanacional"},
            ],
        },
        {
            "id": "pib",
            "index": "10",
            "nav": "PIB",
            "kind": "built",
            "title": "O Brasil que precisava voltar a crescer",
            "leitura": [
                "Quando a economia cresce, as empresas podem vender mais e contratar. Quando encolhe, o emprego e o salário das famílias sentem.",
                f"PIB é o tamanho dessa produção. No gráfico, 2002 vale 100. Se o número sobe, o país produziu mais, já sem contar a alta dos preços. Em 2014 estava em {br(at(pib, 2014), 0)}. A crise de 2015 e 2016 derrubou para {br(at(pib, 2016), 0)}. Em 2025 o índice está em {br(at(pib, 2025), 0)}.",
                "Em 2024 a economia cresceu 3,4%. Em 2025, 2,3%. Obras, consumo e crédito ajudam. Crise, juros e o que acontece lá fora também. Produzir mais não quer dizer que a vida de todo mundo melhorou.",
            ],
            "hint": "2002 vale 100. Se sobe, o país produziu mais, sem contar só o aumento dos preços.",
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
            "index": "11",
            "nav": "Reservas",
            "kind": "built",
            "title": "O Brasil que precisava se proteger de crises externas",
            "leitura": [
                "Uma crise em outro país também pode bater aqui. Reservas são uma poupança em moeda estrangeira para atravessar um momento difícil.",
                f"No fim de 2002 o Brasil tinha US$ {br(at(reservas, 2002), 0)} bilhões. Em 2012, US$ {br(at(reservas, 2012), 0)} bilhões. Em dezembro de 2025, US$ {br(at(reservas, 2025), 0)} bilhões. O gráfico é esse colchão, no fim de cada ano.",
                f"Vender mais para fora e a decisão de guardar esse dinheiro ajudaram a engrossar a reserva. Isso não acaba com as crises. O preço do dólar é outra história: R$ {br(ptax[2002], 2)} em dezembro de 2002 e R$ {br(ptax[2025], 2)} em dezembro de 2025.",
            ],
            "hint": "Dinheiro em moeda estrangeira no fim de dezembro. Não é o preço do dólar.",
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
            "index": "12",
            "nav": "Exportações",
            "kind": "built",
            "title": "O Brasil que vendia pouco ao mundo",
            "leitura": [
                "Vender para outros países traz dinheiro para cá. O valor do que o Brasil vendeu cresceu muito, com altos e baixos.",
                f"Em 2002 foram US$ {br(at(exp, 2002), 0)} bilhões. Em 2025, US$ {br(at(exp, 2025), 0)} bilhões. O gráfico é esse valor, em dólares, por ano. Teve queda em anos como 2009 e 2015.",
                "Vender mais não quer dizer que o país passou a fabricar mais máquina e tecnologia. Soja, minério e petróleo pesam nesse número. O preço deles lá fora muda o total mesmo quando a quantidade não muda tanto.",
            ],
            "hint": "Soma do ano em dólar. 2026 ainda não fechou, então ficou de fora.",
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
            "index": "13",
            "nav": "Carros",
            "kind": "built",
            "title": "O Brasil do carro velho",
            "leitura": [
                "Por muito tempo, carro novo estava fora do alcance de muita família. Quem precisava de um veículo acabava no usado.",
                f"O gráfico mostra quantos carros zero-quilômetro foram emplacados. Em 2002, {br(at(carros, 2002), 2)} milhão. O pico é {pico_carro['year']}, com {br(pico_carro['value'], 2)} milhões. Em 2025, {br(at(carros, 2025), 2)} milhões.",
                "Salário, emprego e crédito ajudaram mais gente a pensar em um carro novo. Isso não quer dizer que toda família tenha um. Financiar o carro também pode comprometer o mês. A linha começa em 2002, quando a conta passa a ser o emplacamento.",
            ],
            "hint": "Só carros novos. Não inclui moto nem a frota usada.",
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
            "index": "14",
            "nav": "Universidade",
            "kind": "built",
            "title": "O Brasil de portas fechadas à universidade",
            "leitura": [
                "Entrar numa universidade pública foi, por muito tempo, coisa distante. Principalmente para quem morava longe ou não tinha dinheiro para estudar em outra cidade.",
                f"O gráfico mostra matrículas na graduação. A sala de aula presencial sai de {br(at(uni_presencial, 2002), 2)} milhões em 2002 para {br(at(uni_presencial, 2014), 2)} milhões em 2014. A linha azul, a partir de 2014, soma o estudo a distância e chega a {br(at(uni_total, 2024), 2)} milhões em 2024.",
                "Bolsa, financiamento, mais campi e a Lei de Cotas, de 2012, abriram caminhos. Matrícula não é formatura. A presencial diminui depois de 2015 porque parte das vagas foi para o estudo a distância, não porque a universidade tenha sumido.",
            ],
            "hint": "A linha clara é só o curso presencial. A azul soma o estudo a distância.",
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
            "index": "15",
            "nav": "Luz",
            "kind": "built",
            "title": "O Brasil sem luz no campo",
            "leitura": [
                "Luz em casa é geladeira, estudo à noite e um jeito de trabalhar. Por muito tempo, muita família no campo vivia sem isso.",
                f"O gráfico mostra a parcela das casas permanentes no campo que tinham energia. Era {br(at(luz, 2002), 1)}% em 2002 e {br(at(luz, 2014), 1)}% em 2014.",
                "O Luz para Todos, criado em 2003, fez mais de 3 milhões de ligações até 2014. Essa conta de ligações não é a linha. A linha é a casa que passou a ter luz. Água e esgoto são outra história.",
            ],
            "hint": "Casas no campo com energia. Não é o número de ligações do programa.",
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
            "index": "16",
            "nav": "Dívida",
            "kind": "plain",
            "title": "O Brasil preso à dívida",
            "leitura": [
                "Dívida pública é o que o país deve. Para saber se ela pesa mais ou menos, o jeito é comparar com o tamanho da economia, não olhar só o número em reais.",
                f"O gráfico começa em 2006, em {br(at(divida, 2006), 1)}% da economia. Cai até {br(at(divida, 2011), 1)}% em 2011, sobe e chega a {br(at(divida, 2020), 1)}% em 2020. Em 2025 está em {br(at(divida, 2025), 1)}%. Não há ponto em 2002 porque esta série não publica esse ano.",
                "Crescimento, arrecadação, juros e crise mexem nessa linha. Pagar o FMI em 2005 foi outra dívida, a externa, e não entra aqui. Em 2024, quitar títulos que venceram somou R$ 1,645 trilhão, em boa parte trocando uma dívida por outra. Os juros custaram R$ 384,7 bilhões.",
            ],
            "hint": "Tamanho da dívida comparado com a economia, em dezembro. A série começa em 2006.",
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
        {
            "id": "conclusao",
            "index": "17",
            "nav": "Conclusão",
            "kind": "plain",
            "title": "Conclusão",
            "leitura": [
                "O Brasil nasceu desigual. Colonização, escravidão e injustiça estão na origem do país, e isso ainda pesa na vida de muita gente.",
                "Os governos do PT não resolveram os problemas do Brasil. Mas suas políticas públicas, o esforço para a economia crescer e os programas sociais ajudaram a diminuir, em grande parte, desigualdades que pareciam difíceis de vencer. Depois do golpe de 2016, vários desses problemas pioraram ou voltaram a crescer. Os gráficos desta página mostram isso.",
                "Ainda há muito pela frente. O caminho é seguir adiante, sem desfazer o que já melhorou a vida de milhões de pessoas. Não se deixe enganar pelo anti-petismo: pesquise você mesmo e abra os links das fontes, logo abaixo. Só com conhecimento, união e vontade dá para melhorar o país.",
            ],
            "hint": "",
            "sources": [],
        },
        {
            "id": "videos",
            "index": "18",
            "nav": "Vídeos",
            "kind": "plain",
            "title": "Vídeos auxiliares",
            "leitura": [
                "Vídeos que mostram quem REALMENTE quer quebrar o Brasil.",
            ],
            "hint": "",
            "videos": [
                {
                    "title": "Linha do tempo da Pilantragem de Flávio Bolsonaro — de Clara Bueno",
                    "label": "Linha do tempo da Pilantragem de Flávio Bolsonaro",
                    "href": "https://www.instagram.com/reel/De0Yu4kBNs2/",
                },
                {
                    "title": "O PT Quebrou o Brasil — de Arapê Malik",
                    "label": "O PT Quebrou o Brasil — de Arapê Malik",
                    "href": "https://www.instagram.com/reel/DezVq97s3_2/",
                },
                {
                    "title": "Flávio é contra a 6x1? — de Lauany schultz",
                    "label": "Flávio é contra a 6x1? — de Lauany schultz",
                    "href": "https://www.instagram.com/reel/DehlhtJpxpO/",
                },
                {
                    "title": "Como Bolsonaro foi Preso — de Lauany schultz e Caio Barroso",
                    "label": "Como Bolsonaro foi Preso — de Lauany schultz e Caio Barroso",
                    "href": "https://www.instagram.com/reel/DeK4CTmuI94/",
                },
                {
                    "title": "Revelando: Grandes Igrejas, Master Negócios — de Revelando.Brasil",
                    "label": "Revelando: Grandes Igrejas, Master Negócios — de Revelando.Brasil",
                    "href": "https://www.instagram.com/reel/DdlzspXRPtT/",
                },
            ],
            "sources": [],
        },
    ],
}

(ROOT / "series.js").write_text(
    "window.SITE = " + json.dumps(site, ensure_ascii=False, indent=2) + ";\n",
    encoding="utf-8",
)
print("chapters", len(site["chapters"]))
