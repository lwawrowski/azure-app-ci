from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, ContentSettings
import io
from datetime import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

def get_db_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                surname VARCHAR(100) NOT NULL,
                creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB init error: {e}")

init_db()

@app.route('/api/hello')
def hello():
    return jsonify({
        'message': 'Hello World from Backend!',
        'status': 'success'
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/db/users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, name, surname, creation_date FROM users ORDER BY creation_date DESC')
        users = [{'id': row[0], 'name': row[1], 'surname': row[2], 'creation_date': str(row[3])} for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({'users': users, 'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/db/users', methods=['POST'])
def add_user():
    try:
        data = request.get_json()
        name = data.get('name', '')
        surname = data.get('surname', '')
        
        if not name or not surname:
            return jsonify({'error': 'Name and surname are required', 'status': 'error'}), 400
            
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO users (name, surname) VALUES (%s, %s) RETURNING id, creation_date', (name, surname))
        result = cur.fetchone()
        user_id = result[0]
        creation_date = result[1]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'id': user_id, 'name': name, 'surname': surname, 'creation_date': str(creation_date), 'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/blob/upload', methods=['POST'])
def upload_blob():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided', 'status': 'error'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected', 'status': 'error'}), 400
            
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed', 'status': 'error'}), 400
        
        blob_service_client = BlobServiceClient.from_connection_string(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
        container_name = os.getenv('AZURE_STORAGE_CONTAINER', 'demo-container')
        
        # Generuj unikalną nazwę pliku
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"pdf_{timestamp}_{file.filename}"
        
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=filename)
        content_settings = ContentSettings(content_type='application/pdf')
        blob_client.upload_blob(file.read(), overwrite=True, content_settings=content_settings)
        
        return jsonify({'filename': filename, 'status': 'success', 'url': blob_client.url})
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/blob/list', methods=['GET'])
def list_blobs():
    try:
        blob_service_client = BlobServiceClient.from_connection_string(os.getenv('AZURE_STORAGE_CONNECTION_STRING'))
        container_name = os.getenv('AZURE_STORAGE_CONTAINER', 'demo-container')
        container_client = blob_service_client.get_container_client(container_name)
        
        blobs = [{'name': blob.name, 'size': blob.size, 'last_modified': str(blob.last_modified)} 
                 for blob in container_client.list_blobs()]
        
        return jsonify({'blobs': blobs, 'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
