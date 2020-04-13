# Import required libraries
import pickle
import copy
import pathlib
import dash
import math
import datetime as dt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dash.dependencies import Input, Output
from dash.dependencies import State, ClientsideFunction
import dash_core_components as dcc
import dash_html_components as html
from calc import InsuranceHandler
from calc import real_br_money_mask
from calc import generate_main_plot
from calc import generate_reserves_plot
from calc import generate_tables_plot

# Multi-dropdown options
from controls import PRODUCTS, DEF_PRODUCT, GENDER, DEF_GENDER

class DashCallbackVariables:
    """Class to store information useful to callbacks"""

    def __init__(self):
        self.n_clicks = {1: 0, 2: 0}

    def update_n_clicks(self, nclicks, bt_num):
        self.n_clicks[bt_num] = nclicks

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("data").resolve()

df = pd.read_excel(DATA_PATH.joinpath("life_tables.xlsx"))
df_interest = pd.read_excel(DATA_PATH.joinpath("risk_free.xlsx"))

handler = InsuranceHandler(df)
callbacks_vars = DashCallbackVariables()

app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport",
                          "content": "width=device-width"}]
)
server = app.server

# Create controls
DEF_INTEREST_RATE = df_interest[df_interest['month'] \
                                == df_interest['month'].\
                                max()]['selic_year'].values[0]/100

callbacks_vars.i_rate_reserve =  DEF_INTEREST_RATE

main_fig = go.Figure(data=[go.Surface()],
                     layout=go.Layout(title="Dotal Misto"))

reserve_chart = go.Figure(layout = go.Layout(
        title= "Reservas",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
        ))

table_chart = go.Figure(layout = go.Layout(
        title= "Comparação de Tábuas",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
        ))

tables = list(df['table'].unique())
table_options = [{'value':tb, 'label':tb} for i, tb in enumerate(tables)]
DEF_TABLE = ' AT2000'

product_options = [
    {"label": str(PRODUCTS[product]), "value": product} for product in PRODUCTS
]

gender_options = [
    {"label": str(GENDER[option_]), "value": option_} for option_ in GENDER
]


# Load data
# Create global chart template
mapbox_access_token = "pk.eyJ1IjoiamFja2x1byIsImEiOiJjajNlcnh3MzEwMHZtMzNueGw3NWw5ZXF5In0.fk8k06T96Ml9CLGgKmk81w"

layout = dict(
    autosize=True,
    automargin=True,
    margin=dict(l=30, r=30, b=20, t=40),
    hovermode="closest",
    plot_bgcolor="#F9F9F9",
    paper_bgcolor="#F9F9F9",
    legend=dict(font=dict(size=10), orientation="h"),
    title="Satellite Overview",
    mapbox=dict(
        accesstoken=mapbox_access_token,
        style="light",
        center=dict(lon=-78.05, lat=42.54),
        zoom=7,
    ),
)

