from flask import Flask, render_template, make_response, request
import pandas as pd
import numpy as np
import matplotlib as mpl
import datetime
from io import BytesIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

app = Flask(__name__, template_folder='templates')


def generateCountryPlot(country):
    """Return image with COVID-19 plot for given country.

    Description
    -----------
    Return the figure of a the COVID-19 matplotlib chart for the given country.

    Parameters
    ----------
    1.  `country` (str) - Name of country for which to produce COVID-19 chart


    Return Value
    ------------
    Matplotlib figure of COVID-19 plot
    """
    dfCases = covidDict['cases'][country]
    dfDeaths = covidDict['deaths'][country]
    dfRecoveries = covidDict['recoveries'][country]
    dfActive = covidDict['active'][country]

    # Pack data into dataframe
    df = pd.DataFrame({'Cases': dfCases,
                       'Deaths': dfDeaths,
                       'Recoveries': dfRecoveries,
                       'Active': dfActive
                       },
                      index=pd.Index(dfCases.index.values, name='Date')
                      )

    # Generate plot using Pandas' integratio with matplotlib
    aPlot = df.plot(figsize=(5, 4))

    # Set chart's title
    aPlot.set_title('COVID-19 stats for ' + country)

    # Reformat yaxis using commas to group digits
    aPlot.yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter('{x:20,.0f}'))

    # Set reference to figure
    aPlot.get_figure().set_dpi(100)

    # Return image
    return aPlot.get_figure()


def getCovid19Data():
    """Return dataframes dict with COVID-19 country time series.

    Description
    -----------
    Pulls COVID-19 statistics from a web repository.  It parses the stats
    into four dataframes: diagnosed cases, deaths, recoveries, and active
    cases.  Each dataframe represents the historical stats for a bunch of
    countries.  Country names are the column headers and dates the index
    of each of the four dataframes.

    Return Value
    ------------
    Dictionary indexed by: cases, deaths, recoveries, active, and date.
    Key date is used to store the datetime of the datasets. This is used
    to determine if the data sets must be redownloaded.
    """
    # Specify sources for datasets
    # All data from https://data.humdata.org/dataset/novel-coronavirus-2019-ncov-cases
    # Set URL sources for individual datasets (cases, deaths, and recoveries)
    baseUrl = 'https://data.humdata.org/hxlproxy/api/data-preview.csv?url=https%3A%2F%2Fraw.githubusercontent.com%2FCSSEGISandData%2FCOVID-19%2Fmaster%2Fcsse_covid_19_data%2Fcsse_covid_19_time_series%2F'
    casesSrc = baseUrl+'time_series_covid19_confirmed_global.csv&filename=time_series_covid19_confirmed_global.csv'
    deathsSrc = baseUrl+'time_series_covid19_deaths_global.csv&filename=time_series_covid19_deaths_global.csv'
    recoveriesSrc = baseUrl+'time_series_covid19_recovered_global.csv&filename=time_series_covid19_recovered_global.csv'

    # Request datasets
    dfCases, dfDeaths, dfRecoveries = map(pd.read_csv,
                                          [casesSrc, deathsSrc, recoveriesSrc]
                                          )

    # Drop columns 'Lat', and 'Long'
    dfCases, dfDeaths, dfRecoveries = map(lambda x: x.drop(['Lat', 'Long'], axis=1),
                                          [dfCases, dfDeaths, dfRecoveries]
                                          )

    # Sum all Province/State rows corresponding to the same Country/Region
    # so each country's total appears in a single row
    dfCases, dfDeaths, dfRecoveries = map(lambda x: x.groupby(by='Country/Region').sum(),
                                          [dfCases, dfDeaths, dfRecoveries]
                                          )
    # Transpose the datasets so dates run along the vertical axis.
    dfCases, dfDeaths, dfRecoveries = map(lambda x: x.T,
                                          [dfCases, dfDeaths, dfRecoveries]
                                          )

    return {'cases': dfCases,
            'deaths': dfDeaths,
            'recoveries': dfRecoveries,
            'active': dfCases-dfDeaths-dfRecoveries,
            'date': datetime.date.today()
            }


