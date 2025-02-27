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
        'desc': data.get("desc", "No description..."),
        'fields': {
            0: {
            }
        }
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
    fields = data.get("fields", [])  # Expecting an array of fields
    title = data.get("title")  # Fetch the new title
    desc = data.get("desc")  # Fetch the new description

    if not form_id:
        return jsonify({"error": "Missing form_id"}), 400

    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()

    if not form_doc.exists:
        return jsonify({"error": "Form not found"}), 404

    # Fetch existing form data
    form_data = form_doc.to_dict()

    # Update fields only if provided
    existing_fields = form_data.get("fields", [])
    if fields:
        existing_fields.extend(fields)

    # Prepare the updated data
    updated_data = {
        "fields": existing_fields,
    }
    
    # Update title and description only if they are provided in the request
    if title is not None:
        updated_data["title"] = title
    if desc is not None:
        updated_data["desc"] = desc

    # Update Firestore document with merged data
    form_ref.set(updated_data, merge=True)

    # Return updated form data
    return jsonify({
        "form_id": form_id,
        "title": updated_data.get("title", form_data.get("title")),
        "desc": updated_data.get("desc", form_data.get("desc")),
        "fields": existing_fields
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)  # Required for Render
