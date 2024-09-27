import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import io
import pandas as pd
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Get the absolute path of the directory where app.py is located
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'scooters.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Database models
class List(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    warehouse = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    scans = db.relationship('Scan', backref='list', lazy=True, cascade='all, delete-orphan')

class Scan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scooter_id = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    list_id = db.Column(db.Integer, db.ForeignKey('list.id'), nullable=False)

@app.route('/')
def index():
    logging.debug("Rendering index page.")
    return render_template('index.html')

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    if request.method == 'POST':
        logging.debug("Received POST request at /scan.")
        list_id = request.form.get('list_id')
        if list_id:
            logging.debug(f"List ID received: {list_id}")
            # Continue scanning existing list
            current_list = List.query.get(list_id)
            if current_list:
                logging.debug(f"Continuing scanning session: {list_id}")
                return render_template('scan.html', session_id=list_id, list_name=current_list.name)
            else:
                logging.debug(f"List ID {list_id} not found.")
                return redirect(url_for('index'))
        else:
            logging.debug("No list ID received, creating new list.")
            # Create new list
            list_name = request.form.get('list_name')
            warehouse_name = request.form.get('warehouse_name')
            logging.debug(f"List name: {list_name}, Warehouse name: {warehouse_name}")
            new_list = List(name=list_name, warehouse=warehouse_name)
            db.session.add(new_list)
            db.session.commit()
            logging.debug(f"New scanning session created: {new_list.id}")
            return render_template('scan.html', session_id=new_list.id, list_name=list_name)
    else:
        logging.debug("GET request received at /scan, redirecting to index.")
        return redirect(url_for('index'))

@app.route('/save_scan', methods=['POST'])
def save_scan():
    data = request.get_json()
    logging.debug(f"Received scan data: {data}")
    session_id = data.get('session_id')
    scooter_id = data.get('scooter_id')
    logging.debug(f"Session ID: {session_id}, Scooter ID: {scooter_id}")

    # Validate scooter_id
    valid_prefixes = ['https://tier.app/', 'https://qr.tier-services.io/']
    if not any(scooter_id.startswith(prefix) for prefix in valid_prefixes):
        logging.debug(f"Invalid scooter ID prefix: {scooter_id}")
        return jsonify({'status': 'invalid'})

    # Check if list exists
    current_list = List.query.get(session_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        # Check for duplicates within the list
        existing_scan = Scan.query.filter_by(list_id=session_id, scooter_id=scooter_id).first()
        if existing_scan:
            logging.debug(f"Scooter ID {scooter_id} already scanned in session {session_id}.")
            return jsonify({'status': 'duplicate'})
        else:
            # Add new scan
            new_scan = Scan(scooter_id=scooter_id, list_id=session_id)
            db.session.add(new_scan)
            db.session.commit()
            total_scans = Scan.query.filter_by(list_id=session_id).count()
            logging.debug(f"Scooter ID {scooter_id} added to session {session_id}. Total items: {total_scans}")
            return jsonify({'status': 'success', 'total': total_scans, 'scan_id': new_scan.id})
    else:
        logging.debug(f"Session ID {session_id} not found.")
        return jsonify({'status': 'error'})

@app.route('/add_manual_entry', methods=['POST'])
def add_manual_entry():
    data = request.get_json()
    logging.debug(f"Received manual entry data: {data}")
    list_id = data.get('list_id')
    scooter_id = data.get('scooter_id').strip()
    logging.debug(f"List ID: {list_id}, Scooter ID: {scooter_id}")

    # Validate scooter ID (5 to 9 characters, no URLs)
    if len(scooter_id) < 5 or len(scooter_id) > 9:
        logging.debug("Invalid scooter ID length.")
        return jsonify({'status': 'invalid_length'})
    if any(scooter_id.startswith(prefix) for prefix in ['http://', 'https://']):
        logging.debug("Invalid scooter ID: cannot be a URL.")
        return jsonify({'status': 'invalid_format'})

    # Check if list exists
    current_list = List.query.get(list_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        # Check for duplicates within the list
        existing_scan = Scan.query.filter_by(list_id=list_id, scooter_id=scooter_id).first()
        if existing_scan:
            logging.debug(f"Scooter ID {scooter_id} already exists in list {list_id}.")
            return jsonify({'status': 'duplicate'})
        else:
            # Add new scan
            new_scan = Scan(scooter_id=scooter_id, list_id=list_id)
            db.session.add(new_scan)
            db.session.commit()
            total_scans = Scan.query.filter_by(list_id=list_id).count()
            logging.debug(f"Scooter ID {scooter_id} added manually to list {list_id}. Total items: {total_scans}")
            return jsonify({'status': 'success', 'total': total_scans, 'scan_id': new_scan.id})
    else:
        logging.debug(f"List ID {list_id} not found.")
        return jsonify({'status': 'error'})

@app.route('/export/<int:list_id>')
def export(list_id):
    logging.debug(f"Exporting data for list {list_id}.")
    current_list = List.query.get(list_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        scans = Scan.query.filter_by(list_id=list_id).all()
        data = []
        for scan in scans:
            full_id = scan.scooter_id
            # Remove URL prefix
            for prefix in ['https://tier.app/', 'https://qr.tier-services.io/']:
                if full_id.startswith(prefix):
                    short_id = full_id[len(prefix):]
                    break
            else:
                short_id = full_id

            data.append({
                'Full Scooter ID': full_id,
                'Scooter ID': short_id,
                'Timestamp': scan.timestamp.strftime('%H:%M | %d.%m.%Y')
            })

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        filename = f'{current_list.name}_{current_list.warehouse}_{current_list.timestamp.strftime("%Y%m%d%H%M%S")}.xlsx'
        logging.debug(f"Data exported successfully for list {list_id}. Filename: {filename}")
        return send_file(output, download_name=filename, as_attachment=True)
    else:
        logging.debug(f"No data found for list {list_id}.")
        return 'No data found for this list.'

@app.route('/lists')
def list_lists():
    logging.debug("Fetching all lists.")
    all_lists = List.query.order_by(List.timestamp.desc()).all()
    total_scooters = sum(len(lst.scans) for lst in all_lists)
    logging.debug(f"Total lists found: {len(all_lists)}")
    return render_template('lists.html', lists=all_lists, total_scooters=total_scooters)

@app.route('/list/<int:list_id>')
def view_list(list_id):
    logging.debug(f"Viewing list {list_id}.")
    current_list = List.query.get(list_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        scans = Scan.query.filter_by(list_id=list_id).order_by(Scan.timestamp.desc()).all()
        logging.debug(f"Total scans in list: {len(scans)}")
        # Process scans to add scooter_id_short
        for scan in scans:
            full_id = scan.scooter_id
            # Remove URL prefix
            for prefix in ['https://tier.app/', 'https://qr.tier-services.io/']:
                if full_id.startswith(prefix):
                    scan.scooter_id_short = full_id[len(prefix):]
                    break
            else:
                scan.scooter_id_short = full_id
        return render_template('view_list.html', list=current_list, scans=scans)
    else:
        logging.debug(f"List {list_id} not found.")
        return 'List not found', 404

@app.route('/delete_list/<int:list_id>', methods=['POST'])
def delete_list(list_id):
    logging.debug(f"Deleting list {list_id}.")
    current_list = List.query.get(list_id)
    if current_list:
        db.session.delete(current_list)
        db.session.commit()
        logging.debug(f"List {list_id} deleted successfully.")
        return '', 200
    else:
        logging.debug(f"List {list_id} not found.")
        return 'List not found', 404

@app.route('/delete_scan/<int:scan_id>', methods=['POST'])
def delete_scan(scan_id):
    logging.debug(f"Deleting scan {scan_id}.")
    scan = Scan.query.get(scan_id)
    if scan:
        db.session.delete(scan)
        db.session.commit()
        logging.debug(f"Scan {scan_id} deleted successfully.")
        return jsonify({'status': 'success'})
    else:
        logging.debug(f"Scan {scan_id} not found.")
        return jsonify({'status': 'error'})

# Route to serve sw.js
@app.route('/sw.js')
def sw():
    logging.debug("Serving service worker.")
    return app.send_static_file('sw.js')

# Initialize the database
with app.app_context():
    logging.debug("Initializing database.")
    db.create_all()
    logging.debug("Database initialized.")

if __name__ == '__main__':
    app.run(debug=True)
