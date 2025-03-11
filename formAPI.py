from flask import Flask, jsonify
import uuid
from firebase_admin import firestore

db = firestore.client()
app = Flask(__name__)

def parse_formatted_string(fields):
    # Assuming this function processes and returns a list of field dictionaries
    return fields

@app.route('/update-form-metadata/<form_id>/<form_title>/<form_desc>', methods=['GET'])
def update_form_metadata(form_id, form_title, form_desc):
    if not form_id:
        return jsonify({"error": "Missing form_id"}), 400

    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()

    if not form_doc.exists:
        return jsonify({"error": "Form not found"}), 404

    updated_data = {}
    if form_title:
        updated_data["title"] = form_title
    if form_desc:
        updated_data["desc"] = form_desc

    if updated_data:
        form_ref.set(updated_data, merge=True)
    
    return jsonify({"message": "Form metadata updated successfully"}), 200

@app.route('/update-form-fields/<form_id>/<field_id>/<fields>', methods=['GET'])
def update_form_fields(form_id, field_id, fields):
    fields = parse_formatted_string(fields)
    form_ref = db.collection("Forms").document(form_id)
    fields_collection = form_ref.collection("fields")
    
    field_ref = fields_collection.document(field_id)
    field_doc = field_ref.get()
    
    if not field_doc.exists:
        return jsonify({"error": "Field not found"}), 404
    
    for field in fields:
        field_ref.set(field, merge=True)
    
    fields_snapshot = fields_collection.stream()
    updated_fields = [{"id": field.id, **field.to_dict()} for field in fields_snapshot]
    
    return jsonify({"message": "Field updated successfully", "fields": updated_fields}), 200

@app.route('/add-form-field/<form_id>/<field_type>', methods=['GET'])
def add_form_field(form_id, field_type):
    if not field_type:
        return jsonify({"error": "Missing field_type"}), 400
    
    form_ref = db.collection("Forms").document(form_id)
    fields_collection = form_ref.collection("fields")
    new_field_id = str(uuid.uuid4())
    new_field = {
        "label": f"New {field_type}",
        "type": field_type,
        "options": [],
        "correct_option": "",
        "required": False
    }
    fields_collection.document(new_field_id).set(new_field, merge=True)
    
    fields_snapshot = fields_collection.stream()
    updated_fields = [{"id": field.id, **field.to_dict()} for field in fields_snapshot]
    
    return jsonify({"message": "New field added successfully", "field_id": new_field_id, "fields": updated_fields}), 200
