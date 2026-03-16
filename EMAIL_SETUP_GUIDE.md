# How to Fix Email Sending Error (Gmail)

The error `Username and Password not accepted` occurs because Google no longer supports using your regular account password for third-party apps like this one. You must use an **App Password**.

## Step 1: Enable 2-Step Verification
1. Go to your [Google Account Security page](https://myaccount.google.com/security).
2. Under "How you sign in to Google", ensure **2-Step Verification** is turned **ON**.

## Step 2: Generate an App Password
1. Go to the [App Passwords page](https://myaccount.google.com/apppasswords) (you might need to sign in again).
   - If you can't find it, search "App Passwords" in the search bar at the top of the Google Account page.
2. Under **App name**, type `pharmEZ`.
3. Click **Create**.
4. Google will generate a 16-character password (e.g., `abcd efgh ijkl mnop`).

## Step 3: Update `.env` File
1. Copy the 16-character password (spaces don't matter, but it's safer to remove them if pasting directly, though most systems handle them).
2. Open your `.env` file in the project folder.
3. Replace your current password with the new App Password:

```env
EMAIL_SENDER=pharmeez@gmail.com
EMAIL_PASSWORD=yfourappppassword  <-- Paste the 16-char code here
```

4. Save the file and try sending the report again.
