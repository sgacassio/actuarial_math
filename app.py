# Import required libraries
import pickle
import copy
import pathlib
import dash
import math
import datetime as dt
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State, ClientsideFunction
import dash_core_components as dcc
import dash_html_components as html

# Multi-dropdown options
from controls import PRODUCTS, DEF_PRODUCT, GENDER, DEF_GENDER

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("data").resolve()

app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
)
server = app.server

# Create controls
df = pd.read_excel(DATA_PATH.joinpath("life_tables.xlsx"))
df_interest = pd.read_excel(DATA_PATH.joinpath("risk_free.xlsx"))

DEF_INTEREST_RATE = df_interest[df_interest['month'] \
                                == df_interest['month'].\
                                max()]['selic_year'].values[0]/100

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
                                    id="period-selector-outer",
                                    children=[
                                        html.Label("Valor (R$)", className="control_label"),
                                        dcc.Input(
                                                id="value-input",
                                                type="number",
                                                min=1,
                                                value=1,
                                                className="dcc_control"
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            #className="control-row-1",
                            children=[
                                html.Div(
                                    id="value-input-outer",
                                    children=[
                                        html.Label("Periodicidade", className="control_label"),
                                        dcc.Dropdown(
                                                id="period_selector",
                                                options=[{"value":1, 'label':"Único"},
                                                         {"value":2, 'label':"Mensal"},
                                                         {"value":3, 'label':"Anual"}],
                                                value=3,
                                                clearable=False,
                                                className="dcc_control",
                                        ),
                                    ],
                                ),
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
                                                    options=[{"label": "Vitalício", "value": "locked"}],
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
                            #className="control-row-1",
                            children=[
                                html.Div(
                                    id="term-p-input-outer",
                                    children=[
                                        html.Label("Prazo", className="control_label"),
                                        dcc.Input(
                                            id="term-p-input",
                                            type="number",
                                            placeholder="Prazo Pagto",
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
                    ],
                    className="pretty_container four columns",
                    id="cross-filter-options",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(id="well_text"), html.P("Produto")],
                                    id="wells",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="gasText"), html.P("Valor (R$)")],
                                    id="gas",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="oilText"), html.P("PNA")],
                                    id="oil",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="waterText"), html.P("PUP")],
                                    id="water",
                                    className="mini_container",
                                ),
                            ],
                            id="info-container",
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
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="pie_graph")],
                    className="pretty_container seven columns",
                ),
                html.Div(
                    [dcc.Graph(id="aggregate_graph")],
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
        Output("well_text", "children"),
    ],
    [Input("product_selector", "value")],
)
def update_product_text(product):
    return [PRODUCTS[product]]

@app.callback(
    [
        Output("gasText", "children"),
    ],
    [Input("value-input", "value")],
)
def update_value_text(value):
    return ["R$ " + str(value)]

@app.callback(
[
Output("count_graph", "figure"),
],
[Input("value-input", "value")],
)
def update_chart(value):
    fig = go.Figure(go.Surface(
    contours = {
        "x": {"show": True, "start": 1.5, "end": 2, "size": 0.04, "color":"white"},
        "z": {"show": True, "start": 0.5, "end": 0.8, "size": 0.05}
    },
    x = [1,2,3,4,5],
    y = [1,2,3,4,5],
    z = [
        [0, 1, 0, 1, 0],
        [1, 0, 1, 0, 1],
        [0, 1, 0, 1, 0],
        [1, 0, 1, 0, 1],
        [0, 1, 0, 1, 0]
    ]))
    fig.update_layout(
        scene = {
            "xaxis": {"nticks": 20},
            "zaxis": {"nticks": 4},
            'camera_eye': {"x": 0, "y": -1, "z": 0.5},
            "aspectratio": {"x": 1, "y": 1, "z": 0.2}
        })
    return [fig]
# Helper functions

def df_filter(table, gender):
    '''
    Input: table name, gender
    Output: Filtered dataframe according to the
            selected life table and gender
    '''
    #Build a query string
    query = 'gender == "{}" and table == "{}"'.\
             format(gender, table)

    #Apply a filter and reset the index of the original dataframe
    df_temp = df.query(query).\
                 reset_index(drop=True).copy()
    return df_temp

def pv_calc(i_rate, n):
    '''
    Input: Interest rate, array of periods [0,1,2,3,...]
    Ouput: Array of v's
    '''
    return 1/(1+i_rate)**n

def calc_Dx(age, lx, i_rate):
    '''
    Input: Array of ages, array with the number of survivals,
           interest rate
    Output: Array of commutation Dx for all ages available in the
            life table
    '''
    return lx*pv_calc(i_rate, age)

def calc_Cx(age, dx, i_rate):
    '''
    Input: Array of ages, array with the number of deaths,
               interest rate
    Output: Array of commutation Cx for all ages available in the
            life table
    '''
    age_ = age + 1
    return dx*pv_calc(i_rate, age_)

def calc_Mx(Cx, ini=0):
    '''
    Input: Array with commutation Cx for all ages
    Output: Array with commutation Mx for all ages
    '''
    size = Cx.shape[0]
    if ini > size - 1:
        return 0
    else:
        Cx_ = Cx[ini:].copy()
        return Cx_[::-1].cumsum()[::-1]

def calc_Nx(Dx, ini=0):
    '''
    Input: Array with commutation Dx for all ages
    Output: Array with commutation Nx for all ages
    '''
    size = Dx.shape[0]
    if ini > size - 1:
        return 0
    else:
        Dx_ = Dx[ini:].copy()
        return Dx_[::-1].cumsum()[::-1]

def commut_calc(df, i_rate, which="Dx"):
    '''
    Input: Dataframe with life table (lx and dx must be already
           calculated), interest rate, commutation (Dx o Cx)
    Output: Array with either Dx or Cx calculated for all ages
           available in the life table
    '''
    age = df['age'].values
    lx = df['lx'].values
    dx = df['dx'].values

    if which == "Dx":
        return calc_Dx(age, lx, i_rate)
    elif which == "Cx":
        return calc_Cx(age, dx, i_rate)
# Main
if __name__ == "__main__":
    app.run_server(debug=True)
