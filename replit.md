# YouTube Video Downloader

## Overview

A Flask-based web application that allows users to download YouTube videos by providing a URL. The application validates YouTube URLs, extracts video metadata, and provides download functionality with real-time progress tracking. Built with a clean, responsive web interface using Bootstrap and JavaScript for enhanced user experience.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask for server-side rendering
- **UI Framework**: Bootstrap 5 with dark theme support for responsive design
- **JavaScript**: Vanilla JavaScript for client-side interactions and progress tracking
- **Icon System**: Feather Icons for consistent iconography
- **Styling**: Custom CSS combined with Bootstrap for enhanced visual appeal

### Backend Architecture
- **Web Framework**: Flask application with route-based architecture
- **Video Processing**: PyTube library for YouTube video extraction and download
- **URL Validation**: Regular expressions and URL parsing for YouTube URL validation
- **Progress Tracking**: Global dictionary-based progress tracking with threading support
- **File Management**: Temporary file handling for download processing

### Core Features
- **URL Validation**: Comprehensive YouTube URL format validation including various URL patterns
- **Video Metadata Extraction**: Retrieves video information before download
- **Progress Monitoring**: Real-time download progress tracking with AJAX polling
- **File Size Formatting**: Human-readable file size conversion utilities
- **Flash Messaging**: User feedback system for success and error states

### Session Management
- **Secret Key**: Environment-based session secret with development fallback
- **Flash Messages**: Flask's built-in flash messaging for user notifications

### Error Handling
- **Logging**: Python logging configuration for debugging and monitoring
- **URL Parsing**: Robust URL parsing with error handling for malformed URLs
- **Download Management**: Progress tracking with timeout mechanisms

## External Dependencies

### Python Libraries
- **Flask**: Web framework for routing and templating
- **PyTube**: YouTube video extraction and download functionality
- **urllib**: URL parsing and query parameter extraction

### Frontend Libraries
- **Bootstrap 5**: CSS framework with dark theme support
- **Feather Icons**: Icon library for UI elements

### Runtime Dependencies
- **Python Threading**: For background download processing
- **Temporary File System**: For managing downloaded content
- **Environment Variables**: For configuration management