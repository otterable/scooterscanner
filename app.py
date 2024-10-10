import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import io
import pandas as pd
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import pytz  # For timezone handling
from flask_migrate import Migrate

# Get the absolute path of the directory where app.py is located
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'scooters.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Set up Flask-Migrate
migrate = Migrate(app, db)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Set your local timezone
local_tz = pytz.timezone('Europe/Berlin')  # Replace with your timezone

# Function to get local time
def get_local_time():
    return datetime.now(local_tz)

# Function to normalize scooter IDs
def normalize_scooter_id(scooter_id):
    logging.debug(f"Normalizing scooter ID: {scooter_id}")
    prefixes = ['https://tier.app/', 'https://qr.tier-services.io/']
    for prefix in prefixes:
        if scooter_id.startswith(prefix):
            scooter_id = scooter_id[len(prefix):]
            break
    scooter_id = scooter_id.upper()
    logging.debug(f"Normalized scooter ID: {scooter_id}")
    return scooter_id

# Function to compare scooter IDs considering possible prefixes
def scooter_id_matches(scooter_id_db, scooter_id_input):
    # Normalize both IDs
    id_db_normalized = normalize_scooter_id(scooter_id_db)
    id_input_normalized = normalize_scooter_id(scooter_id_input)
    return id_db_normalized == id_input_normalized

# Models
class List(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    warehouse = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=get_local_time)
    scans = db.relationship('Scan', backref='list', lazy=True, cascade='all, delete-orphan')
    is_validated = db.Column(db.Boolean, default=False)
    validation_timestamp = db.Column(db.DateTime)
    validations = db.relationship('Validation', backref='list', lazy=True, cascade='all, delete-orphan')

class Scan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scooter_id = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=get_local_time)
    list_id = db.Column(db.Integer, db.ForeignKey('list.id'), nullable=False)

class Validation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scooter_id = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=get_local_time)
    list_id = db.Column(db.Integer, db.ForeignKey('list.id'), nullable=False)
    is_valid = db.Column(db.Boolean, default=False)

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

