import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import datetime

from main import download_station_data_logic, process_stream_logic, detect_phases_logic, download_catalogue_logic, match_events_logic, generate_report_logic, send_email_logic
from station import Station
from stream_processing import save_stream

# 创建 Dash 应用
GUI = dash.Dash(__name__)
GUI.title = "Earthquake Identification And Report"  # 设置网页标题
GUI.config.suppress_callback_exceptions = True

# 用于存储全局 Station、Catalog 对象和 p_only 变量的变量
global_station = None
global_catalog = None
global_report = None
global_p_only = None

# 获取今天的日期的前一天
yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

# 定义应用布局
GUI.layout = html.Div([
    html.H1("Earthquake Report Generator"),
    html.Div(className='container', children=[
        html.Div(className='section', children=[
            html.Div(className='section-title', children='Station Settings'),
            html.Div(className='station-inputs', children=[
                html.Div([
                    html.Label("Network : "),
                    dcc.Input(id='network', value='AM', type='text', className='short-input')
                ]),
                html.Div([
                    html.Label("Station Code : "),
                    dcc.Input(id='station-code', value='R50D6', type='text', className='short-input')
                ]),
                html.Div([
                    html.Label("Data Provider URL : "),
                    dcc.Input(id='data-provider-url', value='https://data.raspberryshake.org', type='text',
                              className='long-input')
                ]),
                html.Div([
                    html.Label("Report Date : "),
                    dcc.DatePickerSingle(
                        id='report-date',
                        date=yesterday,
                        display_format='YYYY-MM-DD',
                        className='date-picker'
                    )
                ])
            ], style={'display': 'flex', 'gap': '20px'}),
            html.Button('Download Station Data', id='download-data-button', n_clicks=0),
            html.Div(id='download-status')
        ]),
        html.Div(className='section', children=[
            html.Div(className='section-title', children='Stream Processing'),
            html.Div(className='processing-inputs', children=[
                html.Div([
                    dcc.Checklist(
                        id='processing-options-1',
                        options=[
                            {'label': 'Detrend Demean', 'value': 'detrend_demean'},
                            {'label': 'Detrend Linear', 'value': 'detrend_linear'},
                            {'label': 'Remove Outliers', 'value': 'remove_outliers'},
                        ],
                        value=['detrend_demean', 'detrend_linear', 'remove_outliers'],
                        inline=True
                    )
                ], style={'display': 'flex', 'gap': '20px'}),
                html.Div([
                    dcc.Checklist(
                        id='processing-options-2',
                        options=[
                            {'label': 'Bandpass Filter', 'value': 'bandpass_filter'},
                            {'label': 'Taper', 'value': 'taper'},
                            {'label': 'Denoise', 'value': 'denoise'}
                        ],
                        value=['bandpass_filter', 'taper', 'denoise'],
                        inline=True
                    )
                ], style={'display': 'flex', 'gap': '20px'}),
                html.Div([
                    dcc.Checklist(
                        id='save-processed-stream',
                        options=[
                            {'label': 'Save Processed Stream', 'value': 'save'}
                        ],
                        value=['save'],  # 默认勾选
                        inline=True
                    )
                ], style={'display': 'flex', 'flex-direction': 'column', 'gap': '20px'})
            ]),
            html.Button('Process Stream', id='process-stream-button', n_clicks=0),
            html.Div(id='process-status')
        ]),
        html.Div(className='section', children=[
            html.Div(className='section-title', children='Event Picking'),
            html.Div(className='event-picking-inputs', children=[
                html.Div([
                    html.Label("P Threshold : "),
                    dcc.Input(id='p-threshold', value='0.7', type='text', className='short-input')
                ]),
                html.Div([
                    html.Label("S Threshold : "),
                    dcc.Input(id='s-threshold', value='1', type='text', className='short-input')
                ]),
                html.Div([
                    dcc.Checklist(id='p-only', options=[
                        {'label': 'P Waves Only', 'value': 'yes'}
                    ], value=['yes'], inline=True)
                ])
            ], style={'display': 'flex', 'gap': '20px'}),
            html.Div([
                dcc.Checklist(
                    id='save-annotated-stream',
                    options=[
                        {'label': 'Save Annotated Stream', 'value': 'save'}
                    ],
                    value=['save'],  # 默认勾选
                    inline=True
                )
            ]),
            html.Button('Detect Phases', id='detect-phases-button', n_clicks=0),
            html.Div(id='detect-phases-status')
        ]),
        html.Div(className='section', children=[
            html.Div(className='section-title', children='Catalog Settings'),
            html.Div([
                html.Label("Catalog Providers : "),
                dcc.Input(id='catalog-providers', value='IRIS,USGS,EMSC', type='text', className='long-input')
            ], style={'margin-top': '10px'}),
            html.Div(className='catalog-inputs', children=[
                html.Div([
                    html.Label("Radmin : "),
                    dcc.Input(id='radmin', value='0', type='text', className='short-input')
                ]),
                html.Div([
                    html.Label("Radmax : "),
                    dcc.Input(id='radmax', value='90', type='text', className='short-input')
                ]),
                html.Div([
                    html.Label("Minmag : "),
                    dcc.Input(id='minmag', value='4', type='text', className='short-input')
                ]),
                html.Div([
                    html.Label("Maxmag : "),
                    dcc.Input(id='maxmag', value='10', type='text', className='short-input')
                ])
            ], style={'display': 'flex', 'gap': '20px'}),
            html.Button('Download Catalog Data', id='download-catalog-button', n_clicks=0),
            html.Div(id='download-catalog-status')
        ]),
        html.Div(className='section', children=[
            html.Div(className='section-title', children='Event Matching'),
            html.Div(className='event-matching-inputs', children=[
                html.Div([
                    html.Label("Tolerance P : "),
                    dcc.Input(id='tolerance-p', value='10', type='text', className='short-input')
                ]),
                html.Div([
                    html.Label("Tolerance S : "),
                    dcc.Input(id='tolerance-s', value='0', type='text', className='short-input')
                ]),
            ], style={'display': 'flex', 'gap': '20px'}),
            html.Div([
                dcc.Checklist(
                    id='save-results-to-csv',
                    options=[
                        {'label': 'Save Results To CSV', 'value': 'save'}
                    ],
                    value=['save'],  # 默认勾选
                    inline=True
                )
            ]),
            html.Button('Match Events', id='match-events-button', n_clicks=0),
            html.Div(id='match-events-status')
        ]),
    ]),
    html.Div(className='section', children=[
        html.Div(className='section-title', children='Report Generation'),
        html.Div(className='options-inputs', children=[
            html.Div([
                dcc.Checklist(id='create-gif', options=[
                    {'label': 'Create GIF', 'value': 'yes'}
                ], value=['yes'], inline=True)  # 默认勾选
            ]),
            html.Div([
                dcc.Checklist(id='fill-map', options=[
                    {'label': 'Fill Map', 'value': 'yes'}
                ], value=['yes'], inline=True)  # 默认勾选
            ]),
            html.Div([
                dcc.Checklist(id='simplified', options=[
                    {'label': 'Simplified', 'value': 'yes'}
                ], value=['yes'], inline=True)  # 默认勾选
            ])
        ], style={'display': 'flex', 'gap': '20px'}),
        html.Button('Generate Report', id='generate-report-button', n_clicks=0),
        html.Div(id='generate-report-status')
    ]),
    html.Div(className='section', children=[
        html.Div(className='section-title', children='Email Settings'),
        html.Div([
            html.Label("Email Recipient : "),
            dcc.Input(id='email-recipient', value='891578348@qq.com', type='email', className='long-input')
        ], style={'margin-top': '10px'}),
        html.Button('Send Email', id='send-email-button', n_clicks=0),
        html.Div(id='send-email-status')
    ])
])

