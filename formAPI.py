import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import jsonify, Flask, request
from flask_cors import CORS  # Added CORS support
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate('formAPIkey.json'))

# Get Firestore database reference
db = firestore.client()
@app.route('/create-form', methods=['GET'])
def createForm():
    form_id = str(uuid.uuid4())

    form_doc = {
        'title': "Untitled Form",
        'desc': "No description...",
        'fields': []
    }

    db.collection('Forms').document(form_id).set(form_doc)
    return jsonify({"success": True, "message": "Form created", "form_id": form_id}), 201


def returnAllFields(form_id):
    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()

    if not form_doc.exists:
        return []

    form_data = form_doc.to_dict()
    return form_data.get("fields", [])  # Ensure "fields" key exists

def parse_formatted_string(input_str):
    groups = input_str.split("@@@@@")  # Split different form groups
    result = []

    for group in groups:
        fields = group.split(",,,,,")  # Split key-value pairs
        form_dict = {}

        for field in fields:
            if ":::::" in field:
                key, value = field.split(":::::", 1)
                value = value.strip()

                # Convert boolean values
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False

                # Convert list values (detects `,,,` as a separator)
                elif ",,," in value:
                    value = value.split(",,,")  # Convert to list

                form_dict[key] = value  # Store in dictionary

        result.append(form_dict)

    return result

def debugForm(form_id):
    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()

    if not form_doc.exists:
        return jsonify({"error": "Form not found"}), 404

    form_data = form_doc.to_dict() or {}
    return jsonify(form_data), 200


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
    
    return jsonify({"message": "Field updated successfully"}), 200

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
    
    return jsonify({"message": "New field added successfully", "field_id": new_field_id}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)  # Required for Render
