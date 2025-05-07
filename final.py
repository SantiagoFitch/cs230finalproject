import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
import plotly.express as px

#load the csv file
df = pd.read_csv("airports.csv")

#remove rows that are missing important values
df = df.dropna(subset=['latitude_deg', 'longitude_deg', 'iso_region'])

#rename state codes to full names
state_names = {
    'US-CT': 'Connecticut',
    'US-ME': 'Maine',
    'US-MA': 'Massachusetts',
    'US-NH': 'New Hampshire',
    'US-RI': 'Rhode Island',
    'US-VT': 'Vermont'
}

#map the state codes to state names
df['State'] = df['iso_region'].map(state_names)

#keep only airports in new england
df = df[df['State'].notnull()]

#(PY1): function with two parameters, one default value
def filter_scheduled(data, scheduled=True):
    if scheduled:
        return data[data['scheduled_service'] == 'yes']
    else:
        return data

#(PY2): function that returns multiple values
def elevation_stats(data):
    return data['elevation_ft'].min(), data['elevation_ft'].max(), data['elevation_ft'].mean()

#(PY3): error checking
try:
    df['elevation_ft'] = df['elevation_ft'].astype(float)
except Exception as e:
    st.error("Error converting elevation to float: " + str(e))

#(PY4): list comprehension
airport_names = [name for name in df['name'] if isinstance(name, str)]

#sidebar (ST4)
st.set_page_config(page_title="New England Airports", layout="wide")
st.sidebar.title("About This App")
st.sidebar.write("This is an app to explore airport data.")

#state input (ST1)
state = st.selectbox("Choose a New England state", list(state_names.values()))

#checkbox for showing only scheduled flights (ST2)
show_scheduled = st.checkbox("Show only airports with scheduled flights.")

#slider to pick the minimum elevation (ST3)
min_elevation = st.slider("Minimum elevation (ft)", 0, 5000, 0)

#multi-select for airport types
airport_types = st.multiselect("Select airport types to include", df['type'].unique(), default=list(df['type'].unique()))

#filter by selected state
filtered = df[df['State'] == state]

#use the filter function twice (PY1)
filtered = filter_scheduled(filtered, show_scheduled)
filtered_all = filter_scheduled(df)

#filter by elevation (DA1)
filtered = filtered[filtered['elevation_ft'] >= min_elevation]

#filter by airport type (DA1)
filtered = filtered[filtered['type'].isin(airport_types)]

#remove rows that are missing coordinates
filtered = filtered.dropna(subset=['latitude_deg', 'longitude_deg'])

#sort by elevation (DA2)
filtered = filtered.sort_values(by='elevation_ft', ascending=False)

#(DA3): find min & max elevation
min_elev, max_elev, avg_elev = elevation_stats(filtered)
st.write(f"Minimum Elevation: {min_elev} ft")
st.write(f"Maximum Elevation: {max_elev} ft")
st.write(f"Average Elevation: {round(avg_elev, 2)} ft")

#(DA4): create new column
def elevation_level(row):
    if row['elevation_ft'] >= 2000:
        return "High"
    elif row['elevation_ft'] >= 1000:
        return "Medium"
    else:
        return "Low"

filtered['Elevation Category'] = filtered.apply(elevation_level, axis=1)

#(DA5): group by airport type
type_counts = filtered.groupby('type').size().reset_index(name='count')

#(DA6): iterate through rows (Assisted by AI)
for index, row in filtered.head(1).iterrows():
    st.write(f"Sample Airport: {row['name']} in {row['municipality']}")

#bar chart of airport types (VIZ1)
st.subheader("Types of Airports in " + state)
st.bar_chart(type_counts.set_index('type'))

#pie chart of airport types (AI-assisted, VIZ2)
if not filtered.empty:
    pie = alt.Chart(type_counts).mark_arc().encode(
        theta='count',
        color='type',
        tooltip=['type', 'count']
    ).properties(title="Pie Chart of Airport Types")
    st.altair_chart(pie, use_container_width=True)

#elevation line chart (AI-assisted, VIZ3)
if not filtered.empty:
    st.subheader("Airport Elevations (ft)")
    line_data = filtered.sort_values('elevation_ft')
    line = alt.Chart(line_data).mark_line(point=True).encode(
        x='name:N',
        y='elevation_ft:Q',
        tooltip=['name', 'elevation_ft']
    ).properties(width=700, title="Elevation Line Chart").interactive()
    st.altair_chart(line, use_container_width=True)

#plotly chart (AI assisted, VIZ4)
if not filtered.empty:
    st.subheader("Elevation Distribution by Type (Plotly)")
    fig = px.box(filtered, x="type", y="elevation_ft", color="type")
    st.plotly_chart(fig, use_container_width=True)

#row number selection
row_num = st.slider("How many airport rows to show?", 1, 20, 5)
st.subheader("Airport Table")
st.dataframe(filtered[['name', 'municipality', 'type', 'elevation_ft', 'scheduled_service']].head(row_num))

#airport name search (#AI assisted)
search_term = st.text_input("Search for an airport by name")
if search_term:
    result = filtered[filtered['name'].str.contains(search_term, case=False, na=False)]
    st.subheader("Search Results")
    st.dataframe(result[['name', 'municipality', 'type']])

#(AI-assisted) map of airports
if not filtered.empty:
    st.subheader("Map of Airports")
    map_data = filtered[['latitude_deg', 'longitude_deg', 'name', 'municipality', 'elevation_ft']].copy()
    map_data = map_data.rename(columns={
        'latitude_deg': 'lat',
        'longitude_deg': 'lon',
        'name': 'Airport Name',
        'municipality': 'City',
        'elevation_ft': 'Elevation (ft)'
    })
    view = pdk.ViewState(
        latitude=map_data['lat'].mean(),
        longitude=map_data['lon'].mean(),
        zoom=6,
        pitch=0
    )
    dot_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position='[lon, lat]',
        get_radius=3000,
        get_color=[255, 100, 0],
        pickable=True
    )
    tooltip = {
        "html": """
        <b>{Airport Name}</b><br/>
        City: {City}<br/>
        Elevation: {Elevation (ft)} ft<br/>
        Latitude: {lat}<br/>
        Longitude: {lon}
        """,
        "style": {"backgroundColor": "steelblue", "color": "white"}
    }
    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view,
        layers=[dot_layer],
        tooltip=tooltip
    ))
else:
    st.subheader("No airports match the current filters.")

#totals
st.write("Total airports shown:", len(filtered))
st.write("Number of airport types:", filtered['type'].nunique())

#average latitude
if not filtered.empty:
    st.write("Average latitude:", round(filtered['latitude_deg'].mean(), 4))
