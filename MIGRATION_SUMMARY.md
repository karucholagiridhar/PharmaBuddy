# Flask Migration Complete

The application has been fully migrated to a production-ready Flask architecture.
Location: `c:\Users\visha\Desktop\sdc\medical upgraded\pharmEZ_flask`

## Structure
- **app.py**: Main entry point.
- **utils/**: Backend logic (Auth, AI, Reminder).
- **templates/**: HTML pages (Jinja2).
- **static/css/**: Custom styling.

## How to Run
1. Open terminal in `pharmEZ_flask`:
   ```powershell
   cd "pharmEZ_flask"
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Run the app:
   ```powershell
   python app.py
   ```
4. Visit `http://localhost:5000`

## Features
- **Modern UI**: Clean, responsive layout with Teal theme.
- **Dashboard**: Prescription upload, AI analysis, and Chat.
- **Medications**: Scheduler with Google Calendar sync.
- **Safety**: OTC interaction checker.
- **Pharmacy**: Interactive locator.
