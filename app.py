import logging
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import io
import pandas as pd
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scooters.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Database models
class List(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    warehouse = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    scans = db.relationship('Scan', backref='list', lazy=True, cascade='all, delete-orphan')

class Scan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scooter_id = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    list_id = db.Column(db.Integer, db.ForeignKey('list.id'), nullable=False)

@app.route('/')
def index():
    logging.debug("Rendering index page.")
    return render_template('index.html')

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    if request.method == 'POST':
        list_id = request.form.get('list_id')
        if list_id:
            # Continue scanning existing list
            current_list = List.query.get(list_id)
            if current_list:
                logging.debug(f"Continuing scanning session: {list_id}")
                return render_template('scan.html', session_id=list_id, list_name=current_list.name)
            else:
                logging.debug(f"List ID {list_id} not found.")
                return redirect(url_for('index'))
        else:
            # Create new list
            list_name = request.form['list_name']
            warehouse_name = request.form['warehouse_name']
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
    session_id = data['session_id']
    scooter_id = data['scooter_id']
    # Check if list exists
    current_list = List.query.get(session_id)
    if current_list:
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
            return jsonify({'status': 'success', 'total': total_scans})
    else:
        logging.debug(f"Session ID {session_id} not found.")
        return jsonify({'status': 'error'})

@app.route('/export/<int:list_id>')
def export(list_id):
    logging.debug(f"Exporting data for list {list_id}.")
    current_list = List.query.get(list_id)
    if current_list:
        scans = Scan.query.filter_by(list_id=list_id).all()
        data = [{'Scooter ID': scan.scooter_id, 'Timestamp': scan.timestamp.strftime('%H:%M | %d.%m.%Y')} for scan in scans]
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        filename = f'{current_list.name}_{current_list.warehouse}_{current_list.timestamp.strftime("%Y%m%d%H%M%S")}.xlsx'
        logging.debug(f"Data exported successfully for list {list_id}.")
        return send_file(output, download_name=filename, as_attachment=True)
    else:
        logging.debug(f"No data found for list {list_id}.")
        return 'No data found for this list.'


@app.route('/lists')
def list_lists():
    all_lists = List.query.order_by(List.timestamp.desc()).all()
    return render_template('lists.html', lists=all_lists)

@app.route('/list/<int:list_id>')
def view_list(list_id):
    current_list = List.query.get(list_id)
    if current_list:
        scans = Scan.query.filter_by(list_id=list_id).order_by(Scan.timestamp.desc()).all()
        return render_template('view_list.html', list=current_list, scans=scans)
    else:
        return 'List not found', 404

@app.route('/delete_list/<int:list_id>', methods=['POST'])
def delete_list(list_id):
    current_list = List.query.get(list_id)
    if current_list:
        db.session.delete(current_list)
        db.session.commit()
        return '', 200
    else:
        return 'List not found', 404

@app.route('/delete_scan/<int:scan_id>', methods=['POST'])
def delete_scan(scan_id):
    scan = Scan.query.get(scan_id)
    if scan:
        list_id = scan.list_id
        db.session.delete(scan)
        db.session.commit()
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error'})

# Route to serve sw.js
@app.route('/sw.js')
def sw():
    logging.debug("Serving service worker.")
    return app.send_static_file('sw.js')

# Initialize the database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