def encodePlot(aPlot):
    """Encode a matplotlib plot for HTML display.

    Description
    -----------
    Converts a matplotlib figure into a byte array. This array is suitable
    for display in an HTML page.

    Parameters
    ----------
    1.  `aPlot` (matplotlib figure)

    Return Value
    ------------
    Byte array representation of a matplotlib figure
    """
    canvas = FigureCanvas(aPlot)
    png_output = BytesIO()
    canvas.print_png(png_output)

    return png_output.getvalue()


def getCountryData(countryName, numberOfDays):
    """Returns HTML formatted dataframe with requested data."""
    dfCases = covidDict['cases'][countryName]
    dfDeaths = covidDict['deaths'][countryName]
    dfRecoveries = covidDict['recoveries'][countryName]
    dfActive = covidDict['active'][countryName]

    # Pack data into dataframe
    df = pd.DataFrame({'Cases': dfCases,
                       'Deaths': dfDeaths,
                       'Recoveries': dfRecoveries,
                       'Active': dfActive
                       },
                      index=pd.Index(dfCases.index.values, name='Date')
                      ).tail(numberOfDays)

    return df.applymap(lambda x: '{:,.0f}'.format(x))\
             .reset_index()\
             .style\
             .hide_index()\
             .set_table_attributes('class="BorderCollapse"')\
             .set_table_styles([dict(selector="th",
                                     props=[("text-align", "center"),
                                            ("color", "black"),
                                            ("padding-left", "5px"),
                                            ("padding-right", "5px"),
                                            ("padding-top", "2px"),
                                            ("padding-bottom", "2px"),
                                            ("border", "1px dotted black")
                                            ]
                                     ),
                                dict(selector="tr:nth-child(even)",
                                     props=[("background-color", "lightyellow")]
                                     ),

                                ]
                               )\
             .set_properties(subset=['Date', 'Cases', 'Deaths', 'Recoveries',
                                     'Active'
                                     ],
                             **{'border': '1px dotted black',
                                'text-align': 'right',
                                'padding-left': '5px',
                                'padding-right': '5px',
                                'padding-top': '2px',
                                'padding-bottom': '2px'
                                }
                             ).render()


@app.route('/getCountryChart/<string:countryName>', methods=['GET'])
def getCountryChart(countryName):
    """Returns a plot to embed in an HTML page.

    Description
    -----------
    URL endpoint used as the source for `img` elements in the template
    used by the app.  The output of this function will display beautifully
    in HTML.

    Parameters
    ----------
    1.  `countryName` (str) - Name of country for which to produce
        COVID-19 chart

    Return Value
    ------------
    Byte array representation of COVID-19 chart generated by matplotlib
    """
    encodedPlot = encodePlot(generateCountryPlot(countryName))

    response = make_response(encodedPlot)
    response.headers['Content-Type'] = 'image/png'

    return response


@app.route('/', methods=['POST', 'GET'])
def index():
    if datetime.date.today() != covidDict['date']:
        df = getCovid19Data()
        covidDict['cases'] = df['cases']
        covidDict['deaths'] = df['deaths']
        covidDict['recoveries'] = df['recoveries']
        covidDict['active'] = df['active']
        covidDict['date'] = df['date']

    if request.method == 'POST':
        selectedCountry = request.form.get('SelectedCountry')

        return render_template('Covid19Dashboard.html',
                               defaultCountry=selectedCountry,
                               defaultCountryData=getCountryData(selectedCountry,
                                                                 28
                                                                 ),
                               countryNames=covidDict['cases'].columns.to_list()
                               )
    else:
        selectedCountry = 'Malta'

        return render_template('Covid19Dashboard.html',
                               defaultCountry=selectedCountry,
                               defaultCountryData = getCountryData(selectedCountry,
                                                                   28
                                                                   ),
                               countryNames = covidDict['cases'].columns.to_list()
                               )


# Load data into global variable
covidDict = getCovid19Data()


if __name__ == '__main__':
    # Run flask app
    app.run(debug=True, use_reloader=True)
