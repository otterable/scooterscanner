import logging
from flask import Flask, render_template, request, jsonify, send_file
import io
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# In-memory storage for scanned data
lists = {}

@app.route('/')
def index():
    logging.debug("Rendering index page.")
    return render_template('index.html')

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    if request.method == 'POST':
        list_name = request.form['list_name']
        warehouse_name = request.form['warehouse_name']
        session_id = f"{list_name}_{warehouse_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        lists[session_id] = []
        logging.debug(f"New scanning session created: {session_id}")
        return render_template('scan.html', session_id=session_id, list_name=list_name)
    else:
        logging.debug("GET request received at /scan, redirecting to index.")
        return render_template('index.html')

@app.route('/save_scan', methods=['POST'])
def save_scan():
    data = request.get_json()
    logging.debug(f"Received scan data: {data}")
    session_id = data['session_id']
    scooter_id = data['scooter_id']
    timestamp = datetime.now().strftime('%H:%M | %d.%m.%Y')
    if session_id in lists:
        lists[session_id].append({'Scooter ID': scooter_id, 'Timestamp': timestamp})
        logging.debug(f"Scooter ID {scooter_id} added to session {session_id}. Total items: {len(lists[session_id])}")
        return jsonify({'status': 'success', 'total': len(lists[session_id])})
    else:
        logging.debug(f"Session ID {session_id} not found.")
        return jsonify({'status': 'error'})

@app.route('/export/<session_id>')
def export(session_id):
    logging.debug(f"Exporting data for session {session_id}.")
    if session_id in lists:
        df = pd.DataFrame(lists[session_id])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        filename = f'{session_id}.xlsx'
        logging.debug(f"Data exported successfully for session {session_id}.")
        return send_file(output, attachment_filename=filename, as_attachment=True)
    else:
        logging.debug(f"No data found for session {session_id}.")
        return 'No data found for this session.'

# Route to serve sw.js
@app.route('/sw.js')
def sw():
    logging.debug("Serving service worker.")
    return app.send_static_file('sw.js')

if __name__ == '__main__':
    app.run(debug=True)