# Create app layout
app.layout = html.Div(
    [
        dcc.Store(id="aggregate_data"),
        # empty Div to trigger javascript file for graph resizing
        html.Div(id="output-clientside"),
        html.Div(
            [
                html.Div(
                    [
                        html.Img(
                            src=app.get_asset_url("logo_fea_usp.gif"),
                            id="plotly-image",
                            style={
                                "height": "60px",
                                "width": "auto",
                                "margin-bottom": "25px",
                            },
                        )
                    ],
                    className="one-third column",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    "Matemática Atuarial Vida II",
                                    style={"margin-bottom": "0px"},
                                ),
                                html.H5(
                                    "Trabalho 1", style={"margin-top": "0px"}
                                ),
                                html.H6(
                                    "Acássio, Beth, Falcão, Kelvin, Lawrance, Murilo",
                                     style={"margin-top": "0px"}
                                ),
                            ]
                        )
                    ],
                    className="one-half column",
                    id="title",
                )
            ],
            id="header",
            className="row flex-display",
            style={"margin-bottom": "25px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Button(
                            'Calcular',
                            id = 'calc_button',
                            type='submit',
                        ),
                        html.P(
                            "Produto:",
                            className="control_label",
                        ),
                        dcc.Dropdown(
                            id="product_selector",
                            options = product_options,
                            clearable=False,
                            value=DEF_PRODUCT,
                            style={"width":"100%"}
                        ),
                        html.P("Sexo:",
                               className="control_label"),
                        dcc.Dropdown(
                            id="gender_selector",
                            options=gender_options,
                            value=DEF_GENDER,
                            clearable=False,
                            style={"width":"100%"}
                        ),
                        html.P("Idade:", className="control_label"),
                        dcc.Input(
                                id="age-input",
                                placeholder="Idade",
                                type="number",
                                min=0,
                                step=1,
                                value=1,
                                style={"width":"100%"}
                        ),
                        html.P("Tábua:",
                               className="control_label"),
                        dcc.Dropdown(
                            id="table_selector",
                            options=table_options,
                            value=DEF_TABLE,
                            clearable=False,
                            style={"width":"100%"}
                        ),
                        html.P("Taxa:", className="control_label"),
                        dcc.Input(
                                id="interest-rate-input",
                                type="number",
                                min=0,
                                max=1,
                                step=0.0001,
                                value=DEF_INTEREST_RATE,
                                style={"width":"100%"}
                        ),
                        html.Hr(style={"margin-bottom": "0.5em",
                                       "margin-top": "0.5em"}),
                        html.P("Benefício",
                               className="section-title"),
                        html.Div(
                            className="control-row-1",
                            children=[
                                html.Div(
                                    id="term-input-outer",
                                    children=[
                                        html.Label("Prazo", className="control_label"),
                                        dcc.Input(
                                            id="term-input",
                                            type="number",
                                            min=0,
                                            max=100,
                                            step=1,
                                            value=1,
                                            className="dcc_control"
                                        ),
                                    ],
                                ),
                                html.Div(
                                    id="dif-input-outer",
                                    children=[
                                        html.Label("Diferimento", className="control_label"),
                                        dcc.Input(
                                            id="dif-input",
                                            type="number",
                                            min=0,
                                            max=100,
                                            step=1,
                                            value=1,
                                            className="dcc_control"
                                        ),
                                    ],
                                ),
                                html.Div(
                                    id="value-selector-outer",
                                    children=[
                                        html.Label("Valor (R$)", className="control_label"),
                                        dcc.Input(
                                                id="value-input",
                                                type="number",
                                                min=1,
                                                value=1,
                                                className="dcc_control",
                                                style={"width":"100%"},
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            #className="control-row-1",
                            children=[
                                html.Div(
                                    className="control-row-1",
                                    children=[
                                        html.Div(
                                            id="antecip-select-outer",
                                            children=[
                                                dcc.Checklist(
                                                    id="antecip_selector",
                                                    options=[{"label": "Postecipado", "value": "locked"}],
                                                    className="dcc_control",
                                                    value=[],
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            id="whole-select-outer",
                                            children=[
                                                dcc.Checklist(
                                                    id="whole_life_selector",
                                                    options=[{"label": "Vitalício", "value": "locked", "disabled":True}],
                                                    className="dcc_control",
                                                    value=[],
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.Hr(style={"margin-bottom": "0.5em",
                                       "margin-top": "0.5em"}),
                        html.P("Pagamento",
                               className="section-title"),
                        html.Div(
                            className="control-row-1",
                            children=[
                                html.Div(
                                    id="term-p-input-outer",
                                    children=[
                                        html.Label("Prazo", className="control_label"),
                                        dcc.Input(
                                            id="term-p-input",
                                            type="number",
                                            min=0,
                                            max=100,
                                            step=1,
                                            value=1,
                                            style={"width":"100%"}
                                            #className="dcc_control"
                                        ),
                                    ],
                                ),
                                html.Div(
                                    id="dif-p-input-outer",
                                    children=[
                                        html.Label("Diferimento", className="control_label"),
                                        dcc.Input(
                                            id="dif-p-input",
                                            type="number",
                                            min=0,
                                            max=100,
                                            step=1,
                                            value=1,
                                            style={"width":"100%"}
                                            #className="dcc_control"
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            className="control-row-1",
                            children=[
                                html.Div(
                                    id="antecip-p-select-outer",
                                    children=[
                                        dcc.Checklist(
                                            id="antecip_p_selector",
                                            options=[{"label": "Postecipado", "value": "locked"}],
                                            className="dcc_control",
                                            value=[],
                                        ),
                                    ],
                                ),
                                html.Div(
                                    id="whole-p-select-outer",
                                    children=[
                                        dcc.Checklist(
                                            id="whole_p_life_selector",
                                            options=[{"label": "Vitalício", "value": "locked"}],
                                            className="dcc_control",
                                            value=[],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.Hr(style={"margin-bottom": "0.5em",
                                       "margin-top": "0.5em"}),
                        html.P("Reservas",
                               className="section-title"),
                                html.Div(
                                    className="control-row-1",
                                    children=[
                                html.Div(
                                    id="reserv-input-outer",
                                    children=[
                                        html.Label("Momento de avaliação (t)", className="control_label"),
                                        dcc.Input(
                                            id="reserv-input",
                                            type="number",
                                            min=0,
                                            max=100,
                                            step=1,
                                            value=0,
                                            debounce=True,
                                            style={"width":"100%"}
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                    className="pretty_container four columns",
                    id="cross-filter-options",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(id="product_text"), html.P("Produto")],
                                    id="product",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="product_value"), html.P("Valor")],
                                    id="prod_value",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="pnaText"), html.P("PNA")],
                                    id="pna",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="pupText"), html.P("PUP")],
                                    id="pup",
                                    className="mini_container",
                                ),
                            ],
                            id="info-container",
                            className="row container-display",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(id="reservpText"), html.P("Prospectivo")],
                                    id="reserv-prosp",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="reservrText"), html.P("Retrospectivo")],
                                    id="reserv-retro",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="paidupText"), html.P("Paid-Up")],
                                    id="paid-up-insur",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="extendedText"), html.P("Extended")],
                                    id="extended-insur",
                                    className="mini_container",
                                ),
                            ],
                            id="info-container2",
                            className="row container-display",
                        ),
                        html.Div(
                            [dcc.Graph(id="count_graph")],
                            id="countGraphContainer",
                            className="pretty_container",
                        ),
                    ],
                    id="right-column",
                    className="eight columns",
                ),
            ],
            className="row flex-display",
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="main_graph")],
                    className="pretty_container seven columns",
                ),
                html.Div(
                    [dcc.Graph(id="individual_graph")],
                    className="pretty_container five columns",
                ),
            ],
            className="row flex-display",
        ),
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
)

