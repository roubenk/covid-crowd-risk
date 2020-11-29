import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_daq as daq
from dash.dependencies import Input, Output, State
import requests
import re

external_stylesheets = [dbc.themes.BOOTSTRAP, "https://fonts.googleapis.com/css2?family=Lato&display=swap"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server


def get_county_info():
    # Get a dict of Calif. counties and their respective populations from the US Census
    url = "https://api.census.gov/data/2019/pep/population"
    params = {
        "get": "NAME,POP",
        "for": "county:*",
        "in": "state:06"  # 06 == California
    }
    resp = requests.get(url, params=params)
    #status = resp.status_code
    data = resp.json()
    # Create dictionary of county names and corresponding populations
    pops = {}
    for county in data[1:]:  # Skip header
        name = re.findall(".+?(?= County)", county[0])[0]  # Clean county name (i.e. "Yolo County, California" -> "Yolo")
        pop = int(county[1])
        pops[name] = pop
    # Create list of dicts of county names for dropwdown menu
    counties = pops.keys()
    counties = sorted(counties)
    menu = [{'label': county, 'value': county}
               for county in counties]
    return pops, menu


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
    #status = resp.status_code
    data = resp.json()
    cases = data['result']['records'][0]['sum']
    return int(cases)


COUNTY_POPS, COUNTY_MENU = get_county_info()

county_dropdown_label = html.Div(
    "Select your county"
)

county_dropdown = html.Div([
    dcc.Dropdown(
        id="county-dropdown",
        options=COUNTY_MENU,
        value="Los Angeles"
    )
])

attendees_label = html.Div(
    "",
    id="attendee-label"
)

attendees_slider = html.Div([
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

result_label = html.Div(
    html.H3(id="result-label")
)

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
    dbc.Container( # HEADER
        dbc.Row(dbc.Col([
            html.H1("Know Your COVID-19 Exposure Risk"),
            html.H5("Attending a gathering in California?"),
            html.H5("Find out the risk that at least one infected person will be present.")
            ])),
    className="header"
    ),
    dbc.Container(  # CALCULATOR
        dbc.Row([
            dbc.Col([
                dbc.Row(
                    dbc.Col(county_dropdown_label, width=7),
                    className="pb-2 justify-content-lg-end justify-content-center"),
                dbc.Row(
                    dbc.Col(county_dropdown, width=7),
                    className="pb-5 justify-content-lg-end justify-content-center"),
                dbc.Row(
                    dbc.Col(attendees_label, width=7),
                    className="pb-2 justify-content-lg-end justify-content-center"),
                dbc.Row(
                    dbc.Col(attendees_slider, width=7, className="pl-0 pr-0 "),
                    className="pb-5 justify-content-lg-end justify-content-center")
            ], lg=True
            ),
            dbc.Col(
                dbc.Row([
                    dbc.Col(result, width={"size": 2, "offset": 2}),
                    dbc.Col(result_label, width=4)
                ],
                className="justify-content-lg-start justify-content-center",
                align="center"
                ),
                lg=True
            )
        ],
        justify="center"
        ),
    className="calculator"
    ),
    dbc.Container(  # DESCRIPTION
        dbc.Row(dbc.Col([
            html.H5("What is this?"),
            html.P([
                html.Span(
                    "This calcaulator measures the probability that at least one person " \
                    "with a COVID-19 infection will be in attendance at a gathering."
                ),
                html.Br(),
                html.Span(
                    "The calculation is based on the prevalence of active COVID-19 " \
                    "cases in each California county and the number of people in " \
                    "attendance."
                ),
                html.Br(),
                html.Span("The following formula determines the probability:  "),
                html.Img(src="assets/images/eqn.png", style={"padding-left": 10}),
                html.Span(".")
            ])
        ])),
    className="description"
    ),
    dbc.Container(  # FOOTER
        dbc.Row([
            dbc.Col(
                html.P("Data from the State of California and the US Census Bureau"),
                className="col-lg-auto",
                align="end",
                style={"text-align": "left"},
            ),
            dbc.Col(
                html.P("Icon and image attributions"),
                lg=True,
                align="end",
                style={"text-align": "center"},
            ),
            dbc.Col(
                html.P("Created by Rouben K."),
                lg=True,
                align="end",
                style={"text-align": "right"},
            )
        ]),
    className="footer",
    fluid=False
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
    population = COUNTY_POPS.get(county)  # Safetly get value from dictionary (returns None if item not found)
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
