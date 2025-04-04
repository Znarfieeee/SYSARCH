# CCS SIT-IN MONITORING SYSTEM

A Flask-based web application for managing and monitoring sit-in requests in the College of Computer Studies. This system digitizes and automates the traditional paper-based sit-in request process, making it more efficient for students, faculty, and administrative staff.

## Features

- Student Management
  - Registration and authentication
  - Profile management
  - Session tracking and limits (30 sessions for BSIT/BSCS/BSCPE, 15 for others)
  - Sit-in request submission and tracking

- Staff/Admin Features
  - Dashboard with real-time statistics
  - Student management
  - Announcement management
  - Approval/rejection of sit-in requests
  - Detailed reporting system with export options (CSV, Excel, PDF)
  - Session reset functionality

- Monitoring Features
  - Real-time classroom/lab capacity tracking
  - Attendance logging (check-in/check-out)
  - Historical data and analytics
  - Purpose-based and year level-based reporting

## Prerequisites

- Python 3.x
- SQLite3
- Flask and its dependencies
- Additional Python packages (specified in requirements.txt)

## Installation

1. Clone the repository
```bash
git clone <repository-url>
cd ccs-sitin-system
```

2. Create and activate a virtual environment (recommended)
```
python -m venv venv
venv\Scripts\activate 
```

3. Install required packages
```
pip install -r requirements.txt
```

4. Run the application
```
py app.py
```

## Project Structure
SYSARCH/
├── app.py                 # Main application file
├── staff_app.py           # Staff/Admin routes and functionality
├── dbhelper.py           # Database helper functions
├── static/               # Static assets
│   ├── css/             # Stylesheets
│   ├── js/              # JavaScript files
│   └── img/             # Images
├── templates/            # HTML templates
│   ├── student/         # Student-specific templates
│   └── staff/           # Staff-specific templates
└── app.db               # SQLite database

## Tech Stack ⚙️
### Backend:

- Flask (Python web framework)
- SQLite3 (Database)
- Jinja2 (Template engine)

### Frontend:

- HTML5
- CSS3
- JavaScript
- Tailwind CSS

### Features:

- Session-based authentication
- Role-based access control
- Real-time monitoring
- Export functionality (CSV, Excel, PDF)

### License
This project is proprietary and confidential. Unauthorized copying, modification, or distribution is strictly prohibited.

### Authors
- Mari Franz H. Espelita - Project Lead

### Acknowledgments
- College of Computer Studies, UC
- Jeff P. Salimbangon - Project Adviser