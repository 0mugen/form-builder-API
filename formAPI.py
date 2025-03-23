import os, uuid, json
import firebase_admin
from firebase_admin import credentials, firestore
from flask import jsonify, Flask, request
from flask_cors import CORS  # Added CORS support

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Load Firestore credentials from environment variable
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/etc/secrets/formAPIkey.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate(cred_path))

# Get Firestore database reference
db = firestore.client()

@app.route('/create-form', methods=['GET'])
def createForm():
    form_id = str(uuid.uuid4())

    form_doc = {
        'title': "Untitled Form",
        'desc': "No description...",
        'fields': [],
        'form_id': form_id
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


@app.route('/update-form-metadata/<form_id>', methods=['GET'])
def update_form_metadata(form_id):
    if not form_id:
        return jsonify({"error": "Missing form_id"}), 400

    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()

    if not form_doc.exists:
        return jsonify({"error": "Form not found"}), 404

    updated_data = {}
    if "form_title" in request.args:
        updated_data["title"] = request.args.get("form_title")
    if "form_desc" in request.args:
        updated_data["desc"] = request.args.get("form_desc")

    if updated_data:
        form_ref.set(updated_data, merge=True)
    
    # Fetch updated document
    updated_doc = form_ref.get().to_dict()
    
    return jsonify({
            "message": "Form metadata updated successfully", 
            "title": updated_doc.get("title", "Untitled Form"), 
            "desc": updated_doc.get("desc", "No description")
        }), 200


@app.route('/update-form-fields/<form_id>/<field_id>/<field_type>', methods=['GET'])
def update_form_fields(form_id, field_id, field_type):
    form_ref = db.collection("Forms").document(form_id)
    fields_collection = form_ref.collection("fields")
    
    field_ref = fields_collection.document(field_id)
    field_doc = field_ref.get()
    
    if not field_doc.exists:
        return jsonify({"error": "Field not found"}), 404
    
    update_data = {}
    if "label" in request.args:
        update_data["label"] = request.args.get("label")
    if "required" in request.args:
        update_data["required"] = request.args.get("required").lower() == "true"
    if "options" in request.args:
        new_option = request.args.get("options")
        existing_options = field_doc.to_dict().get("options", [])
        if new_option not in existing_options:
            existing_options.append(new_option)
        update_data["options"] = existing_options
    if "correct_option" in request.args:
        update_data["correct_option"] = request.args.get("correct_option")
    if "remove_option" in request.args:
        remove_option = request.args.get("remove_option")
        existing_options = field_doc.to_dict().get("options", [])
        if remove_option in existing_options:
            existing_options.remove(remove_option)
        update_data["options"] = existing_options

    
    if update_data:
        field_ref.set(update_data, merge=True)
    
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
        "required": False,
        "field_id": new_field_id
        "created_at": firestore.SERVER_TIMESTAMP
    }
    fields_collection.document(new_field_id).set(new_field, merge=True)
    
    fields_snapshot = fields_collection.stream()
    updated_fields = [{"id": field.id, **field.to_dict()} for field in fields_snapshot]
    
    return jsonify({"message": "New field added successfully", "field_id": new_field_id, "fields": updated_fields}), 200

@app.route('/submit-form/<form_id>/<user_id>', methods=['GET'])
def submit_form(form_id, user_id):
    try:
        # Extract answers from query parameters
        answers = request.args.get("answers")  # Expected as a JSON string

        if not answers:
            return jsonify({"error": "Missing answers parameter"}), 400

        try:
            answers_data = json.loads(answers)  # Parse JSON safely
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid answers format"}), 400

        response_ref = db.collection("Responses").document()
        response_ref.set({
            "form_id": form_id,
            "user_id": user_id,
            "submitted_at": firestore.SERVER_TIMESTAMP
        })

        # Store each answer in the "fields" subcollection
        for field in answers_data:
            response_ref.collection("responded_fields").document(field["field_id"]).set({
                "label": field["label"],
                "answer": field["answer"]
            })

        return jsonify({"message": "Form submitted successfully!", "response_id": response_ref.id}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete-form/<form_id>', methods=['GET'])
def delete_form(form_id):
    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()
    
    if not form_doc.exists:
        return jsonify({"error": "Form not found"}), 404
    
    form_ref.delete()
    return jsonify({"message": "Form deleted successfully"}), 200

@app.route('/delete-form-field/<form_id>/<field_id>', methods=['GET'])
def delete_form_field(form_id, field_id):
    form_ref = db.collection("Forms").document(form_id)
    fields_collection = form_ref.collection("fields")
    field_ref = fields_collection.document(field_id)
    field_doc = field_ref.get()
    
    if not field_doc.exists:
        return jsonify({"error": "Field not found"}), 404
    
    field_ref.delete()
    
    fields_snapshot = fields_collection.stream()
    updated_fields = [{"id": field.id, **field.to_dict()} for field in fields_snapshot]
    
    return jsonify({"message": "Field deleted successfully", "fields": updated_fields}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)  # Required for Render
