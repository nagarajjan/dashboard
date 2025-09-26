import os
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from pypdf import PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from rag_setup import create_rag_chain
import io
import base64
import tempfile
import plotly.io as pio

# Path to your external PDF document
DOCUMENT_PATH = "external_doc.pdf"

# Create the RAG chain
try:
    rag_chain = create_rag_chain(DOCUMENT_PATH)
except FileNotFoundError:
    print(f"ERROR: Document '{DOCUMENT_PATH}' not found. Please add it to the project directory.")
    rag_chain = None

# Initialize Dash app
app = dash.Dash(__name__)

# Sample data for a dashboard chart
df = pd.DataFrame({
    "Region": ["North America", "Europe", "Asia"],
    "Q1 2025 Revenue ($M)": [1.5, 0.7, 1.1]
})

def create_dashboard_layout(graph_figure, rag_response_text):
    """Generates the main layout of the dashboard."""
    return html.Div(
        style={'fontFamily': 'sans-serif', 'padding': '20px'},
        id='dashboard-content',
        children=[
            html.H1("AI-Powered Data Analysis Dashboard", style={'textAlign': 'center'}),

            # Traditional dashboard chart
            html.Div(
                children=[
                    html.H2("Q1 2025 Regional Revenue", style={'textAlign': 'center'}),
                    dcc.Graph(id='main-graph', figure=graph_figure)
                ]
            ),
            
            html.Hr(),

            # RAG-powered natural language query section
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

            # Hidden component to store the RAG response for PDF generation
            dcc.Store(id='rag-response-store'),

            # PDF export button
            html.Button('Download Report as PDF', id='download-button', n_clicks=0, style={'marginTop': '20px', 'padding': '10px', 'fontSize': '16px'}),
            dcc.Download(id="download-pdf")
        ]
    )

def create_pdf_report(graph_image_buffer, rag_response: str) -> io.BytesIO:
    """Creates a PDF report using reportlab and the graph image."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, 10.5 * inch, "AI-Powered Data Report")
    
    # Graph Section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, 9.5 * inch, "Q1 2025 Regional Revenue")
    
    # Add graph image
    c.drawImage(io.BytesIO(graph_image_buffer), 1 * inch, 6 * inch, width=6 * inch, height=3.5 * inch, preserveAspectRatio=True)

    # RAG Response Section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, 5 * inch, "LLM Analysis")
    
    c.setFont("Helvetica", 10)
    textobject = c.beginText()
    textobject.setTextOrigin(1 * inch, 4.8 * inch)
    textobject.setWordSpace(0)
    # Split text into lines to fit on the page
    lines = rag_response.split('\n')
    for line in lines:
        textobject.textLine(line)
    c.drawText(textobject)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# Initial graph figure
initial_figure = go.Figure(
    data=[go.Bar(x=df['Region'], y=df['Q1 2025 Revenue ($M)'], marker_color=['#1f77b4', '#d62728', '#2ca02c'])],
    layout=go.Layout(xaxis={'title': 'Region'}, yaxis={'title': 'Revenue ($M)'})
)

app.layout = create_dashboard_layout(initial_figure, "Enter a question and click 'Submit'.")

# Callback for RAG query and storing response
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

# Callback for PDF download
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

    # Export Plotly figure to a PNG image buffer
    img_bytes = pio.to_image(graph_figure, format="png")
    
    # Create the PDF report
    pdf_buffer = create_pdf_report(img_bytes, rag_response_text)

    # Return the PDF file for download
    return dcc.send_bytes(pdf_buffer.getvalue(), "analysis_report.pdf")

# Run the app with the updated method
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