@app.route('/validate_scan/<int:list_id>', methods=['GET', 'POST'])
def validate_scan(list_id):
    logging.debug(f"Accessing validate_scan for list ID: {list_id}")
    current_list = List.query.get(list_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        scans = Scan.query.filter_by(list_id=list_id).all()
        total_scooters = len(scans)
        logging.debug(f"Total scooters in list: {total_scooters}")
        # Prepare scooter IDs for validation
        scooter_ids = [scan.scooter_id for scan in scans]
        # Get validations
        validations = Validation.query.filter_by(list_id=list_id).all()
        validated_scooter_ids = [validation.scooter_id for validation in validations]
        validated_count = len(validated_scooter_ids)
        logging.debug(f"Total validated scooters: {validated_count}")
        # Prepare list of scooters with validation status
        scooters_with_status = []
        for scan in scans:
            scooter_id = scan.scooter_id
            short_id = normalize_scooter_id(scooter_id)
            is_validated = any(scooter_id_matches(validation_id, scooter_id) for validation_id in validated_scooter_ids)
            scooters_with_status.append({'scooter_id': scooter_id, 'short_id': short_id, 'is_validated': is_validated})
        return render_template('validate_scan.html', session_id=list_id, list_name=current_list.name, total_scooters=total_scooters, scooter_ids=scooter_ids, scooters_with_status=scooters_with_status, validated_count=validated_count)
    else:
        logging.debug(f"List ID {list_id} not found.")
        return redirect(url_for('validate_lists'))

@app.route('/save_validation', methods=['POST'])
def save_validation():
    data = request.get_json()
    logging.debug(f"Received validation data: {data}")
    session_id = data.get('session_id')
    scooter_id = data.get('scooter_id')
    logging.debug(f"Session ID: {session_id}, Scooter ID: {scooter_id}")

    normalized_scooter_id = normalize_scooter_id(scooter_id)

    current_list = List.query.get(session_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        # Check if scooter_id is in the original list
        original_scan = next((scan for scan in current_list.scans if scooter_id_matches(scan.scooter_id, scooter_id)), None)
        if original_scan:
            logging.debug(f"Scooter ID {scooter_id} is in the original list.")
            # Check if already validated
            existing_validation = next((val for val in current_list.validations if scooter_id_matches(val.scooter_id, scooter_id)), None)
            if existing_validation:
                logging.debug(f"Scooter ID {scooter_id} already validated.")
                return jsonify({'status': 'duplicate'})
            else:
                # Add validation entry
                new_validation = Validation(scooter_id=original_scan.scooter_id, list_id=session_id, is_valid=True)
                db.session.add(new_validation)
                db.session.commit()
                total_validated = len(current_list.validations)
                total_scooters = len(current_list.scans)
                logging.debug(f"Scooter ID {scooter_id} validated successfully. Total validated: {total_validated}/{total_scooters}")
                return jsonify({'status': 'success', 'total_validated': total_validated, 'total_scooters': total_scooters, 'scooter_id': normalized_scooter_id})
        else:
            logging.debug(f"Scooter ID {scooter_id} is NOT in the original list.")
            return jsonify({'status': 'not_in_list'})
    else:
        logging.debug(f"Session ID {session_id} not found.")
        return jsonify({'status': 'error'})

@app.route('/unvalidate_scooter', methods=['POST'])
def unvalidate_scooter():
    data = request.get_json()
    logging.debug(f"Received unvalidation data: {data}")
    session_id = data.get('session_id')
    scooter_id = data.get('scooter_id')
    logging.debug(f"Session ID: {session_id}, Scooter ID: {scooter_id}")

    current_list = List.query.get(session_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        # Find the validation entry
        validation_entry = next((val for val in current_list.validations if scooter_id_matches(val.scooter_id, scooter_id)), None)
        if validation_entry:
            db.session.delete(validation_entry)
            db.session.commit()
            total_validated = len(current_list.validations)
            total_scooters = len(current_list.scans)
            logging.debug(f"Scooter ID {scooter_id} unvalidated successfully. Total validated: {total_validated}/{total_scooters}")
            return jsonify({'status': 'success', 'total_validated': total_validated, 'total_scooters': total_scooters, 'scooter_id': normalize_scooter_id(scooter_id)})
        else:
            logging.debug(f"Scooter ID {scooter_id} not found in validations.")
            return jsonify({'status': 'not_validated'})
    else:
        logging.debug(f"Session ID {session_id} not found.")
        return jsonify({'status': 'error'})

@app.route('/unvalidate_scooter_in_list', methods=['POST'])
def unvalidate_scooter_in_list():
    logging.debug("Unvalidating a scooter from list overview.")
    data = request.get_json()
    scooter_id = data.get('scooter_id')
    list_id = data.get('list_id')
    logging.debug(f"Unvalidating scooter {scooter_id} from list {list_id}")

    current_list = List.query.get(list_id)
    if current_list:
        # Find the validation entry
        validation_entry = next((val for val in current_list.validations if scooter_id_matches(val.scooter_id, scooter_id)), None)
        if validation_entry:
            db.session.delete(validation_entry)
            db.session.commit()
            logging.debug(f"Scooter {scooter_id} unvalidated in list {list_id}")
            return jsonify({'status': 'success'})
        else:
            logging.debug(f"Scooter {scooter_id} not validated in list {list_id}")
            return jsonify({'status': 'error', 'message': 'Scooter not validated'})
    else:
        logging.debug(f"List {list_id} not found.")
        return jsonify({'status': 'error', 'message': 'List not found'})

@app.route('/save_scan', methods=['POST'])
def save_scan():
    data = request.get_json()
    logging.debug(f"Received scan data: {data}")
    session_id = data.get('session_id')
    scooter_id = data.get('scooter_id')
    logging.debug(f"Session ID: {session_id}, Scooter ID: {scooter_id}")

    # No change here, as we want to store the scooter ID as scanned

    # Validate scooter_id
    is_valid_id = len(normalize_scooter_id(scooter_id)) >= 5 and len(normalize_scooter_id(scooter_id)) <= 9
    if not is_valid_id:
        logging.debug(f"Invalid scooter ID format after normalizing: {scooter_id}")
        return jsonify({'status': 'invalid'})

    # Check if list exists
    current_list = List.query.get(session_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        # Check for duplicates within the list
        existing_scan = next((scan for scan in current_list.scans if scooter_id_matches(scan.scooter_id, scooter_id)), None)
        if existing_scan:
            logging.debug(f"Scooter ID {scooter_id} already scanned in session {session_id}.")
            return jsonify({'status': 'duplicate'})
        else:
            # Add new scan
            new_scan = Scan(scooter_id=scooter_id, list_id=session_id)
            db.session.add(new_scan)
            db.session.commit()
            total_scans = len(current_list.scans)
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

    scooter_id = normalize_scooter_id(scooter_id)

    # Validate scooter ID length
    if len(scooter_id) < 5 or len(scooter_id) > 9:
        logging.debug("Invalid scooter ID length.")
        return jsonify({'status': 'invalid_length'})
    if any(scooter_id.startswith(prefix.upper()) for prefix in ['http://', 'https://']):
        logging.debug("Invalid scooter ID: cannot be a URL.")
        return jsonify({'status': 'invalid_format'})

    # Check if list exists
    current_list = List.query.get(list_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        # Check for duplicates within the list
        existing_scan = next((scan for scan in current_list.scans if scooter_id_matches(scan.scooter_id, scooter_id)), None)
        if existing_scan:
            logging.debug(f"Scooter ID {scooter_id} already exists in list {list_id}.")
            return jsonify({'status': 'duplicate'})
        else:
            # Add new scan
            new_scan = Scan(scooter_id=scooter_id, list_id=list_id)
            db.session.add(new_scan)
            db.session.commit()
            total_scans = len(current_list.scans)
            logging.debug(f"Scooter ID {scooter_id} added manually to list {list_id}. Total items: {total_scans}")
            return jsonify({'status': 'success', 'total': total_scans, 'scan_id': new_scan.id})
    else:
        logging.debug(f"List ID {list_id} not found.")
        return jsonify({'status': 'error'})

@app.route('/add_manual_validation', methods=['POST'])
def add_manual_validation():
    logging.debug("Adding manual validation entry.")
    data = request.get_json()
    scooter_id_input = data.get('scooter_id').strip()
    list_id = data.get('list_id')
    logging.debug(f"Adding scooter {scooter_id_input} to validations in list {list_id}")

    normalized_input_id = normalize_scooter_id(scooter_id_input)

    current_list = List.query.get(list_id)
    if current_list:
        # Find matching scooter in scans (allow partial match)
        matching_scan = next((scan for scan in current_list.scans if normalize_scooter_id(scan.scooter_id).endswith(normalized_input_id)), None)
        if not matching_scan:
            logging.debug(f"Scooter ID {scooter_id_input} is not in the original scans.")
            return jsonify({'status': 'not_in_list'})
        # Use the original scooter ID from the scans
        full_scooter_id = matching_scan.scooter_id
        logging.debug(f"Full scooter ID found: {full_scooter_id}")

        # Check if already validated
        existing_validation = next((val for val in current_list.validations if scooter_id_matches(val.scooter_id, full_scooter_id)), None)
        if existing_validation:
            logging.debug(f"Scooter ID {full_scooter_id} already validated.")
            return jsonify({'status': 'duplicate'})
        else:
            # Add validation entry
            new_validation = Validation(scooter_id=full_scooter_id, list_id=list_id, is_valid=True)
            db.session.add(new_validation)
            db.session.commit()
            logging.debug(f"Scooter ID {full_scooter_id} manually validated in list {list_id}")
            return jsonify({'status': 'success'})
    else:
        logging.debug(f"List {list_id} not found.")
        return jsonify({'status': 'error', 'message': 'List not found'})

@app.route('/export/<int:list_id>')
def export(list_id):
    logging.debug(f"Exporting data for list {list_id}.")
    current_list = List.query.get(list_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        # Check if validations exist
        validation_count = len(current_list.validations)
        if validation_count > 0:
            logging.debug(f"{validation_count} validations found. Exporting only validated scooters.")
            validated_scooter_ids = [val.scooter_id for val in current_list.validations]
            scans = [scan for scan in current_list.scans if any(scooter_id_matches(scan.scooter_id, val_id) for val_id in validated_scooter_ids)]
        else:
            logging.debug("No validations found. Exporting all scooters.")
            scans = current_list.scans

        data = []
        for scan in scans:
            scooter_id = normalize_scooter_id(scan.scooter_id)
            local_time = scan.timestamp.astimezone(local_tz)
            data.append({
                'Scooter ID': scooter_id,
                'Timestamp': local_time.strftime('%H:%M | %d.%m.%Y')
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

@app.route('/validate_list_overview/<int:list_id>')
def validate_list_overview(list_id):
    logging.debug(f"Viewing validation overview for list {list_id}.")
    current_list = List.query.get(list_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        scans = current_list.scans
        total_scooters = len(scans)
        validations = current_list.validations
        validated_count = len(validations)
        # Prepare scooters with validation status
        scooters_with_status = []
        for scan in scans:
            scooter_id = scan.scooter_id
            short_id = normalize_scooter_id(scooter_id)
            is_validated = any(scooter_id_matches(val.scooter_id, scooter_id) for val in validations)
            scooters_with_status.append({
                'scooter_id': scooter_id,
                'short_id': short_id,  # IDs are displayed normalized
                'is_validated': is_validated
            })
        logging.debug(f"Total scooters: {total_scooters}, Validated scooters: {validated_count}")
        return render_template('validate_list_overview.html', list=current_list, total_scooters=total_scooters, validated_count=validated_count, scooters_with_status=scooters_with_status)
    else:
        logging.debug(f"List {list_id} not found.")
        return 'List not found', 404

@app.route('/lists')
def list_lists():
    logging.debug("Fetching all lists.")
    all_lists = List.query.order_by(List.timestamp.desc()).all()
    unique_scooter_ids = set()
    for lst in all_lists:
        for scan in lst.scans:
            unique_scooter_ids.add(normalize_scooter_id(scan.scooter_id))
    total_scooters = len(unique_scooter_ids)
    # Count duplicates
    scooter_counts = {}
    for lst in all_lists:
        for scan in lst.scans:
            norm_id = normalize_scooter_id(scan.scooter_id)
            scooter_counts[norm_id] = scooter_counts.get(norm_id, 0) + 1
    duplicate_count = sum(1 for count in scooter_counts.values() if count > 1)
    logging.debug(f"Total lists found: {len(all_lists)}")
    logging.debug(f"Total unique scooters: {total_scooters}")
    logging.debug(f"Total duplicates: {duplicate_count}")
    return render_template('lists.html', lists=all_lists, total_scooters=total_scooters, duplicate_count=duplicate_count)

@app.route('/list/<int:list_id>')
def view_list(list_id):
    logging.debug(f"Viewing list {list_id}.")
    current_list = List.query.get(list_id)
    if current_list:
        logging.debug(f"List found: {current_list.id}")
        scans = current_list.scans
        logging.debug(f"Total scans in list: {len(scans)}")
        # Process scans to add scooter_id_short
        for scan in scans:
            scan.scooter_id_short = normalize_scooter_id(scan.scooter_id)
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

@app.route('/validate_lists')
def validate_lists():
    logging.debug("Fetching lists for validation.")
    all_lists = List.query.order_by(List.timestamp.desc()).all()
    # Calculate validated counts for each list
    for lst in all_lists:
        total_scans = len(lst.scans)
        total_validations = len(lst.validations)
        lst.total_scans = total_scans
        lst.total_validations = total_validations
        logging.debug(f"List ID {lst.id}: Total Scans: {total_scans}, Total Validations: {total_validations}")
    return render_template('validate_lists.html', lists=all_lists)

@app.route('/validatedlists')
def validated_lists():
    logging.debug("Fetching validated lists.")
    validated_lists = List.query.filter(List.is_validated == True).order_by(List.validation_timestamp.desc()).all()
    for lst in validated_lists:
        total_scans = len(lst.scans)
        total_validations = len(lst.validations)
        lst.total_scans = total_scans
        lst.total_validations = total_validations
        logging.debug(f"Validated List ID {lst.id}: Total Scans: {total_scans}, Total Validations: {total_validations}")
    logging.debug(f"Total validated lists found: {len(validated_lists)}")
    return render_template('validatedlists.html', validated_lists=validated_lists)

@app.route('/check_duplicates')
def check_duplicates():
    logging.debug("Checking for duplicates.")
    all_scans = db.session.query(Scan).all()
    # Create a mapping of normalized scooter IDs
    from collections import defaultdict
    scooter_counts = defaultdict(list)
    for scan in all_scans:
        norm_id = normalize_scooter_id(scan.scooter_id)
        scooter_counts[norm_id].append({'list_id': scan.list_id, 'full_id': scan.scooter_id})

    # Find duplicates
    duplicate_details = []
    for scooter_id, entries in scooter_counts.items():
        if len(entries) > 1:
            list_ids = [entry['list_id'] for entry in entries]
            lists = List.query.filter(List.id.in_(list_ids)).all()
            duplicate_details.append({
                'scooter_id': scooter_id,
                'count': len(entries),
                'lists': lists,
                'full_ids': [entry['full_id'] for entry in entries]
            })
    logging.debug(f"Total duplicates found: {len(duplicate_details)}")
    return render_template('duplicates.html', duplicates=duplicate_details)

@app.route('/export_duplicates')
def export_duplicates():
    logging.debug("Exporting duplicates to Excel.")
    all_scans = db.session.query(Scan).all()
    # Create a mapping of normalized scooter IDs
    from collections import defaultdict
    scooter_counts = defaultdict(list)
    for scan in all_scans:
        norm_id = normalize_scooter_id(scan.scooter_id)
        scooter_counts[norm_id].append(scan)

    data = []
    for scooter_id, scans in scooter_counts.items():
        if len(scans) > 1:
            list_names = ', '.join(set(scan.list.name for scan in scans))
            data.append({'Scooter ID': scooter_id, 'Occurrences': len(scans), 'Lists': list_names})

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    filename = 'duplicate_scooters.xlsx'
    logging.debug("Duplicates exported successfully.")
    return send_file(output, download_name=filename, as_attachment=True)

@app.route('/remove_duplicate', methods=['POST'])
def remove_duplicate():
    scooter_id = request.form.get('scooter_id')
    list_id = request.form.get('list_id')
    logging.debug(f"Removing scooter {scooter_id} from list {list_id}.")

    # Find the scan entry
    scan = Scan.query.filter(Scan.list_id == list_id).filter(Scan.scooter_id.like(f"%{scooter_id}%")).first()
    if scan:
        db.session.delete(scan)
        db.session.commit()
        logging.debug(f"Scooter {scooter_id} removed from list {list_id}.")
    else:
        logging.debug(f"Scooter {scooter_id} not found in list {list_id}.")
    return redirect(url_for('check_duplicates'))

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
