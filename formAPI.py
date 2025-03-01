import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import jsonify, Flask, request
from flask_cors import CORS  # Added CORS support
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Load Firestore credentials from environment variable
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/etc/secrets/formAPIkey.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate(cred_path))

# Get Firestore database reference
db = firestore.client()

@app.route('/create-form', methods=['POST'])
def createForm():
    data = request.json
    form_id = str(uuid.uuid4())

    form_doc = {
        'title': data.get("title", "Untitled Form"),
        'desc': data.get("desc", "No description...")
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


def debugForm(form_id):
    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()

    if not form_doc.exists:
        return jsonify({"error": "Form not found"}), 404

    form_data = form_doc.to_dict() or {}
    return jsonify(form_data), 200


@app.route('/update-form/<form_id>', methods=['POST'])
def updateForm(form_id):
    data = request.json
    fields = data.get("fields", [])  
    title = data.get("title")  
    desc = data.get("desc")  
    field_type = data.get("field_type")
    print(f"Received field_type: {field_type}")

    if not form_id:
        return jsonify({"error": "Missing form_id"}), 400

    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()

    if not form_doc.exists:
        return jsonify({"error": "Form not found"}), 404

    updated_data = {}
    if title is not None:
        updated_data["title"] = title
    if desc is not None:
        updated_data["desc"] = desc

    if updated_data:
        form_ref.set(updated_data, merge=True)

    fields_collection = form_ref.collection("fields")

    # Debugging: Check if existing fields are found
    print(f"Updating fields for form {form_id}")

    for field in fields:
        field_label = field.get("label", "")
        field_type = field.get("type", "")

        if field_label and field_type:
            print(f"Checking existing fields with label: {field_label}, type: {field_type}")
            existing_fields = fields_collection.where("label", "==", field_label).where("type", "==", field_type).stream()
            field_id = None

            for existing_field in existing_fields:
                field_id = existing_field.id
                print(f"Found existing field: {field_id}")

            if field_id:
                print(f"Updating existing field {field_id}")
                fields_collection.document(field_id).set(field, merge=True)
            else:
                print(f"Creating new field: {field_label}, type: {field_type}")
                new_field_id = str(uuid.uuid4())
                fields_collection.document(new_field_id).set(field, merge=True)

    if not field_type:
        print("No field_type provided. Skipping field creation.")
        return jsonify({"error": "Missing field_type"}), 400
   
   if field_type:
    print(f"Adding new field with type: {field_type}")
    new_field_id = str(uuid.uuid4())
    new_field = {
        "label": f"New {field_type}",
        "type": field_type,
        "options": [],
        "correct_option": "",
        "required": False
    }
    fields_collection.document(new_field_id).set(new_field, merge=True)
    print(f"New field {new_field_id} added successfully!")


    fields_snapshot = fields_collection.stream()
    updated_fields = [{"id": field.id, **field.to_dict()} for field in fields_snapshot]

    print(f"Updated fields: {updated_fields}")  # Debugging final fields

    return jsonify({
        "form_id": form_id,
        "title": updated_data.get("title", form_doc.to_dict().get("title", "Untitled Form")),
        "desc": updated_data.get("desc", form_doc.to_dict().get("desc", "No description")),
        "fields": updated_fields
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)  # Required for Render
