"""
Excel Consolidator Web Version
Simple Flask application with no database - stateless file processing
"""
import os
import uuid
import shutil
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import threading
import time

# Import the consolidation service (we'll create this from your existing code)
from services.consolidator import ExcelConsolidator

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['OUTPUT_FOLDER'] = 'temp_outputs'

# Create necessary folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# In-memory job tracking (simple dict - no database needed)
jobs = {}

# Cleanup old files after 1 hour
CLEANUP_TIMEOUT = 3600


class ConsolidationJob:
    """Simple job tracker without database"""
    def __init__(self, job_id):
        self.job_id = job_id
        self.status = 'pending'  # pending, processing, completed, error
        self.progress = 0
        self.message = 'Waiting to start...'
        self.output_file = None
        self.error = None
        self.created_at = datetime.now()
        self.current_file = ''
        self.total_files = 0
        self.processed_files = 0


def cleanup_old_jobs():
    """Background cleanup of old temporary files"""
    while True:
        time.sleep(300)  # Run every 5 minutes
        now = datetime.now()
        
        for job_id in list(jobs.keys()):
            job = jobs[job_id]
            age = (now - job.created_at).total_seconds()
            
            if age > CLEANUP_TIMEOUT:
                # Clean up job files
                job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
                if os.path.exists(job_folder):
                    shutil.rmtree(job_folder)
                
                if job.output_file and os.path.exists(job.output_file):
                    os.remove(job.output_file)
                
                # Remove from memory
                del jobs[job_id]
                print(f"Cleaned up old job: {job_id}")


# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_jobs, daemon=True)
cleanup_thread.start()


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/consolidate', methods=['POST'])
def consolidate():
    """
    Handle file upload and start consolidation
    Returns: job_id for tracking progress
    """
    # Validate files
    if 'template' not in request.files:
        return jsonify({'error': 'No template file provided'}), 400
    
    if 'sources' not in request.files:
        return jsonify({'error': 'No source files provided'}), 400
    
    template_file = request.files['template']
    source_files = request.files.getlist('sources')
    
    if template_file.filename == '':
        return jsonify({'error': 'Empty template filename'}), 400
    
    if len(source_files) == 0:
        return jsonify({'error': 'No source files selected'}), 400
    
    # Get optional settings
    settings = {
        'convert_text_to_numbers': request.form.get('convert_text_to_numbers', 'true') == 'true',
        'convert_percentages': request.form.get('convert_percentages', 'true') == 'true',
        'create_backup': request.form.get('create_backup', 'false') == 'true',
        'skip_validation': request.form.get('skip_validation', 'true') == 'true'
    }
    
    # Create unique job ID
    job_id = str(uuid.uuid4())
    job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    os.makedirs(job_folder, exist_ok=True)
    
    # Save template
    template_path = os.path.join(job_folder, secure_filename(template_file.filename))
    template_file.save(template_path)
    
    # Save source files
    source_folder = os.path.join(job_folder, 'sources')
    os.makedirs(source_folder, exist_ok=True)
    
    source_paths = []
    for source in source_files:
        if source.filename:
            filepath = os.path.join(source_folder, secure_filename(source.filename))
            source.save(filepath)
            source_paths.append(filepath)
    
    # Create job tracker
    job = ConsolidationJob(job_id)
    job.total_files = len(source_paths)
    jobs[job_id] = job
    
    # Start processing in background thread
    def process_job():
        try:
            job.status = 'processing'
            job.message = 'Starting consolidation...'
            
            # Create consolidator instance
            consolidator = ExcelConsolidator(
                template_path=template_path,
                source_folder=source_folder,
                settings=settings,
                progress_callback=lambda current, total, filename: update_progress(
                    job_id, current, total, filename
                )
            )
            
            # Run consolidation
            output_path = consolidator.consolidate()
            
            # Move output to temp_outputs
            output_filename = f"Consolidated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            final_output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_{output_filename}")
            shutil.copy2(output_path, final_output_path)
            
            job.output_file = final_output_path
            job.status = 'completed'
            job.progress = 100
            job.message = 'Consolidation completed successfully!'
            
        except Exception as e:
            job.status = 'error'
            job.error = str(e)
            job.message = f'Error: {str(e)}'
            print(f"Error in job {job_id}: {str(e)}")
    
    thread = threading.Thread(target=process_job)
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'message': 'Consolidation started',
        'total_files': len(source_paths)
    })


def update_progress(job_id, current, total, filename):
    """Callback to update job progress"""
    if job_id in jobs:
        job = jobs[job_id]
        job.processed_files = current
        job.total_files = total
        job.current_file = filename
        job.progress = int((current / total) * 100) if total > 0 else 0
        job.message = f'Processing {current}/{total}: {filename}'


@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get job status"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    return jsonify({
        'job_id': job_id,
        'status': job.status,
        'progress': job.progress,
        'message': job.message,
        'current_file': job.current_file,
        'processed_files': job.processed_files,
        'total_files': job.total_files,
        'error': job.error,
        'has_output': job.output_file is not None
    })


@app.route('/api/download/<job_id>', methods=['GET'])
def download_result(job_id):
    """Download consolidated file"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    if job.status != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400
    
    if not job.output_file or not os.path.exists(job.output_file):
        return jsonify({'error': 'Output file not found'}), 404
    
    return send_file(
        job.output_file,
        as_attachment=True,
        download_name=f"Consolidated_{datetime.now().strftime('%b_%d_%Y')}.xlsx"
    )


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'active_jobs': len(jobs),
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    import os
    
    # Get port from environment variable (for cloud deployment) or use 5000
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    print("=" * 60)
    print("Excel Consolidator Web Server")
    print("=" * 60)
    print(f"Server starting at: http://localhost:{port}")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Output folder: {app.config['OUTPUT_FOLDER']}")
    print(f"Debug mode: {debug}")
    print("=" * 60)
    
    app.run(debug=debug, host='0.0.0.0', port=port)
