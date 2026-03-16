
PROJECT SUMMARY REPORT: pharmEZ

1. EXECUTIVE SUMMARY

pharmEZ is a state-of-the-art medical management web application engineered to bridge the gap between patients and complex healthcare coordination. By leveraging modern web technologies and Artificial Intelligence, it provides a seamless platform for medication tracking, prescription analysis, and pharmacy location services.

The system is designed with a patient-first approach, prioritizing data privacy, accessibility, and ease of use. It successfully integrates advanced AI capabilities—such as RAG-based prescription chat—with essential utility features like offline-capable scheduling and cost-effective location services.


2. SYSTEM ARCHITECTURE


The application is built on a modular, scalable architecture ensuring high availability and maintainability.


2.1 CORE TECHNOLOGY STACK

- Backend Framework: Flask (v3.0.0). Chosen for its flexibility and lightweight footprint, handling all HTTP requests, session security, and business logic routing.

- Database: MongoDB. A NoSQL document store ideal for the flexible data structures of medical prescriptions and chat logs.

- Frontend: Built with semantic HTML5, CSS3, and Vanilla JavaScript, ensuring broad browser compatibility and fast load times without heavy framework overhead.


2.2 ARTIFICIAL INTELLIGENCE ENGINE

- Prescription Analysis: Utilizes Google Gemini (Generative AI) to parse complex medical documents (PDF/Images) and extract structured data (Medication Name, Dosage, Frequency).

- RAG System: A Retrieval-Augmented Generation system, backed by a Pinecone vector database, allows users to "chat" with their prescriptions, asking context-aware questions.

2.3 EXTERNAL INTEGRATIONS


- Mapping Services: OpenStreetMap (OSM) via Nominatim and Overpass APIs. This strategic shift from paid Google Maps APIs ensures the project remains cost-effective while providing accurate, global pharmacy coverage.

- Scheduling: Google Calendar API integration allows users to sync their medication regimen directly to their personal calendars.

- Notifications: Automated email services using SMTP for delivery of adherence reports and alerts.


3. KEY FUNCTIONAL MODULES



3.1 THE "BRAIN": INTELLIGENT DASHBOARD
The core of pharmEZ is its dashboard, which serves as the command center for the user.
- Smart Upload: Users upload raw files; the system converts them into structured, actionable data.
- Contextual Chat: Users can query specific details about their meds (e.g., "Is this safe with aspirin?") and receive AI-generated, context-aware answers.

3.2 MEDICATION MANAGEMENT


A robust scheduling engine ensures users never miss a dose.
- Granular Timings: Specific slots for Morning (M), Afternoon (A), and Night (N).
- Safety Instructions: Tracks constraints like "Before Food" or "Avoid Alcohol".
- History & Logging: A complete audit trail of every dose taken or skipped.


3.3 PHARMACY LOCATOR


A geolocation module designed for reliability.
- Dual Search Mode: Supports both "Current Location" (GPS) and "Text Search" (Address).
- Visual Results: Displays a list of nearest pharmacies with distance calculations, sorted for convenience.



3.4 OTC SAFETY DATABASE
A self-contained module for medication safety.
- Database: Contains a curated list of Over-The-Counter medications.
- Search: Allows instant verification of drug indications and contraindications.



4.Conclusion


pharmEZ is a robust, feature-rich application that successfully bridges the gap between simple reminder apps and complex healthcare portals. By leveraging Modern AI for data interpretation and free open-source APIs for location services, it offers a premium user experience without high operational costs. The project is stable, well-structured, and ready for deployment or further scaling.




