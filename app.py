import os
import re
import logging
import json
import subprocess
import uuid
import shutil
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, abort
import yt_dlp
from urllib.parse import urlparse, parse_qs
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_change_in_production")

# Global configuration
MAX_VIDEO_DURATION_MINUTES = 60
MAX_RESOLUTION_HEIGHT = 1080
CLEANUP_INTERVAL_SECONDS = 60
FILE_RETENTION_MINUTES = 10

class DownloadManager:
    def __init__(self):
        self.jobs = {}
        self.active_job_id = None  # Track the single active (running) job
        self.lock = threading.Lock()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def create_job(self):
        """Create a new job ID but reject if another job is currently running."""
        with self.lock:
            # Check for active job
            if self.active_job_id:
                # Double check status to be safe, though active_job_id should strictly track running state
                active_job = self.jobs.get(self.active_job_id)
                if active_job and active_job['status'] in ['queued', 'downloading', 'merging']:
                    return None, "Another download is currently in progress. Please wait for it to finish."
                else:
                    # Should not happen if logic is correct, but self-heal
                    self.active_job_id = None

            job_id = str(uuid.uuid4())
            self.jobs[job_id] = {
                'id': job_id,
                'status': 'queued',
                'progress': 0,
                'status_text': 'Queued...',
                'created_at': datetime.now(),
                'file_path': None,
                'error': None,
                'temp_dir': None,
                'filename': None
            }
            self.active_job_id = job_id  # Mark as active immediately
            return job_id, None

    def get_job(self, job_id):
        with self.lock:
            return self.jobs.get(job_id)

    def update_job(self, job_id, **kwargs):
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].update(kwargs)

    def start_download(self, job_id, url, format_args):
        thread = threading.Thread(
            target=self._process_download,
            args=(job_id, url, format_args),
            daemon=True
        )
        thread.start()

    def _process_download(self, job_id, url, format_args):
        job = self.get_job(job_id)
        if not job:
            return
        
        # Defensively assume failure to start with
        success = False
        temp_dir = None

        try:
            temp_dir = tempfile.mkdtemp(prefix=f"tubefetch_{job_id}_")
            self.update_job(job_id, status='downloading', temp_dir=temp_dir, status_text='Initializing...')

            # Force yt-dlp to ensure FFmpeg is available (downloads if missing)
            try:
                import yt_dlp.utils
                yt_dlp.utils.check_executable("ffmpeg") 
            except Exception as ex:
                logging.warning(f"FFmpeg check warning: {ex}")

            # Common options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'paths': {'home': temp_dir},
                'progress_hooks': [lambda d: self._progress_hook(job_id, d)],
                'ffmpeg_location': None, # Allow auto-download of static ffmpeg if missing
            }

            # Determine mode
            mode = format_args.get('mode')
            
            if mode == 'merge':
                video_fmt = format_args.get('video_format_id')
                audio_fmt = format_args.get('audio_format_id')
                ydl_opts['format'] = f"{video_fmt}+{audio_fmt}"
            else:
                fmt = format_args.get('format_id')
                ydl_opts['format'] = fmt

            self.update_job(job_id, status_text='Starting download...')

            logging.info(f"Starting download for job {job_id}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # If merged, the filename might differ, scan directory
                if not os.path.exists(filename):
                     files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
                     if files:
                         filename = os.path.join(temp_dir, files[0])
                
                final_filename = os.path.basename(filename)
                
                # Verify file exists and has size
                if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                    raise Exception("Download failed: Output file is empty or missing.")

                self.update_job(job_id, 
                    status='completed', 
                    progress=100, 
                    status_text='Ready for download',
                    file_path=filename,
                    filename=final_filename
                )
                success = True

        except Exception as e:
            logging.error(f"Job {job_id} failed: {e}")
            self.update_job(job_id, status='error', error=str(e), status_text='Download Failed')
            
            # Immediate cleanup on failure
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logging.info(f"Cleaned up failed job {job_id}")
                except Exception as cleanup_obj:
                     logging.error(f"Failed to cleanup failed job {job_id}: {cleanup_obj}")
            
            self.update_job(job_id, temp_dir=None, file_path=None)

        finally:
            # Release lock irrespective of success/failure
            with self.lock:
                if self.active_job_id == job_id:
                    self.active_job_id = None
            
            # If successful, we DON'T cleanup yet. We wait for serving.

    def _progress_hook(self, job_id, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                percent = (downloaded / total) * 100
                self.update_job(job_id, 
                    progress=percent, 
                    status_text=f"Downloading: {percent:.1f}%"
                )
        elif d['status'] == 'finished':
             self.update_job(job_id, 
                progress=99, # Wait for post-processing
                status_text="Processing/Merging..."
            )

    def _cleanup_loop(self):
        """Failsafe periodic cleanup."""
        while True:
            try:
                time.sleep(CLEANUP_INTERVAL_SECONDS)
                now = datetime.now()
                expired_jobs = []
                
                with self.lock:
                    for job_id, job in self.jobs.items():
                        age = now - job['created_at']
                        if age > timedelta(minutes=FILE_RETENTION_MINUTES):
                            expired_jobs.append(job_id)
                
                for job_id in expired_jobs:
                    self.force_cleanup_job(job_id)
            except Exception as e:
                logging.error(f"Error in cleanup loop: {e}")

    def force_cleanup_job(self, job_id):
        """Force delete job files and entry."""
        job = self.get_job(job_id)
        if job and job.get('temp_dir') and os.path.exists(job['temp_dir']):
            try:
                shutil.rmtree(job['temp_dir'])
                logging.info(f"Cleaned up job {job_id}")
            except Exception as e:
                logging.error(f"Failed to cleanup job {job_id}: {e}")
        
        with self.lock:
            # If we are cleaning up the active job (timeout?), ensure we release lock
            if self.active_job_id == job_id:
                self.active_job_id = None
            if job_id in self.jobs:
                del self.jobs[job_id]

download_manager = DownloadManager()

def is_valid_youtube_url(url):
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return youtube_regex.match(url) is not None

def format_file_size(bytes_size):
    if bytes_size is None: return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0: return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_video():
    try:
        url = request.form.get('url', '').strip()
        if not url or not is_valid_youtube_url(url):
            flash('Please enter a valid YouTube URL', 'error')
            return redirect(url_for('index'))
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ffmpeg_location': None, # Allow auto-download
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                logging.error(f"Analysis failed: {e}")
                flash("Failed to analyze video. It might be private or restricted.", 'error')
                return redirect(url_for('index'))
            
            # Enforce Max Duration
            duration = info.get('duration', 0)
            if duration > MAX_VIDEO_DURATION_MINUTES * 60:
                flash(f'Video exceeds limit of {MAX_VIDEO_DURATION_MINUTES} minutes.', 'error')
                return redirect(url_for('index'))
            
            video_info = {
                'title': info.get('title', 'Unknown'),
                'author': info.get('uploader', 'Unknown'),
                'length': f"{duration // 60}:{duration % 60:02d}",
                'thumbnail': info.get('thumbnail', ''),
                'video_id': info.get('id'),
                'url': url,
            }
            
            formats = info.get('formats', [])
            processed_formats = []
            
            for f in formats:
                # Enforce Max Resolution
                height = f.get('height')
                if height and height > MAX_RESOLUTION_HEIGHT:
                    continue
                    
                processed_formats.append(f)

            video_audio_streams = []
            video_only_streams = []
            audio_only_streams = []
            
            for fmt in processed_formats:
                height = fmt.get('height')
                ext = fmt.get('ext')
                if ext == 'mhtml': continue
                
                # Zero-size check
                filesize_raw = fmt.get('filesize') or fmt.get('filesize_approx')
                if not filesize_raw or filesize_raw <= 0:
                    continue
                
                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                
                stream = {
                   'format_id': fmt['format_id'],
                   'resolution': f"{height}p" if height else "Audio",
                   'filesize': format_file_size(filesize_raw),
                   'ext': ext,
                   'vcodec': vcodec,
                   'acodec': acodec,
                   'fps': fmt.get('fps'),
                   'url': fmt.get('url')
                }
                
                if vcodec != 'none' and acodec != 'none':
                    video_audio_streams.append(stream)
                elif vcodec != 'none':
                    video_only_streams.append(stream)
                elif acodec != 'none' and vcodec == 'none':
                     audio_only_streams.append(stream)
            
            video_audio_streams.sort(key=lambda x: (int(x['resolution'].replace('p','')) if 'p' in x['resolution'] else 0), reverse=True)
            
            best_audio = None
            if audio_only_streams:
                audio_only_streams.sort(key=lambda x: (float(x['filesize'].split()[0]) if 'MB' in x['filesize'] else 0), reverse=True)
                best_audio = audio_only_streams[0]

            auto_merge_streams = []
            if best_audio:
                seen_resolutions = set()
                for v in video_only_streams:
                    res = v['resolution']
                    try:
                        res_val = int(res.replace('p', ''))
                    except:
                        res_val = 0
                    
                    if res_val >= 720 and res not in seen_resolutions:
                        auto_merge_streams.append({
                            'resolution': res,
                            'fps': v['fps'],
                            'video_format_id': v['format_id'],
                            'audio_format_id': best_audio['format_id'],
                            'vcodec': v['vcodec'],
                            'acodec': best_audio['acodec'],
                            'filesize': "Calc on server", 
                            'video_ext': v['ext']
                        })
                        seen_resolutions.add(res)

            return render_template('index.html',
                video_info=video_info,
                video_audio_streams=video_audio_streams,
                video_only_streams=video_only_streams,
                audio_only_streams=audio_only_streams,
                auto_merge_streams=auto_merge_streams
            )
            
    except Exception as e:
        logging.error(f"Error: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/preview')
def preview_video():
    url = request.args.get('url')
    format_id = request.args.get('itag')
    if not url or not format_id:
        flash('Missing parameters', 'error')
        return redirect(url_for('index'))
    try:
         with yt_dlp.YoutubeDL({'quiet':True}) as ydl:
             info = ydl.extract_info(url, download=False)
             tgt = next((f for f in info['formats'] if f['format_id'] == format_id), None)
             if not tgt: raise Exception("Stream not found")
             
             video_info = {
                 'title': info.get('title'),
                 'stream_url': tgt['url'],
                 'mime_type': f"video/{tgt['ext']}",
                 'resolution': f"{tgt.get('height')}p"
             }
             return render_template('preview.html', video_info=video_info)
    except Exception as e:
        flash(f"Preview failed: {e}", 'error')
        return redirect(url_for('index'))

@app.route('/api/download/start', methods=['POST'])
def start_download_job():
    data = request.json
    url = data.get('url')
    mode = data.get('mode', 'single') 
    
    if not url:
        return jsonify({'error': 'Missing URL'}), 400
        
    job_id, error = download_manager.create_job()
    
    if error:
        return jsonify({'error': error}), 429  # 429 Too Many Requests (or 409 Conflict)
    
    format_args = {'mode': mode}
    if mode == 'merge':
        format_args['video_format_id'] = data.get('video_format_id')
        format_args['audio_format_id'] = data.get('audio_format_id')
    else:
        format_args['format_id'] = data.get('format_id')
    
    download_manager.start_download(job_id, url, format_args)
    
    return jsonify({'job_id': job_id})

@app.route('/api/download/status/<job_id>')
def get_job_status(job_id):
    job = download_manager.get_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({
        'status': job['status'],
        'progress': job['progress'],
        'status_text': job['status_text'],
        'error': job['error']
    })

@app.route('/api/download/file/<job_id>')
def download_file(job_id):
    job = download_manager.get_job(job_id)
    if not job or job['status'] != 'completed' or not job['file_path']:
        return jsonify({'error': 'File not ready or expired'}), 404
    
    # Register immediate cleanup after serving
    @flask.after_this_request
    def cleanup_after_request(response):
        try:
             # Immediately remove the temp directory for this job
             if job.get('temp_dir') and os.path.exists(job['temp_dir']):
                 shutil.rmtree(job['temp_dir'])
                 logging.info(f"Immediate cleanup for job {job_id} after serving.")
             
             # Also remove job from memory to free up "completed" state fully
             # (Though create_job only checks ACTIVE status, it's good practice)
             download_manager.force_cleanup_job(job_id)
        except Exception as e:
            logging.error(f"Cleanup error during response: {e}")
        return response

    try:
        return send_file(
            job['file_path'],
            as_attachment=True,
            download_name=job['filename']
        )
    except Exception as e:
        return jsonify({'error': f"File error: {str(e)}"}), 500

import flask # Needed for after_this_request decorator ref

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