@app.callback(
    [
        Output("age-input", "max")
    ],
    [
        Input("gender_selector", "value"),
        Input("table_selector", "value")
    ]
)
def filter_dataframe(gender, table):
    max_age = df.query('gender == "{}" and table == "{}"'. \
                       format(gender, table))['age'].max()
    return [max_age]

@app.callback(
    [
        Output("whole_life_selector", "options")
    ],
    [
        Input("product_selector", "value")
    ]
)
def disable_whole_life(product):
    if product == 'D' or product == 'd':
        return [[{"label": "Vitalício", "value": "locked", 'disabled':True}]]
    else:
        return [[{"label": "Vitalício", "value": "locked"}]]

@app.callback(
    [
        Output("antecip_selector", "options")
    ],
    [
        Input("product_selector", "value")
    ]
)
def disable_post(product):
    if product == 'D' or product == 'd' or product == 'A':
        return [[{"label": "Postecipado", "value": "locked", "disabled":True}]]
    else:
        return [[{"label": "Postecipado", "value": "locked"}]]

@app.callback(
    [
        Output("dif-input", "disabled")
    ],
    [
        Input("product_selector", "value")
    ]
)
def disable_diferred(product):
    if product == 'd':
        return ['DISABLED']
    else:
        return [False]

@app.callback(
    [
        Output("product_text", "children"),
        Output("product_value", "children")
    ],
    [
        Input("product_selector", "value"),
        Input("value-input", "value")

    ]
)
def bind_prod_value(product, product_value):
    return [[PRODUCTS[product]],[real_br_money_mask(product_value)]]

