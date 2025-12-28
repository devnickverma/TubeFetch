# TubeFetch 🎬

**A local YouTube video downloader for educational and personal use.**

TubeFetch is a Flask-based application that allows you to download YouTube videos locally on your machine with automatic video+audio merging using FFmpeg.

> **⚠️ Important**: This project is designed to run **locally only** for educational and personal use. It is **not intended for public cloud deployment or commercial use**.

## 🎥 Project Output / Demo

![TubeFetch Demo](output/output.gif)
*The GIF above demonstrates the application workflow: analyzing a video, selecting quality, and downloading the final merged file.*

## 🚀 Features

- **Unrestricted Downloads**: No artificial limits on video duration, resolution, or file size
- **Best Quality**: Downloads the best available video and audio streams
- **Automatic Merging**: Uses FFmpeg to merge video and audio into a single MP4 file
- **Simple Interface**: Clean Flask-based web UI
- **Local Storage**: All downloads saved to local `downloads/` directory
- **Progress Tracking**: Real-time download progress feedback

## 🛠️ Setup & Run Locally

### Prerequisites
- **Python 3.9+** or **3.10+**
- **FFmpeg**: Must be installed and added to your system's PATH
  - *Windows*: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add `bin` folder to Environment Variables
  - *Mac*: `brew install ffmpeg`
  - *Linux*: `sudo apt install ffmpeg`

### Installation

1. **Navigate to the project folder**:
   ```bash
   cd TubeFetch
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App

1. Start the Flask application:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

3. Enter a YouTube URL, select your preferred quality, and download!

## 📂 Project Structure

```
TubeFetch/
├── app.py              # Main Flask application
├── templates/          # HTML templates
│   ├── index.html     # Main UI
│   └── preview.html   # Video preview
├── static/            # CSS and JavaScript
├── downloads/         # Downloaded videos (created automatically)
└── requirements.txt   # Python dependencies
```

## 🎯 How It Works

1. User submits a YouTube URL via the web interface
2. yt-dlp analyzes the video and extracts available formats
3. User selects desired quality (or auto-merge option)
4. yt-dlp downloads video and audio streams
5. FFmpeg merges them into a single MP4 file
6. File is delivered to the user's browser
7. Video is saved in the `downloads/` folder

## 📜 Disclaimer

This project is for **educational and personal use only**.  
Users are responsible for complying with YouTube's Terms of Service.  
This application is not intended for commercial use, public distribution, or cloud deployment.

## 🔧 Technical Notes

- Uses `yt-dlp` for video extraction and downloading
- Requires local FFmpeg installation for stream merging
- Runs on Flask development server (localhost only)
- All processing happens server-side (your local machine)