# 下载站台数据的回调
@GUI.callback(
    Output('download-status', 'children'),
    Input('download-data-button', 'n_clicks'),
    State('network', 'value'),
    State('station-code', 'value'),
    State('data-provider-url', 'value'),
    State('report-date', 'date')
)
def download_station_data(n_clicks, network, station_code, data_provider_url, report_date):
    global global_station
    if n_clicks > 0:
        station, message = download_station_data_logic(network, station_code, data_provider_url, report_date)
        if station:
            global_station = station
        return message
    return ""

# 处理流数据的回调
@GUI.callback(
    Output('process-status', 'children'),
    Input('process-stream-button', 'n_clicks'),
    State('processing-options-1', 'value'),
    State('processing-options-2', 'value'),
    State('save-processed-stream', 'value')
)
def process_stream_callback(n_clicks, processing_options_1, processing_options_2, save_processed):
    global global_station
    if n_clicks > 0 and global_station:
        try:
            detrend_demean = 'detrend_demean' in processing_options_1
            detrend_linear = 'detrend_linear' in processing_options_1
            remove_outliers = 'remove_outliers' in processing_options_1
            bandpass_filter = 'bandpass_filter' in processing_options_2
            taper = 'taper' in processing_options_2
            denoise = 'denoise' in processing_options_2

            process_stream_logic(global_station, detrend_demean, detrend_linear, remove_outliers, bandpass_filter, taper, denoise)

            if 'save' in save_processed:
                save_stream(global_station, global_station.processed_stream, "processed")
                print("Processed stream saved.")

            return "Stream processing completed."
        except Exception as e:
            print(f"Error during stream processing: {str(e)}")
            return f"Error: {str(e)}"

    return ""

