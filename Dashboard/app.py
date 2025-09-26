import os
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image as PlatypusImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import io
import plotly.io as pio
import sys

# Path to your external PDF document
DOCUMENT_PATH = "external_doc.pdf"

# This block is for handling the ImportError if rag_setup.py is not found
# and for creating the RAG chain
try:
    from rag_setup import create_rag_chain
    rag_chain = create_rag_chain(DOCUMENT_PATH)
except FileNotFoundError:
    print(f"ERROR: Document '{DOCUMENT_PATH}' not found. Please add it to the project directory.", file=sys.stderr)
    rag_chain = None
except ImportError:
    print("ERROR: rag_setup.py not found. Please ensure it's in the project directory.", file=sys.stderr)
    rag_chain = None

# ----------------- Dash App Initialization -----------------
# Initialize the Dash app here, before it is used anywhere else.
app = dash.Dash(__name__)

# Sample data for a dashboard chart
df = pd.DataFrame({
    "Region": ["North America", "Europe", "Asia"],
    "Q1 2025 Revenue ($M)": [1.5, 0.7, 1.1]
})

def create_pdf_report(graph_image_buffer, rag_response: str) -> io.BytesIO:
    """Creates a PDF report using reportlab and the graph image, with proper text wrapping."""
    buffer = io.BytesIO()
    
    # Use SimpleDocTemplate for flowable content like Paragraphs
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=inch, leftMargin=inch)
    
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("<b>AI-Powered Data Report</b>", styles['h1']))
    story.append(Spacer(1, 0.2*inch))
    
    # Graph Section
    story.append(Paragraph("<b>Q1 2025 Regional Revenue</b>", styles['h2']))
    story.append(Spacer(1, 0.2*inch))
    
    # Create a BytesIO object for the image data
    image_bytes_io = io.BytesIO(graph_image_buffer)
    
    # Add graph image using platypus.Image with explicit width and height
    img = PlatypusImage(image_bytes_io, width=6*inch, height=3.5*inch)
    story.append(img)
    story.append(Spacer(1, 0.5*inch))
    
    # RAG Response Section
    story.append(Paragraph("<b>LLM Analysis</b>", styles['h2']))
    story.append(Spacer(1, 0.1*inch))
    
    # Add the RAG response text as a Paragraph for automatic wrapping
    story.append(Paragraph(rag_response, styles['Normal']))

    # Build the document
    doc.build(story)
    buffer.seek(0)
    return buffer

# Initial graph figure
initial_figure = go.Figure(
    data=[go.Bar(x=df['Region'], y=df['Q1 2025 Revenue ($M)'], marker_color=['#1f77b4', '#d62728', '#2ca02c'])],
    layout=go.Layout(xaxis={'title': 'Region'}, yaxis={'title': 'Revenue ($M)'})
)

def create_dashboard_layout(graph_figure, rag_response_text):
    """Generates the main layout of the dashboard."""
    return html.Div(
        style={'fontFamily': 'sans-serif', 'padding': '20px'},
        id='dashboard-content',
        children=[
            html.H1("AI-Powered Data Analysis Dashboard", style={'textAlign': 'center'}),
            html.Div(
                children=[
                    html.H2("Q1 2025 Regional Revenue", style={'textAlign': 'center'}),
                    dcc.Graph(id='main-graph', figure=graph_figure)
                ]
            ),
            html.Hr(),
            html.Div(
                children=[
                    html.H2("Ask a Question (Powered by Llama 3.1 RAG)", style={'textAlign': 'center'}),
                    dcc.Input(
                        id='question-input',
                        type='text',
                        placeholder="e.g., What was the growth in the North America region?",
                        style={'width': '80%', 'padding': '10px', 'fontSize': '16px', 'marginRight': '10px'}
                    ),
                    html.Button('Submit', id='submit-button', n_clicks=0, style={'padding': '10px', 'fontSize': '16px'}),
                    html.Div(id='rag-response', style={'marginTop': '20px', 'border': '1px solid #ccc', 'padding': '15px', 'minHeight': '50px'}, children=rag_response_text)
                ]
            ),
            dcc.Store(id='rag-response-store'),
            html.Button('Download Report as PDF', id='download-button', n_clicks=0, style={'marginTop': '20px', 'padding': '10px', 'fontSize': '16px'}),
            dcc.Download(id="download-pdf")
        ]
    )

# Assign the layout to the app
app.layout = create_dashboard_layout(initial_figure, "Enter a question and click 'Submit'.")

# ----------------- Callbacks -----------------

@app.callback(
    Output('rag-response', 'children'),
    Output('rag-response-store', 'data'),
    Output('question-input', 'value'),
    Input('submit-button', 'n_clicks'),
    State('question-input', 'value'),
    prevent_initial_call=True
)
def update_response(n_clicks, question):
    if rag_chain is None:
        return html.P("RAG system not initialized. Check server logs for errors.", style={'color': 'red'}), "RAG system not initialized.", ""
    if question:
        try:
            response = rag_chain.invoke({"query": question})
            response_text = response['result']
            return html.P(response_text), response_text, ""
        except Exception as e:
            error_message = f"An error occurred: {e}"
            return html.P(error_message, style={'color': 'red'}), error_message, ""
    return dash.no_update, dash.no_update, ""

@app.callback(
    Output("download-pdf", "data"),
    Input("download-button", "n_clicks"),
    State('main-graph', 'figure'),
    State('rag-response-store', 'data'),
    prevent_initial_call=True
)
def download_pdf(n_clicks, graph_figure, rag_response_text):
    if n_clicks is None or not rag_response_text:
        return dash.no_update

    img_bytes = pio.to_image(graph_figure, format="png")
    pdf_buffer = create_pdf_report(img_bytes, rag_response_text)
    return dcc.send_bytes(pdf_buffer.getvalue(), "analysis_report.pdf")

# ----------------- App Run -----------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