@app.callback(
    [
        Output("pupText", "children"),
        Output("pnaText", "children"),
        Output("count_graph", "figure"),
        Output("reservpText", "children"),
        Output("reservrText", "children"),
        Output("main_graph", "figure"),
        Output("individual_graph", "figure"),
        Output("paidupText", "children"),
        Output("extendedText", "children")
    ],
    [
        Input("calc_button", "n_clicks"),
        Input("product_selector", "value"),
        Input("gender_selector", "value"),
        Input("age-input", "value"),
        Input("table_selector", "value"),
        Input("interest-rate-input", "value"),
        Input("term-input", "value"),
        Input("dif-input", "value"),
        Input("value-input", "value"),
        Input("antecip_selector", "value"),
        Input("whole_life_selector", "value"),
        Input("term-p-input", "value"),
        Input("dif-p-input", "value"),
        Input("antecip_p_selector", "value"),
        Input("whole_p_life_selector", "value"),
        Input("reserv-input", "value")
    ],
)
def update_value_click(nclicks, prod,
                       gender, age, table, i_rate,
                       term_bnf, dif_bnf, value_bnf,
                       postecip_bnf, whole_life_bnf,
                       term_pay, dif_pay, postecip_pay,
                       whole_life_pay, reserv_t):

    global main_fig
    global handler
    global reserve_chart
    global table_chart

    antecip_bnf = True
    antecip_pay = True

    if nclicks is None:
        nclicks = 0

    if nclicks != callbacks_vars.n_clicks[1]:
        handler.select_table(table, gender)
        handler.gen_commutations(i_rate)

        if whole_life_bnf:
            term_bnf = np.inf

        if whole_life_pay:
            term_pay = np.inf

        if postecip_bnf:
            antecip_bnf = False

        if postecip_pay:
            antecip_pay = False

        if prod == 'd':
            dif_bnf = 0

        try:
            handler.calc_premium(age=age,
                             dif_benef=dif_bnf,
                             term_benef=term_bnf,
                             antecip_benef=antecip_bnf,
                             prod=prod,
                             dif_pay=dif_pay,
                             term_pay=term_pay,
                             antecip_pay=antecip_pay)

            a = handler.calc_reserves(reserv_t, 'retrosp', i_rate)
            a = handler.calc_reserves(reserv_t, 'prosp', i_rate)

            main_fig = generate_main_plot(handler_copy=handler,
                                          dif_benef=dif_bnf,
                                          term_benef=term_bnf,
                                          product=prod,
                                          antecip_benef=antecip_bnf,
                                          value_bnf=value_bnf,
                                          dif_pay=dif_pay,
                                          term_pay=term_pay,
                                          antecip_pay=antecip_pay)

            table_chart = generate_tables_plot(handler_copy=handler,
                                     gender=gender, age=age,
                                     i_rate=i_rate, dif_bnf=dif_bnf,
                                     term_bnf = term_bnf,
                                     antecip_bnf = antecip_bnf,
                                     prod = prod,
                                     dif_pay = dif_pay,
                                     term_pay = term_pay,
                                     antecip_pay = antecip_pay,
                                     value_bnf = value_bnf)

            reserve_chart = generate_reserves_plot(handler_copy=handler,
                                                    value_bnf=value_bnf)


        except:
            pass

        callbacks_vars.update_n_clicks(nclicks, 1)

    v1 = handler.pup*value_bnf if handler.pup else 0
    v2 = handler.pna*value_bnf if handler.pna else 0
    r1 = handler.last_prosp_reserve*value_bnf \
                 if handler.last_prosp_reserve else 0
    r2 = handler.last_retro_reserve*value_bnf \
                 if handler.last_retro_reserve else 0

    s1 = handler.paidup*value_bnf if handler.paidup else 0
    s2 = handler.extended if handler.extended else [0]

    if len(s2) > 1:
        s2 = [str(s2[0]) + "/" + str(real_br_money_mask(s2[1]*value_bnf))]

    return [[real_br_money_mask(v1)], [real_br_money_mask(v2)],
             main_fig, [real_br_money_mask(r1)],
             [real_br_money_mask(r2)], reserve_chart, table_chart,
             [real_br_money_mask(s1)], s2]

# Main
if __name__ == "__main__":
    app.run_server(debug=True)
