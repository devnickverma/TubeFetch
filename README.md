# TubeFetch 🎬

TubeFetch is a Flask-based asynchronous YouTube video downloader built as a personal and educational portfolio project.

It supports high-quality video downloads (up to 1080p), audio merging using FFmpeg, real-time progress tracking, and automatic cleanup of temporary files.

---

## 🚀 Features
- Asynchronous background downloads
- High-quality video + audio merging
- Real-time progress tracking
- Automatic file cleanup
- Clean and responsive UI
- Free-tier cloud–safe architecture

---

## 🧠 How It Works
1. User submits a YouTube URL
2. Metadata is analyzed
3. A background job starts downloading
4. Progress is polled from the server
5. Video and audio are merged
6. File is delivered to the user
7. Temporary files are deleted

---

## ⚠️ Limitations
- Large videos may take several minutes on free hosting
- Maximum supported duration: 60 minutes
- Only one download can run at a time

---

## 📜 Disclaimer
This project is for educational and personal portfolio purposes only.  
Users are responsible for complying with YouTube’s Terms of Service.
