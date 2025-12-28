# TubeFetch 🎬

TubeFetch is a Flask-based asynchronous YouTube video downloader built as a personal and educational portfolio project. 

It handles video downloads via background jobs to ensure responsiveness and stability, supporting high-quality video (up to 1080p), audio merging using FFmpeg, and automatic resource cleanup.

## 🎥 Project Output / Demo

![TubeFetch Demo](output/output.gif)
*The GIF above demonstrates the application workflow: analyzing a video, selecting quality, tracking progress, and downloading the final merged file.*

## 🚀 Features

- **Asynchronous Background Downloads**: Utilizes background threads to handle downloads without blocking the web server.
- **High-Quality Merging**: Automatically combines best video and audio streams using FFmpeg for 1080p+ quality.
- **Real-Time Progress**: Live polling of download and conversion status.
- **Smart Resource Management**: Enforces single active job limits to prevent server overload.
- **Auto-Cleanup**: Automatically cleans up temporary files and finished downloads to maintain zero disk waste.
- **Cloud-Safe Architecture**: Designed to run reliably on free-tier hosting services with strict timeouts.

## 🧠 How It Works

1. **User submits a YouTube URL** via the web interface.
2. **Video metadata is analyzed** to present available formats and qualities.
3. **A background job starts** when the user selects a download option.
4. **Progress is tracked** via client-side polling while the server handles the heavy lifting.
5. **Video and audio are merged** (if required) using FFmpeg.
6. **File is delivered** to the user immediately upon completion.
7. **Temporary files are deleted** instantly to free up resources.

## 🛠️ Setup & Run Locally

### Prerequisites
- **Python 3.9+** or **3.10+**
- **FFmpeg**: Must be installed and added to your system's PATH.
  - *Windows*: Download and add `bin` folder to Environment Variables.
  - *Mac*: `brew install ffmpeg`
  - *Linux*: `sudo apt install ffmpeg`

### Installation

1. **Clone the repository** (if applicable) or navigate to the project folder.

2. **Create a virtual environment** (optional but recommended):
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

## ⚠️ Limitations

- **Performance**: Large 1080p videos may take several minutes to process on free-tier hosting compared to local execution.
- **Duration Limit**: Support is limited to videos under **60 minutes**.
- **Concurrency**: To ensure stability, **only one download job** can run at a time.
- **Scope**: Designed strictly for personal/portfolio demonstration, not high-volume public use.

## 📜 Disclaimer

This project is for **educational and personal portfolio purposes only**.  
Users are responsible for complying with YouTube’s Terms of Service. This application is not intended for commercial use or public distribution.
