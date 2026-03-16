# Deployment Guide for Render

This guide outlines the steps to deploy your **pharmEZ** application to [Render](https://render.com), a cloud hosting provider.

## Prerequisites

1.  **GitHub Repository**: Your code must be pushed to a GitHub repository.
2.  **Render Account**: Create a free account at [render.com](https://render.com).
3.  **Database Services**:
    *   **MongoDB Atlas**: You need a cloud-hosted MongoDB database (e.g., MongoDB Atlas).
    *   **Pinecone**: You need a Pinecone index for vector search.
    *   **Google Gemini**: You need a Google API Key.

---

## Step 1: Prepare Your Project

Ensure your project files are ready for deployment. I have already performed these steps for you:
1.  **`Procfile`**: Created a file named `Procfile` containing `web: gunicorn app:app`. This tells Render how to start your web server.
2.  **`requirements.txt`**: Added `gunicorn` to your dependencies.

**Important**: Push these changes to your GitHub repository before proceeding.
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

---

## Step 2: Create a Web Service on Render

1.  Log in to your [Render Dashboard](https://dashboard.render.com/).
2.  Click **New +** and select **Web Service**.
3.  Connect your GitHub account and select your **pharmEZ** repository.
4.  Configure the service:
    *   **Name**: `pharmeZ-app` (or any name you like)
    *   **Region**: Select the one closest to you (e.g., Singapore, Oregon).
    *   **Branch**: `main` (or your working branch).
    *   **Runtime**: `Python 3`.
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `gunicorn app:app` (Render should auto-detect this from the Procfile).
    *   **Plan**: Free (for hobby projects) or Starter.

---

## Step 3: Configure Environment Variables

This is the most critical step. You must provide your API keys and database connections.

1.  Scroll down to the **Environment Variables** section.
2.  Click **Add Environment Variable** for each of the following keys from your `.env` file:

| Key | Value Description |
| :--- | :--- |
| `FLASK_SECRET_KEY` | A random strong string (e.g., `s3cr3t_k3y_123`) |
| `MONGO_URI` | Your MongoDB Connection String (must be accessible from the internet, e.g., MongoDB Atlas) |
| `GOOGLE_API_KEY` | Your Google Gemini API Key |
| `PINECONE_API_KEY` | Your Pinecone API Key |
| `PINECONE_ENV` | Your Pinecone Environment (e.g., `us-east-1`) |
| `PINECONE_INDEX_NAME` | Your Index Name (e.g., `medimate-index`) |
| `MAIL_USERNAME` | (Optional) Your email for sending notifications |
| `MAIL_PASSWORD` | (Optional) Your email app password |

**Note regarding `MONGO_URI`**: Ensure your connection string looks like:
`mongodb+srv://<username>:<password>@cluster0.xyz.mongodb.net/?retryWrites=true&w=majority`
*Make sure to whitelist `0.0.0.0/0` (Allow from Anywhere) in your MongoDB Atlas Network Access settings so Render can connect.*

---

## Step 4: Deploy

1.  Click **Create Web Service**.
2.  Render will start building your application. You can watch the logs in the dashboard.
3.  Once the build finishes, you will see a green **Live** badge.
4.  Click the URL provided (e.g., `https://pharmeZ-app.onrender.com`) to access your app!

---

## Troubleshooting

-   **Build Failed**: Check the logs. Usually, this means a package in `requirements.txt` failed to install.
-   **Application Error**: Check the *Service Logs*.
    -   If you see "Internal Server Error" or "Connection refused", check your `MONGO_URI` and ensure your database is accepting connections (Network Access).
    -   If you see "Google API Error", check your `GOOGLE_API_KEY`.
-   **Files Disappearing**:
    -   Render's free tier uses an *ephemeral filesystem*. This means any prescription images you upload will be deleted if the server restarts (which happens frequently on the free tier).
    -   The *data extracted* from the prescriptions is safe because it is stored in your MongoDB database.
    -   To persist images, you would need to implement cloud storage (like AWS S3) or upgrade to a Render plan with a Persistent Disk (and configure the code to use it).

## Final Verification
After deployment, try to:
1.  Log in / Register.
2.  Upload a prescription.
3.  Verify that the extraction works (this confirms Google API and MongoDB are working).
