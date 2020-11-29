import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_daq as daq
from dash.dependencies import Input, Output, State
import requests
import re

external_stylesheets = [dbc.themes.BOOTSTRAP]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server


def get_counties():
    # Get list of Calif. counties from CA.gov database API
    url = "https://data.ca.gov/api/3/action/datastore_search_sql"
    params = dict(
        sql = "SELECT DISTINCT(county) FROM \"926fd08f-cc91-4828-af38-bd45de97f8c3\""
    )
    resp = requests.get(url, params=params)
    data = resp.json()
    counties = data['result']['records']
    options = [{'label': county['county'], 'value': county['county']}
               for county in counties]
    return options


def get_county_pops():
    # Get a dict of counties and their respective populations from the US Census
    url = "https://api.census.gov/data/2019/pep/population"
    params = {
        "get": "NAME,POP",
        "for": "county:*",
        "in": "state:06"  # 06 == California
    }
    resp = requests.get(url, params=params)
    status = resp.status_code
    data = resp.json()
    # Create dictionary of county names and populations
    pops = {}
    for county in data[1:]:  # Skip header
        name = re.findall(".+?(?= County)", county[0])[0]
        pop = int(county[1])
        pops[name] = pop
    return pops


def get_covid_data(county):
    # Get COVID-19 case data from CA.gov database API
    url = "https://data.ca.gov/api/3/action/datastore_search_sql"
    params = dict(
        sql = """
                SELECT SUM(newcountconfirmed)
                FROM \"926fd08f-cc91-4828-af38-bd45de97f8c3\"
                WHERE date > CURRENT_DATE - INTERVAL '14 day' AND
                      county = '{county}'
              """.format(county=county)
    )
    resp = requests.get(url, params=params)
    status = resp.status_code
    data = resp.json()
    cases = data['result']['records'][0]['sum']
    return int(cases)


COUNTY_OPTIONS = get_counties()
COUNTY_POPS = get_county_pops()

county_dropdown = html.Div([
    html.Div("Select your county"),
    dcc.Dropdown(
        id="county-dropdown",
        options=COUNTY_OPTIONS,
        value="Los Angeles"
    )
])

attendees = html.Div([
    html.Div(
        "",
        id="attendee-label"
    ),
    dcc.Slider(
        id="attendee-slider",
        marks={i: '{}'.format(10 ** i) for i in range(4)},
        min=0,
        max=3,
        value=1,
        step=0.01,
        updatemode="drag"
    )
])

result = html.Div(
    daq.Thermometer(
        id="result-thermometer",
        value=0,
        min=0,
        max=100
    )
)


app.layout = html.Div([
    html.Div(id="cases", hidden=True),  # Hidden div to hold number of cases
    dbc.Container(
        dbc.Row([
            dbc.Col([
                dbc.Row(dbc.Col(county_dropdown)),
                dbc.Row(dbc.Col(attendees))
            ]),
            dbc.Col(
                dbc.Row([
                    dbc.Col(result),
                    dbc.Col(html.H3(id="result-label"))
                ])
            )
        ])
    )
])


@app.callback(
    [Output("result-thermometer", "value"),
     Output("result-label", "children"),
     Output("cases", "children")],
    [Input("county-dropdown", "value"),
     Input("attendee-slider", "value")],
    [State("cases", "children")]
)
def update_result(county, attendees, cases):
    ctx = dash.callback_context
    if ctx.triggered[0]['prop_id'].split('.')[0] == "county-dropdown" or cases is None:
        cases = get_covid_data(county)
    attendees = round(10**attendees)
    population = COUNTY_POPS[county]
    prevalence = round(cases/population, 3)
    risk = (1-((1-(prevalence))**attendees))*100  # Percent
    risk = round(risk, 2)
    label = "{}".format(str(risk) + " %")
    return risk, label, cases


@app.callback(
    Output("attendee-label", "children"),
    [Input("attendee-slider", "value")]
)
def update_attendee_label(attendees):
    attendees = round(10**attendees)
    people = "people"
    if attendees == 1:
        people = "person (just yourself)"
    label = "{number} {people} attending".format(number=attendees, people=people)
    return label


if __name__ == '__main__':
    app.run_server(debug=True)
