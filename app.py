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
    dcc.Dropdown(
        id="county-dropdown",
        options=COUNTY_OPTIONS,
        value="Los Angeles"
    )
])

attendees = html.Div([
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
    dbc.Container(
        dbc.Row([
            dbc.Col([
                dbc.Row(dbc.Col(county_dropdown)),
                dbc.Row(dbc.Col(attendees))
            ]),
            dbc.Col(result)
        ])
    )
])


@app.callback(
    Output("result-thermometer", "value"),
    [Input("county-dropdown", "value"),
     Input("attendee-slider", "value")]
)
def update_result(county, attendees):
    attendees = 10**attendees
    print("Attendees: ", attendees)
    population = COUNTY_POPS[county]
    print("Population: ", population)
    cases = get_covid_data(county)
    print("Cases: ", cases)
    prevalence = round(cases/population, 3)
    print(prevalence)
    risk = (1-((1-(prevalence))**attendees))*100  # Percent
    risk = round(risk, 2)
    print(risk)
    return risk


if __name__ == '__main__':
    app.run_server(debug=True)
