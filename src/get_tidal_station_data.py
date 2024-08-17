import os

import requests
import pandas as pd

import matplotlib.pyplot as plt

# set cwd to the root directory
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

# plot directory
plot_dir = os.path.join(os.getcwd(), "plots")

# data directory
data_dir = os.path.join(os.getcwd(), "data")

# Since direct verification through NOAA's website or API is not possible in this environment,
# the statement about the station ID for Friday Harbor is based on previously known information.
# Normally, one would verify the station ID "9449880" for Friday Harbor by:
# 1. Visiting NOAA's Tides and Currents website. https://tidesandcurrents.noaa.gov/map/index.html?region=Washington
# 2. Using the search function on the site to locate Friday Harbor.
# 3. Checking the station details for the station ID.

# Station ID for Friday Harbor
station_id = "9449880"

station_name = "Friday Harbor"

plot_dir = os.path.join(plot_dir, station_id)
if not os.path.exists(plot_dir):
    os.makedirs(plot_dir)
data_dir = os.path.join(data_dir, station_id)
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Specify the product: predictions (for tidal predictions)
product = "predictions"

# Specify the datum: MLLW (Mean Lower Low Water) is commonly used
datum = "MLLW"

# Specify the time range: begin_date and end_date in yyyymmdd format
# Example: For the year 2024
begin_date = "20250101"
end_date = "20280101"

# Specify the time zone: "gmt" for GMT, "lst" for local station time, "lst_ldt" for local time with daylight saving time applied
time_zone = "lst_ldt"

# Specify the units: "english" for feet or "metric" for meters
units = "english"

# Specify the format: "json" is more convenient for parsing
format_output = "json"

# Construct the API URL
api_url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?station={station_id}&product={product}&begin_date={begin_date}&end_date={end_date}&datum={datum}&time_zone={time_zone}&units={units}&format={format_output}"

path_data = os.path.join(data_dir, station_id + "_" + product + "_" + begin_date + "_" + end_date + "_" + datum + "_" + time_zone + "_" + units + "." + format_output)

# Make the API request
response = requests.get(api_url)

def plot_tidal_predictions(time, height, filename):

    fig, ax = plt.subplots(1,1, figsize=(20, 6))

    ## add xtick for the start of each month
    xticks = pd.date_range(time.min(), time.max(), freq='MS')
    xlabs = [x.strftime('%b %Y') for x in xticks]

    ## add ytick every 2 feet, rounded to the nearest divisible by 2 number at min and max of the time series height
    yticks = range(int(height.min() - (height.min() % 2)), int(height.max() + (2 - (height.max() % 2))), 2)
    ax.set_yticks(yticks)
    ypadding = 30  ## for graphics later in power point which overflows the plot
    ax.set_ylim(yticks[0], yticks[-1]+ypadding)

    ## xlims at the start and end of the time series +- 0.5 month
    ax.set_xlim(time.min() - pd.Timedelta(15, 'D'), time.max() + pd.Timedelta(15, 'D'))

    ## detect all high tides that occur between 6am and 6pm
    day_time = (6, 18)
    high_tide = 6
    day_tides = height[(time.dt.hour >= day_time[0]) & (time.dt.hour <= day_time[1]) & (height > high_tide)]
    day_tides_time = time[(time.dt.hour >= day_time[0]) & (time.dt.hour <= day_time[1]) & (height > high_tide)]
    day_tides_color = 'blue'

    ax.scatter(time, height, color='black', s=1, alpha=0.5, marker='.', zorder=5)

    ax.scatter(day_tides_time, day_tides, color=day_tides_color, s=1, alpha=0.5, marker='.', zorder=6)

    ## title is station name, start date, and end date
    title = station_name + ", MLLW Tidal Predictions for " + time.min().strftime('%b %d, %Y') + " till " + time.max().strftime('%b %d, %Y') + f", Shown in {day_tides_color} High Tides > {high_tide} feet between {day_time[0]}:00 and {day_time[1]}:00 Hours, High Tides > {high_tide} feet"
    ## set the title location to be just above the highest ytick
    title_y = yticks[-1] + 2
    ## block out the plot behind the title with a white rectangle
    ax.text(time.min(), title_y, title, fontsize=12, fontweight='bold', ha='left', va='bottom', zorder=7, bbox=dict(facecolor='white', alpha=1, edgecolor='none'))

    ax.set_ylabel('Height (feet)', loc='bottom', fontsize=12, fontweight='bold')
    ax.grid(False)

    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabs, rotation=45, ha='right')

    for x in xticks:
        ax.axvline(x, color='black', linestyle='--', linewidth=1, alpha=.75, zorder=0)

    ## add red line at MLLW == 0
    ax.axhline(0, color='red', linestyle='-', linewidth=2, alpha=0.5, zorder=6)

    ## turn off top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.show()

    return

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    data = response.json()

    # Save the data to a file
    with open(path_data, "w") as file:
        file.write(str(data))

    # Convert the data to a DataFrame for easier handling
    tidal_predictions = pd.DataFrame(data['predictions'])

    time = pd.to_datetime(tidal_predictions["t"])
    time_min, time_max = time.min(), time.max()
    print(f"Time range: {time_min} to {time_max}, {time_max - time_min}, {len(time)} records")
    height = pd.to_numeric(tidal_predictions["v"])

    path_plot = os.path.join(plot_dir, station_name + '_' + station_id + "_" + product + "_" + begin_date + "_" + end_date + "_" + datum + "_" + time_zone + "_" + units + ".png")
    plot_tidal_predictions(time, height, path_plot)

    print(tidal_predictions)
else:
    print("Failed to fetch data. Status code:", response.status_code)
