import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import yt_dlp
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "local_dev_secret_key")

# Local downloads directory
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Global progress tracker
download_progress = {}

def progress_hook(d):
    """Track download progress"""
    if d['status'] == 'downloading':
        video_id = d.get('info_dict', {}).get('id', 'unknown')
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        if total > 0:
            percentage = (downloaded / total) * 100
            download_progress[video_id] = {
                'percentage': round(percentage, 1),
                'status': 'downloading'
            }
    elif d['status'] == 'finished':
        video_id = d.get('info_dict', {}).get('id', 'unknown')
        download_progress[video_id] = {
            'percentage': 100.0,
            'status': 'complete'
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_video():
    """Analyze YouTube video and return available formats"""
    try:
        url = request.form.get('url', '').strip()
        if not url:
            flash('Please enter a YouTube URL', 'error')
            return redirect(url_for('index'))
        
        # Simple analysis - no restrictions
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            duration = info.get('duration', 0)
            video_info = {
                'title': info.get('title', 'Unknown'),
                'author': info.get('uploader', 'Unknown'),
                'length': f"{duration // 60}:{duration % 60:02d}",
                'thumbnail': info.get('thumbnail', ''),
                'video_id': info.get('id'),
                'url': url,
            }
            
            # Get all formats without filtering
            formats = info.get('formats', [])
            video_audio_streams = []
            video_only_streams = []
            audio_only_streams = []
            
            for fmt in formats:
                height = fmt.get('height')
                ext = fmt.get('ext', 'unknown')
                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                filesize = fmt.get('filesize') or fmt.get('filesize_approx', 0)
                
                if ext == 'mhtml':
                    continue
                
                stream = {
                    'format_id': fmt['format_id'],
                    'resolution': f"{height}p" if height else "Audio",
                    'filesize': format_bytes(filesize),
                    'ext': ext,
                    'vcodec': vcodec,
                    'acodec': acodec,
                    'fps': fmt.get('fps'),
                }
                
                if vcodec != 'none' and acodec != 'none':
                    video_audio_streams.append(stream)
                elif vcodec != 'none':
                    video_only_streams.append(stream)
                elif acodec != 'none':
                    audio_only_streams.append(stream)
            
            # Sort by quality
            video_audio_streams.sort(key=lambda x: int(x['resolution'].replace('p','')) if 'p' in x['resolution'] else 0, reverse=True)
            video_only_streams.sort(key=lambda x: int(x['resolution'].replace('p','')) if 'p' in x['resolution'] else 0, reverse=True)
            
            # Auto-merge options for high quality
            auto_merge_streams = []
            if audio_only_streams and video_only_streams:
                best_audio = audio_only_streams[0]
                seen = set()
                for v in video_only_streams:
                    res = v['resolution']
                    if res not in seen and 'p' in res:
                        auto_merge_streams.append({
                            'resolution': res,
                            'fps': v['fps'],
                            'video_format_id': v['format_id'],
                            'audio_format_id': best_audio['format_id'],
                            'vcodec': v['vcodec'],
                            'acodec': best_audio['acodec'],
                        })
                        seen.add(res)
            
            return render_template('index.html',
                video_info=video_info,
                video_audio_streams=video_audio_streams,
                video_only_streams=video_only_streams,
                audio_only_streams=audio_only_streams,
                auto_merge_streams=auto_merge_streams
            )
            
    except Exception as e:
        logging.error(f"Error analyzing video: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/download/<format_id>')
def download_video(format_id):
    """Download video in specified format"""
    try:
        url = request.args.get('url')
        if not url:
            flash('Missing URL', 'error')
            return redirect(url_for('index'))
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': str(DOWNLOADS_DIR / '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                return send_file(filename, as_attachment=True, download_name=os.path.basename(filename))
            else:
                flash('Download failed', 'error')
                return redirect(url_for('index'))
                
    except Exception as e:
        logging.error(f"Download error: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/download_merged/<video_format_id>/<audio_format_id>')
def download_merged(video_format_id, audio_format_id):
    """Download and merge video + audio"""
    try:
        url = request.args.get('url')
        if not url:
            flash('Missing URL', 'error')
            return redirect(url_for('index'))
        
        ydl_opts = {
            'format': f"{video_format_id}+{audio_format_id}",
            'outtmpl': str(DOWNLOADS_DIR / '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # yt-dlp may change extension after merge
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                filename = base + '.mp4'
            
            if os.path.exists(filename):
                return send_file(filename, as_attachment=True, download_name=os.path.basename(filename))
            else:
                flash('Merge failed', 'error')
                return redirect(url_for('index'))
                
    except Exception as e:
        logging.error(f"Merge error: {e}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/progress/<video_id>')
def get_progress(video_id):
    """Get download progress"""
    progress = download_progress.get(video_id, {'percentage': 0, 'status': 'waiting'})
    return jsonify(progress)

def format_bytes(bytes_size):
    """Format bytes to human readable"""
    if not bytes_size:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

if __name__ == '__main__':
    print("=" * 60)
    print("TubeFetch - Local YouTube Downloader")
    print("=" * 60)
    print("This application is designed for LOCAL USE ONLY")
    print("Educational and personal use only")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=True)
