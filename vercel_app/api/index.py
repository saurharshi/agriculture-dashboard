import pandas as pd
import numpy as np
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeSwitchAIO
import plotly.express as px
import os

# Load data from local CSV instead of Oracle
csv_path = os.path.join(os.path.dirname(__file__), '..', 'dataset', 'crop_production.csv')
df = pd.read_csv(csv_path)

# Pre-calculate categories
if 'CATEGORY' not in df.columns:
    df["CATEGORY"] = np.where(df["PRODUCTION_TON"] > 80000, "High Production", "Normal Production")

# Vercel requires WSGI application server
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.MINTY], title="Agricultural Dashboard")
server = app.server

theme_switch = ThemeSwitchAIO(
    aio_id="theme", 
    themes=[dbc.themes.MINTY, dbc.themes.CYBORG]
)

# Tab 1: Analytics Dashboard Layout (Data Entry tab removed for static hosting)
analytics_layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("🌱 Select a Crop to Analyze:", className="fw-bold fs-5 text-success mb-2"),
                dcc.Dropdown(
                    id='crop-filter',
                    options=[{'label': crop, 'value': crop} for crop in df['CROP_NAME'].unique()] if not df.empty else [],
                    value=df['CROP_NAME'].unique()[0] if not df.empty else None,
                    clearable=False,
                    className="shadow-sm text-dark"
                )
            ], className="p-3 rounded shadow-sm border border-success border-opacity-25", style={"backgroundColor": "var(--bs-card-bg)"})
        ], width=12, md=6, lg=4)
    ], className="mb-4"),

    dbc.Row(id='metrics-cards', className="mb-4"),

    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='production-bar'), className="shadow-sm mb-4 border-0"), width=12, lg=6),
        dbc.Col(dbc.Card(dcc.Graph(id='yield-histogram'), className="shadow-sm mb-4 border-0"), width=12, lg=6)
    ], className="mb-2"),

    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='rainfall-scatter'), className="shadow-sm mb-4 border-0"), width=12, lg=6),
        dbc.Col(dbc.Card(dcc.Graph(id='production-pie'), className="shadow-sm mb-4 border-0"), width=12, lg=6)
    ], className="mb-5")
])

app.layout = dbc.Container([
    # Header Section
    dbc.Row([
        dbc.Col(
            html.Img(src="/assets/logo.png", height="80px", className="mb-2"),
            width="auto", className="d-flex align-items-center"
        ),
        dbc.Col([
            html.H1("Jharkhand Agricultural Dashboard", className="text-success fw-bold"),
            html.P("Explore district-wise crop data! (Read-Only Cloud Mode)", className="lead text-muted")
        ], className="d-flex flex-column justify-content-center"),
        dbc.Col([
            html.Div(theme_switch, className="d-flex justify-content-end")
        ], width="auto", className="d-flex align-items-center ms-auto")
    ], className="mt-4 mb-4 align-items-center p-4 rounded shadow-sm", style={"backgroundColor": "var(--bs-card-bg)"}),
    
    analytics_layout
    
], fluid=True, className="pb-5", style={"minHeight": "100vh"})


@app.callback(
    [Output('metrics-cards', 'children'),
     Output('production-bar', 'figure'),
     Output('yield-histogram', 'figure'),
     Output('rainfall-scatter', 'figure'),
     Output('production-pie', 'figure')],
    [Input('crop-filter', 'value'),
     Input(ThemeSwitchAIO.ids.switch("theme"), "value")]
)
def update_dashboard(selected_crop, toggle):
    chart_template = 'plotly_white' if toggle else 'plotly_dark'
    
    if df.empty or selected_crop not in df['CROP_NAME'].values:
        empty_fig = px.bar(title="No Data Available")
        empty_fig.layout.template = chart_template
        return html.Div("No data available for this crop.", className="text-danger"), empty_fig, empty_fig, empty_fig, empty_fig
        
    filtered_df = df[df['CROP_NAME'] == selected_crop]
    
    total_prod = f"{filtered_df['PRODUCTION_TON'].sum():,.0f} Tons"
    avg_yield = f"{filtered_df['YIELD'].mean():.2f}"
    avg_rain = f"{filtered_df['RAINFALL'].mean():.0f} mm"
    
    cards = [
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("🌾 Total Production", className="card-title text-muted fw-bold"),
            html.H2(total_prod, className="text-success fw-bold")
        ]), className="shadow-sm border-success border-start border-5"), width=12, md=4, className="mb-3"),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("📈 Average Yield", className="card-title text-muted fw-bold"),
            html.H2(avg_yield, className="text-info fw-bold")
        ]), className="shadow-sm border-info border-start border-5"), width=12, md=4, className="mb-3"),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("🌧️ Average Rainfall", className="card-title text-muted fw-bold"),
            html.H2(avg_rain, className="text-primary fw-bold")
        ]), className="shadow-sm border-primary border-start border-5"), width=12, md=4, className="mb-3")
    ]
    
    district_prod = filtered_df.groupby("DISTRICT_NAME")["PRODUCTION_TON"].sum().reset_index()
    fig_bar = px.bar(district_prod, x="DISTRICT_NAME", y="PRODUCTION_TON", 
                     title=f"🏆 District-wise Production for {selected_crop}",
                     labels={"DISTRICT_NAME": "District", "PRODUCTION_TON": "Production (Ton)"},
                     template=chart_template, color_discrete_sequence=['#20c997'])
    
    fig_hist = px.histogram(filtered_df, x="YIELD", nbins=6, 
                            title=f"📊 Yield Distribution for {selected_crop}",
                            labels={"YIELD": "Yield"},
                            template=chart_template, color_discrete_sequence=['#fd7e14'])

    fig_scatter = px.scatter(filtered_df, x="RAINFALL", y="PRODUCTION_TON", color="DISTRICT_NAME",
                             size="AREA_HECTARE",
                             title=f"💧 Rainfall vs Production ({selected_crop})",
                             labels={"RAINFALL": "Rainfall (mm)", "PRODUCTION_TON": "Production (Ton)"},
                             template=chart_template)

    cat_prod = filtered_df.groupby("CATEGORY")["PRODUCTION_TON"].sum().reset_index()
    fig_pie = px.pie(cat_prod, values="PRODUCTION_TON", names="CATEGORY",
                     title=f"🥧 Production Categories for {selected_crop}",
                     template=chart_template, hole=0.4, color_discrete_sequence=['#6610f2', '#0dcaf0'])
                     
    for fig in [fig_bar, fig_hist, fig_scatter, fig_pie]:
        fig.update_layout(
            margin=dict(t=60, l=40, r=40, b=40),
            title_font=dict(size=18, family="Arial")
        )

    return cards, fig_bar, fig_hist, fig_scatter, fig_pie
