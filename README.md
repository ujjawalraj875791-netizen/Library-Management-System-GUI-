# Library Hub — Python Tkinter Library Management System

A colourful desktop library management project built with Python, Tkinter/ttk, and JSON files.

## Features
- Multiple admin accounts with separate logins
- Admin-only user and book management
- User login with a read-only personal dashboard
- Book issue and return tracking with due dates
- Late fine calculation (default ₹5 per overdue day)
- Search catalogue by title or author
- Available-copy counts and active-loan lists
- JSON persistence across application restarts
- Backup and restore, including a safety backup before restore
- Passwords stored as salted PBKDF2-HMAC-SHA256 hashes
- Input validation and role-specific screens

## Requirements
- Python 3.10+ (Python 3.11+ recommended)
- Tkinter (included with most standard Windows Python installations)

No third-party packages are required.

## Run on Windows
1. Extract the ZIP file.
2. Open the `LibraryManagementSystem` folder.
3. Open Command Prompt or PowerShell in that folder.
4. Run:

   ```bash
   python main.py
   ```

## First login
- Role: **Admin**
- Username: `admin`
- Password: `Admin@123`

Change the default password after first login by opening **Admin accounts**, selecting the `admin` account, choosing **Edit selected**, and entering a new password. Do not use the default password for real data.

## Data files
The app automatically creates:
- `data/admins.json`
- `data/users.json`
- `data/books.json`
- `data/loans.json`

All files contain JSON lists. Do not manually edit them while the application is running. Make backups before editing/restoring data.

## Suggested first-use workflow
1. Sign in as the initial admin.
2. Open **Admin accounts** and create another admin with a unique username and a password of at least 8 characters.
3. Open **Users** and add library members.
4. Open **Books** and add titles, authors, categories, and copy counts.
5. Open **Issue / Return** to issue a book to an existing user.
6. Sign out and log in as the user to view their own loan and current fine.
7. Use **Backup / Restore** regularly.

## Fine and due-date policy
- Default loan period: 14 days from issue date.
- Default fine: ₹5 for each day after the due date.
- Fine is displayed dynamically for active loans and recorded when a return is processed.
- To change the policy, edit `LOAN_DAYS` and `DAILY_FINE` near the top of `main.py`.

## Notes / limitations
- This is a local, single-computer educational project. It is not designed for multiple people writing to the JSON files concurrently over a network.
- Admin/user authorization is enforced in the GUI flow, but JSON files are not encrypted. Protect the computer and backup folders.
- Fine payment is recorded as part of the return operation; this project does not process real payments.
