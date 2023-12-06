from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
import os
import ezdxf
import io
from zipfile import ZipFile

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'dxf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_and_save_dxf_file(dxf_path, job_loc_values):
    try:
        # Load the DXF file
        doc = ezdxf.readfile(dxf_path)

        # Access the specific layout
        layout = doc.layouts.get('master')

        modified_attributes = False

        # Iterate over the entities in the layout and modify attributes
        for e in layout.query('INSERT[name=="ssp_ARCH_24x36"]'):
            for attrib in e.attribs:
                if attrib.dxf.tag in job_loc_values:
                    modified_attributes = True
                    # Update the attribute text based on job_loc_values
                    attrib.dxf.text = job_loc_values[attrib.dxf.tag]

        if modified_attributes:
            # Create a memory file for the modified DXF
            memfile = io.BytesIO()
            doc.saveas(memfile)
            memfile.seek(0)
            return memfile
        else:
            return None
    except Exception as e:
        print(f"Error processing file: {e}")
        return None


@app.route('/upload', methods=['POST'])
def upload_files_and_download():
    uploaded_files = request.files.getlist('file[]')  # Adjust to handle multiple files
    if not uploaded_files:
        return jsonify({'message': 'No files uploaded'}), 400

    modified_files = []
    for file in uploaded_files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            job_loc_values = {
                'JOB_LOC1': request.form.get('JOB_LOC1', ''),
                # [Other job location values]
            }

            modified_file = process_and_save_dxf_file(file_path, job_loc_values)
            if modified_file:
                modified_files.append((modified_file, filename))

    if not modified_files:
        return jsonify({'message': 'No modifications made to any file'}), 200

    # Create a ZIP file if multiple files are modified
    if len(modified_files) > 1:
        zip_buffer = io.BytesIO()
        with ZipFile(zip_buffer, 'w') as zip_file:
            for file, name in modified_files:
                zip_file.writestr(f"modified_{name}", file.getvalue())
        zip_buffer.seek(0)
        return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='modified_files.zip')
    else:
        # Single file case
        file, name = modified_files[0]
        return send_file(file, mimetype='application/dxf', as_attachment=True, download_name=f"modified_{name}")

if __name__ == '__main__':
    app.run(debug=True)