# 检测事件的回调
@GUI.callback(
    Output('detect-phases-status', 'children'),
    Input('detect-phases-button', 'n_clicks'),
    State('p-threshold', 'value'),
    State('s-threshold', 'value'),
    State('p-only', 'value'),
    State('save-annotated-stream', 'value')
)
def detect_phases(n_clicks, p_threshold, s_threshold, p_only, save_annotated):
    global global_station, global_p_only
    if n_clicks > 0 and global_station:
        try:
            global_p_only = 'yes' in p_only
            picked_signals, annotated_stream, p_count, s_count = detect_phases_logic(global_station, float(p_threshold), float(s_threshold), global_p_only)

            global_station.picked_signals = picked_signals
            global_station.annotated_stream = annotated_stream

            if 'save' in save_annotated:
                save_stream(global_station, global_station.annotated_stream, "processed.annotated")
                print("Annotated stream saved.")

            if global_p_only:
                return f"P waves detected: {p_count}"
            else:
                return f"P waves detected: {p_count}, S waves detected: {s_count}"
        except Exception as e:
            print(f"Error during event detection: {str(e)}")
            return f"Error: {str(e)}"

    return ""

# 下载目录数据的回调
@GUI.callback(
    Output('download-catalog-status', 'children'),
    Input('download-catalog-button', 'n_clicks'),
    State('catalog-providers', 'value'),
    State('radmin', 'value'),
    State('radmax', 'value'),
    State('minmag', 'value'),
    State('maxmag', 'value')
)
def download_catalogue(n_clicks, catalog_providers, radmin, radmax, minmag, maxmag):
    global global_station, global_catalog
    if n_clicks > 0 and global_station:
        providers = [provider.strip() for provider in catalog_providers.split(',')]
        radmin = float(radmin)
        radmax = float(radmax)
        minmag = float(minmag)
        maxmag = float(maxmag)

        catalog, message = download_catalogue_logic(global_station, radmin, radmax, minmag, maxmag, providers)
        if catalog:
            global_catalog = catalog
        return message
    return ""

# 事件匹配的回调
@GUI.callback(
    Output('match-events-status', 'children'),
    Input('match-events-button', 'n_clicks'),
    State('tolerance-p', 'value'),
    State('tolerance-s', 'value'),
    State('save-results-to-csv', 'value')
)
def match_events_callback(n_clicks, tolerance_p, tolerance_s, save_results_to_csv):
    global global_catalog, global_p_only
    if n_clicks > 0 and global_catalog:
        try:
            match_events_logic(global_catalog, float(tolerance_p), float(tolerance_s), global_p_only, 'save' in save_results_to_csv)
            summary = global_catalog.print_summary()
            return html.Pre(f"Event matching completed and summary printed.\n\n{summary}")
        except Exception as e:
            print(f"Error during event matching: {str(e)}")
            return f"Error: {str(e)}"
    return ""

# 报告生成的回调
@GUI.callback(
    Output('generate-report-status', 'children'),
    Input('generate-report-button', 'n_clicks'),
    State('create-gif', 'value'),
    State('fill-map', 'value'),
    State('simplified', 'value')
)
def generate_report_callback(nclicks, create_gif, fill_map, simplified):
    global global_catalog, global_p_only, global_report
    if nclicks > 0 and global_catalog:
        try:
            global_report = generate_report_logic(global_catalog.station, global_catalog, 'yes' in simplified, global_p_only, 'yes' in fill_map, 'yes' in create_gif)
            return "Report HTML generated successfully."
        except Exception as e:
            print(f"Error during report generation: {str(e)}")
            return f"Error: {str(e)}"
    return ""

# 发送邮件的回调
@GUI.callback(
    Output('send-email-status', 'children'),
    Input('send-email-button', 'n_clicks'),
    State('email-recipient', 'value')
)
def send_email_callback(nclicks, email_recipient):
    global global_report
    if nclicks > 0 and global_report:
        try:
            result = send_email_logic(global_report, email_recipient)
            return result
        except Exception as e:
            print(f"Error during email sending: {str(e)}")
            return f"Error: {str(e)}"
    return ""

if __name__ == '__main__':
    GUI.run_server(debug=True)
