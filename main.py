import json
import os
import shutil
import hashlib
import hmac
import secrets
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import date, datetime, timedelta

APP_NAME = "Library Hub"
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
BACKUP_DIR = ROOT / "backups"
FILES = {
    "admins": DATA_DIR / "admins.json",
    "users": DATA_DIR / "users.json",
    "books": DATA_DIR / "books.json",
    "loans": DATA_DIR / "loans.json",
}
DAILY_FINE = 5.0
LOAN_DAYS = 14
PBKDF2_ROUNDS = 240_000

# ---------- JSON storage and authentication ----------

def password_record(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ROUNDS).hex()
    return {"salt": salt, "hash": digest}


def verify_password(password, record):
    try:
        candidate = password_record(password, record["salt"])["hash"]
        return hmac.compare_digest(candidate, record["hash"])
    except (KeyError, TypeError, ValueError):
        return False


class Store:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        BACKUP_DIR.mkdir(exist_ok=True)
        for path in FILES.values():
            if not path.exists():
                path.write_text("[]", encoding="utf-8")
        self._seed_admin()

    def read(self, key):
        try:
            with FILES[key].open("r", encoding="utf-8") as f:
                value = json.load(f)
            if not isinstance(value, list):
                raise ValueError(f"{FILES[key].name} must contain a JSON list.")
            return value
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            raise RuntimeError(f"Cannot read {FILES[key].name}: {exc}") from exc

    def write(self, key, records):
        temp = FILES[key].with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        temp.replace(FILES[key])

    def _seed_admin(self):
        admins = self.read("admins")
        if not admins:
            admins.append({
                "id": "A001", "username": "admin",
                "password": password_record("Admin@123"),
                "full_name": "Main Administrator",
                "created_at": date.today().isoformat()
            })
            self.write("admins", admins)

    def next_id(self, key, prefix):
        existing = self.read(key)
        return f"{prefix}{max([int(''.join(c for c in r.get('id','') if c.isdigit()) or 0) for r in existing] + [0]) + 1:03d}"

    def backup(self, destination=None):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = Path(destination) if destination else BACKUP_DIR / f"library_backup_{stamp}"
        destination.mkdir(parents=True, exist_ok=True)
        for key, source in FILES.items():
            shutil.copy2(source, destination / source.name)
        return destination

    def restore(self, folder):
        folder = Path(folder)
        staged = {}
        for key, target in FILES.items():
            source = folder / target.name
            if not source.exists():
                raise ValueError(f"Backup is missing {target.name}.")
            with source.open("r", encoding="utf-8") as f:
                records = json.load(f)
            if not isinstance(records, list):
                raise ValueError(f"{target.name} must contain a JSON list.")
            staged[key] = records
        # Preserve current data as a safety backup before restoring.
        self.backup()
        for key, records in staged.items():
            self.write(key, records)
        self._seed_admin()


# ---------- Main application ----------

class LibraryApp(tk.Tk):
    BG = "#FFFFFF"
    NAV = "#EB007D"
    NAV_HOVER = "#8196CA"
    BLUE = "#EB007D"
    PURPLE = "#970B30"
    GREEN = "#005037"
    ORANGE = "#836F00"
    RED = "#5C0606"
    TEXT = "#172033"
    MUTED = "#ADBB10"
    WHITE = "#FFFFFF"

    def __init__(self):
        super().__init__()
        self.store = Store()
        self.current = None
        self.role = None
        self.title("Prachi's Library Managament ")
        self.geometry("1920x1080")
        self.minsize(720,480)
        self.configure(bg=self.BG)
        self._style()
        self.show_login()

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", background="white", fieldbackground="white",
                        foreground=self.TEXT, rowheight=30, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#E5EDFF", foreground=self.NAV,
                        font=("Segoe UI", 10, "bold"), padding=8)
        style.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", self.NAV)])
        style.configure("TCombobox", padding=7)
        style.configure("TEntry", padding=7)
        style.configure("TButton", padding=7, font=("Segoe UI", 10))
        style.configure("Accent.TButton", background=self.BLUE, foreground="white", padding=9)
        style.map("Accent.TButton", background=[("active", "#1D4ED8")])
        style.configure("Green.TButton", background=self.GREEN, foreground="white", padding=9)
        style.map("Green.TButton", background=[("active", "#047857")])

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def panel(self, parent, **kwargs):
        return tk.Frame(parent, bg=kwargs.pop("bg", self.WHITE), **kwargs)

    def label(self, parent, text, size=10, color=None, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=kwargs.pop("bg", self.WHITE),
                        fg=color or self.TEXT, font=("Segoe UI", size, "bold" if bold else "normal"),
                        **kwargs)

    def entry(self, parent, show=None, width=30):
        e = tk.Entry(parent, font=("Segoe UI", 11), relief="flat", bg="#F8FAFC",
                     fg=self.TEXT, insertbackground=self.TEXT, width=width,
                     highlightthickness=1, highlightbackground="#D8E1EF", highlightcolor=self.BLUE)
        if show:
            e.configure(show=show)
        return e

    def button(self, parent, text, command, color=None, **kwargs):
        color = color or self.BLUE
        return tk.Button(parent, text=text, command=command, bg=color, fg="white",
                         activebackground=color, activeforeground="white", relief="flat",
                         cursor="hand2", font=("Segoe UI", 10, "bold"), padx=13, pady=9,
                         **kwargs)

    def show_login(self):
        self.clear()
        outer = tk.Frame(self, bg=self.BG)
        outer.pack(fill="both", expand=True)
        left = tk.Frame(outer, bg=self.NAV, width=430)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Label(left, text="📚", bg=self.NAV, fg="white", font=("Segoe UI Emoji", 56)).pack(anchor="w", padx=48, pady=(110, 10))
        tk.Label(left, text="LIBRARY HUB", bg=self.NAV, fg="white", font=("Segoe UI", 26, "bold")).pack(anchor="w", padx=48)
        tk.Label(left, text="A smarter way to manage\nbooks, members and lending.", bg=self.NAV,
                 fg="#C7D2FE", font=("Segoe UI", 13), justify="left").pack(anchor="w", padx=48, pady=18)
        tk.Label(left, text="ADMIN • MEMBERS • BOOKS • FINES", bg=self.NAV, fg="#93C5FD",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=48, pady=(25, 0))

        right = tk.Frame(outer, bg=self.WHITE)
        right.pack(side="left", fill="both", expand=True)
        card = tk.Frame(right, bg=self.WHITE)
        card.place(relx=0.5, rely=0.5, anchor="center")
        self.label(card, "Welcome back", 25, bold=True).pack(anchor="w")
        self.label(card, "Sign in to continue to your library portal", 10, self.MUTED).pack(anchor="w", pady=(4, 26))
        self.label(card, "Login as", 10, bold=True).pack(anchor="w", pady=(0, 6))
        self.login_role = tk.StringVar(value="Admin")
        rolebox = ttk.Combobox(card, textvariable=self.login_role, values=["Admin", "User"], state="readonly", width=31)
        rolebox.pack(anchor="w", ipady=4, pady=(0, 15))
        self.label(card, "Username", 10, bold=True).pack(anchor="w", pady=(0, 6))
        self.login_user = self.entry(card, width=34)
        self.login_user.pack(anchor="w", ipady=8, pady=(0, 14))
        self.label(card, "Password", 10, bold=True).pack(anchor="w", pady=(0, 6))
        self.login_pass = self.entry(card, show="•", width=34)
        self.login_pass.pack(anchor="w", ipady=8, pady=(0, 20))
        self.button(card, "Sign in  →", self.login, self.BLUE, width=31).pack(anchor="w")
        self.label(card, "First-run admin: admin  |  Password: Admin@123", 9, self.MUTED).pack(anchor="w", pady=(18, 0))
        self.label(card, "Change the default password after first login.", 9, self.ORANGE).pack(anchor="w", pady=(4, 0))
        self.login_pass.bind("<Return>", lambda _e: self.login())
        self.login_user.focus_set()

    def login(self):
        username = self.login_user.get().strip()
        password = self.login_pass.get()
        role = self.login_role.get().lower()
        if not username or not password:
            messagebox.showwarning("Missing details", "Enter both username and password.")
            return
        key = "admins" if role == "admin" else "users"
        try:
            records = self.store.read(key)
        except RuntimeError as exc:
            messagebox.showerror("Data error", str(exc))
            return
        match = next((r for r in records if r.get("username", "").casefold() == username.casefold()), None)
        if not match or not verify_password(password, match.get("password", {})):
            messagebox.showerror("Login failed", "Invalid username or password.")
            return
        self.current, self.role = match, role
        self.show_dashboard()

    def logout(self):
        self.current = None
        self.role = None
        self.show_login()

    def show_dashboard(self):
        self.clear()
        shell = tk.Frame(self, bg=self.BG)
        shell.pack(fill="both", expand=True)
        nav = tk.Frame(shell, bg=self.NAV, width=225)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)
        tk.Label(nav, text="📚  LIBRARY HUB", bg=self.NAV, fg="white",
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=(25, 8))
        tk.Label(nav, text=f"{self.role.upper()} PORTAL", bg=self.NAV, fg="#93C5FD",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=22, pady=(0, 25))
        self.content = tk.Frame(shell, bg=self.BG)
        self.content.pack(side="left", fill="both", expand=True)
        if self.role == "admin":
            items = [
                ("▦  Dashboard", self.page_home), ("▤  Books", self.page_books),
                ("♙  Users", self.page_users), ("⇄  Issue / Return", self.page_loans),
                ("♙  Admin accounts", self.page_admins), ("◉  Backup / Restore", self.page_backup)
            ]
        else:
            items = [("▦  My dashboard", self.page_user_home), ("▤  Book catalogue", self.page_catalog)]
        for title, fn in items:
            b = tk.Button(nav, text=title, command=fn, bg=self.NAV, fg="#E2E8F0",
                          activebackground=self.NAV_HOVER, activeforeground="white",
                          relief="flat", anchor="w", padx=22, pady=13,
                          font=("Segoe UI", 10), cursor="hand2")
            b.pack(fill="x", padx=8, pady=2)
        tk.Frame(nav, bg="#334155", height=1).pack(fill="x", padx=18, pady=20)
        tk.Label(nav, text=f"Signed in as\n{self.current.get('full_name', self.current['username'])}",
                 bg=self.NAV, fg="#CBD5E1", justify="left", font=("Segoe UI", 9)).pack(anchor="w", padx=22, side="bottom", pady=(0, 12))
        self.button(nav, "Log out", self.logout, self.RED).pack(fill="x", padx=16, side="bottom", pady=(0, 22))
        self.page_home() if self.role == "admin" else self.page_user_home()

    def page_heading(self, title, subtitle=""):
        for child in self.content.winfo_children():
            child.destroy()
        head = tk.Frame(self.content, bg=self.BG)
        head.pack(fill="x", padx=28, pady=(24, 18))
        tk.Label(head, text=title, bg=self.BG, fg=self.NAV, font=("Segoe UI", 22, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(head, text=subtitle, bg=self.BG, fg=self.MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))
        body = tk.Frame(self.content, bg=self.BG)
        body.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        return body

    def card(self, parent, title, value, color):
        c = tk.Frame(parent, bg=self.WHITE, highlightbackground="#E2E8F0", highlightthickness=1)
        tk.Frame(c, bg=color, height=5).pack(fill="x")
        tk.Label(c, text=title, bg=self.WHITE, fg=self.MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(13, 2))
        tk.Label(c, text=str(value), bg=self.WHITE, fg=self.NAV, font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=16, pady=(0, 15))
        return c

    def make_table(self, parent, columns, headings=None, height=10):
        wrap = tk.Frame(parent, bg=self.WHITE)
        wrap.pack(fill="both", expand=True)
        tree = ttk.Treeview(wrap, columns=columns, show="headings", height=height)
        for col in columns:
            tree.heading(col, text=(headings or {}).get(col, col.replace("_", " ").title()))
            tree.column(col, width=max(90, int(750 / max(1, len(columns)))), anchor="w")
        yscroll = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        return tree

    def page_home(self):
        body = self.page_heading("Admin dashboard", "Overview of your library at a glance.")
        books, users, loans = self.store.read("books"), self.store.read("users"), self.store.read("loans")
        active = [x for x in loans if not x.get("returned")]
        available = sum(max(0, int(b.get("copies", 0)) - sum(1 for l in active if l.get("book_id") == b.get("id"))) for b in books)
        cards = tk.Frame(body, bg=self.BG)
        cards.pack(fill="x")
        for i, c in enumerate([
            self.card(cards, "Book titles", len(books), self.BLUE),
            self.card(cards, "Registered users", len(users), self.PURPLE),
            self.card(cards, "Available copies", available, self.GREEN),
            self.card(cards, "Active loans", len(active), self.ORANGE),
        ]):
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            cards.columnconfigure(i, weight=1)
        tk.Label(body, text="Currently issued books", bg=self.BG, fg=self.NAV,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(24, 10))
        table = self.make_table(body, ("loan_id", "book", "user", "issue_date", "due_date", "fine"))
        book_map = {b["id"]: b for b in books}
        user_map = {u["id"]: u for u in users}
        for loan in active:
            table.insert("", "end", values=(loan.get("id"), book_map.get(loan.get("book_id"), {}).get("title", "Deleted book"),
                         user_map.get(loan.get("user_id"), {}).get("full_name", "Deleted user"),
                         loan.get("issue_date"), loan.get("due_date"), f"₹{self.current_fine(loan):.2f}"))

    def page_books(self):
        body = self.page_heading("Book management", "Add, edit, remove and search the catalogue.")
        top = tk.Frame(body, bg=self.BG)
        top.pack(fill="x", pady=(0, 12))
        search = self.entry(top, width=34)
        search.pack(side="left", ipady=5)
        search.insert(0, "Search title or author...")
        table = self.make_table(body, ("id", "title", "author", "category", "copies"), height=10)
        def refresh():
            query = search.get().strip().casefold()
            for i in table.get_children(): table.delete(i)
            for b in self.store.read("books"):
                if query and query != "search title or author..." and query not in (b.get("title","")+" "+b.get("author","")).casefold():
                    continue
                table.insert("", "end", values=(b["id"], b["title"], b["author"], b.get("category",""), b.get("copies",0)))
        self.button(top, "Search", refresh).pack(side="left", padx=8)
        self.button(top, "Show all", lambda: (search.delete(0, "end"), refresh()), "#05449B").pack(side="left")
        actions = tk.Frame(body, bg=self.BG)
        actions.pack(fill="x", pady=12)
        self.button(actions, "+ Add book", lambda: self.book_form(refresh), self.GREEN).pack(side="left", padx=(0, 8),pady=(0,20))
        self.button(actions, "Edit selected", lambda: self.edit_book(table, refresh), self.PURPLE).pack(side="left", padx=8,pady=(0,20))
        self.button(actions, "Delete selected", lambda: self.delete_book(table, refresh), self.RED).pack(side="left", padx=8,pady=(0,20))
        refresh()

    def book_form(self, refresh, book=None):
        win = tk.Toplevel(self)
        win.title("Book details")
        win.configure(bg=self.WHITE)
        win.resizable(False, False)
        win.transient(self); win.grab_set()
        fields = [("Title", "title"), ("Author", "author"), ("Category", "category"), ("Total copies", "copies")]
        entries = {}
        tk.Label(win, text="Book details", bg=self.WHITE, fg=self.NAV, font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=22, pady=(20, 8))
        form = tk.Frame(win, bg=self.WHITE); form.pack(padx=22, pady=8)
        for label, key in fields:
            tk.Label(form, text=label, bg=self.WHITE, fg=self.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 4))
            e = self.entry(form, width=35)
            e.pack(ipady=5)
            if book: e.insert(0, str(book.get(key, "")))
            elif key == "copies": e.insert(0, "1")
            entries[key] = e
        def save():
            title, author = entries["title"].get().strip(), entries["author"].get().strip()
            try: copies = int(entries["copies"].get())
            except ValueError:
                messagebox.showerror("Invalid copies", "Total copies must be a whole number.", parent=win); return
            if not title or not author or copies < 0:
                messagebox.showerror("Invalid details", "Title and author are required; copies cannot be negative.", parent=win); return
            books = self.store.read("books")
            if book:
                active_count = sum(1 for l in self.store.read("loans") if l.get("book_id") == book["id"] and not l.get("returned"))
                if copies < active_count:
                    messagebox.showerror("Cannot reduce copies", f"{active_count} copy/copies are currently issued.", parent=win); return
                target = next(b for b in books if b["id"] == book["id"])
                target.update(title=title, author=author, category=entries["category"].get().strip(), copies=copies)
            else:
                books.append({"id": self.store.next_id("books", "B"), "title": title, "author": author,
                              "category": entries["category"].get().strip(), "copies": copies})
            self.store.write("books", books); win.destroy(); refresh()
        self.button(win, "Save book", save, self.GREEN).pack(fill="x", padx=22, pady=(12, 22))

    def selected_row(self, table):
        selected = table.selection()
        if not selected:
            messagebox.showwarning("Select a row", "Select a record in the table first.")
            return None
        return table.item(selected[0], "values")

    def edit_book(self, table, refresh):
        row = self.selected_row(table)
        if not row: return
        book = next((b for b in self.store.read("books") if b["id"] == row[0]), None)
        if book: self.book_form(refresh, book)

    def delete_book(self, table, refresh):
        row = self.selected_row(table)
        if not row: return
        if any(l.get("book_id") == row[0] and not l.get("returned") for l in self.store.read("loans")):
            messagebox.showerror("Book is issued", "Return all copies before deleting this book."); return
        if messagebox.askyesno("Confirm delete", f"Delete '{row[1]}'?"):
            self.store.write("books", [b for b in self.store.read("books") if b["id"] != row[0]])
            refresh()

    def page_users(self):
        body = self.page_heading("User management", "Only admins can create and manage member accounts.")
        top = tk.Frame(body, bg=self.BG); top.pack(fill="x", pady=(0, 12))
        table = self.make_table(body, ("id", "username", "full_name", "email"), height=10)
        def refresh():
            for i in table.get_children(): table.delete(i)
            for u in self.store.read("users"):
                table.insert("", "end", values=(u["id"], u["username"], u.get("full_name",""), u.get("email","")))
        self.button(top, "+ Add user", lambda: self.account_form("users", refresh), self.GREEN).pack(side="left")
        self.button(top, "Edit selected", lambda: self.edit_account(table, "users", refresh), self.PURPLE).pack(side="left", padx=8)
        self.button(top, "Delete selected", lambda: self.delete_account(table, "users", refresh), self.RED).pack(side="left", padx=8)
        refresh()

    def page_admins(self):
        body = self.page_heading("Admin accounts", "Create separate administrator accounts. Do not share credentials.")
        top = tk.Frame(body, bg=self.BG); top.pack(fill="x", pady=(0, 12))
        table = self.make_table(body, ("id", "username", "full_name", "created_at"), height=10)
        def refresh():
            for i in table.get_children(): table.delete(i)
            for a in self.store.read("admins"):
                table.insert("", "end", values=(a["id"], a["username"], a.get("full_name",""), a.get("created_at","")))
        self.button(top, "+ Add admin", lambda: self.account_form("admins", refresh), self.GREEN).pack(side="left")
        self.button(top, "Edit selected", lambda: self.edit_account(table, "admins", refresh), self.PURPLE).pack(side="left", padx=8)
        self.button(top, "Delete selected", lambda: self.delete_account(table, "admins", refresh), self.RED).pack(side="left", padx=8)
        refresh()

    def account_form(self, key, refresh, record=None):
        win = tk.Toplevel(self); win.title("Account details"); win.configure(bg=self.WHITE)
        win.resizable(False, False); win.transient(self); win.grab_set()
        title = "Edit account" if record else ("Create admin" if key == "admins" else "Create user")
        tk.Label(win, text=title, bg=self.WHITE, fg=self.NAV, font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=22, pady=(20, 8))
        form = tk.Frame(win, bg=self.WHITE); form.pack(padx=22, pady=8)
        specs = [("Username", "username"), ("Full name", "full_name"), ("Email", "email")]
        entries = {}
        for label, field in specs:
            tk.Label(form, text=label, bg=self.WHITE, fg=self.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 4))
            e = self.entry(form, width=36); e.pack(ipady=5)
            if record: e.insert(0, record.get(field, ""))
            entries[field] = e
        tk.Label(form, text="Password" + (" (leave blank to keep current)" if record else ""), bg=self.WHITE,
                 fg=self.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 4))
        password = self.entry(form, show="•", width=36); password.pack(ipady=5)
        def save():
            username = entries["username"].get().strip()
            full_name = entries["full_name"].get().strip()
            pwd = password.get()
            if not username or not full_name:
                messagebox.showerror("Missing details", "Username and full name are required.", parent=win); return
            records = self.store.read(key)
            if any(r.get("username","").casefold() == username.casefold() and (not record or r["id"] != record["id"]) for r in records):
                messagebox.showerror("Username exists", "Choose a unique username.", parent=win); return
            if not record and len(pwd) < 8:
                messagebox.showerror("Weak password", "New passwords must contain at least 8 characters.", parent=win); return
            if record:
                target = next(r for r in records if r["id"] == record["id"])
                target.update(username=username, full_name=full_name, email=entries["email"].get().strip())
                if pwd:
                    if len(pwd) < 8:
                        messagebox.showerror("Weak password", "Passwords must contain at least 8 characters.", parent=win); return
                    target["password"] = password_record(pwd)
            else:
                target = {"id": self.store.next_id(key, "A" if key == "admins" else "U"),
                          "username": username, "full_name": full_name,
                          "email": entries["email"].get().strip(), "password": password_record(pwd)}
                if key == "admins": target["created_at"] = date.today().isoformat()
                records.append(target)
            self.store.write(key, records); win.destroy(); refresh()
        self.button(win, "Save account", save, self.GREEN).pack(fill="x", padx=22, pady=(12, 22))

    def edit_account(self, table, key, refresh):
        row = self.selected_row(table)
        if not row: return
        if key == "admins" and row[0] == self.current["id"]:
            messagebox.showinfo("Current account", "For safety, manage another admin account from this screen."); return
        record = next((r for r in self.store.read(key) if r["id"] == row[0]), None)
        if record: self.account_form(key, refresh, record)

    def delete_account(self, table, key, refresh):
        row = self.selected_row(table)
        if not row: return
        if key == "admins":
            admins = self.store.read("admins")
            if row[0] == self.current["id"]:
                messagebox.showerror("Not allowed", "You cannot delete the account currently signed in."); return
            if len(admins) <= 1:
                messagebox.showerror("Not allowed", "At least one admin account must remain."); return
        if key == "users" and any(l.get("user_id") == row[0] and not l.get("returned") for l in self.store.read("loans")):
            messagebox.showerror("Active loans", "This user has books that must be returned first."); return
        if messagebox.askyesno("Confirm delete", f"Delete account '{row[1]}'?"):
            self.store.write(key, [r for r in self.store.read(key) if r["id"] != row[0]])
            refresh()

    def page_loans(self):
        body = self.page_heading("Issue & return", "Issue books to existing users and record returns.")
        form = tk.Frame(body, bg=self.WHITE, highlightbackground="#E2E8F0", highlightthickness=1)
        form.pack(fill="x", pady=(0, 14))
        tk.Label(form, text="Issue a book", bg=self.WHITE, fg=self.NAV, font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(14, 8))
        books = self.store.read("books"); users = self.store.read("users")
        book_options = [f'{b["id"]} | {b["title"]} (copies: {b.get("copies",0)})' for b in books]
        user_options = [f'{u["id"]} | {u["username"]} — {u.get("full_name","")}' for u in users]
        tk.Label(form, text="Book", bg=self.WHITE, fg=self.TEXT).grid(row=1, column=0, sticky="w", padx=16)
        bookvar = tk.StringVar()
        bookbox = ttk.Combobox(form, textvariable=bookvar, values=book_options, state="readonly", width=34)
        bookbox.grid(row=2, column=0, padx=16, pady=(4, 14), sticky="w")
        tk.Label(form, text="Existing user", bg=self.WHITE, fg=self.TEXT).grid(row=1, column=1, sticky="w", padx=16)
        uservar = tk.StringVar()
        userbox = ttk.Combobox(form, textvariable=uservar, values=user_options, state="readonly", width=34)
        userbox.grid(row=2, column=1, padx=16, pady=(4, 14), sticky="w")
        tk.Label(form, text="Due date (YYYY-MM-DD)", bg=self.WHITE, fg=self.TEXT).grid(row=1, column=2, sticky="w", padx=16)
        due = self.entry(form, width=18); due.insert(0, (date.today() + timedelta(days=LOAN_DAYS)).isoformat())
        due.grid(row=2, column=2, padx=16, pady=(4, 14), ipady=5, sticky="w")
        def issue():
            if not bookvar.get() or not uservar.get():
                messagebox.showwarning("Missing selection", "Select both a book and an existing user."); return
            try: due_date = date.fromisoformat(due.get().strip())
            except ValueError:
                messagebox.showerror("Invalid date", "Use YYYY-MM-DD for the due date."); return
            if due_date < date.today():
                messagebox.showerror("Invalid date", "Due date cannot be in the past."); return
            book_id, user_id = bookvar.get().split(" | ", 1)[0], uservar.get().split(" | ", 1)[0]
            loans = self.store.read("loans")
            book = next(b for b in self.store.read("books") if b["id"] == book_id)
            active_count = sum(1 for l in loans if l.get("book_id") == book_id and not l.get("returned"))
            if active_count >= int(book.get("copies", 0)):
                messagebox.showerror("Unavailable", "No copies of this book are currently available."); return
            if any(l.get("book_id") == book_id and l.get("user_id") == user_id and not l.get("returned") for l in loans):
                messagebox.showerror("Already issued", "This user already has an active loan for this book."); return
            loans.append({"id": self.store.next_id("loans", "L"), "book_id": book_id, "user_id": user_id,
                          "issue_date": date.today().isoformat(), "due_date": due_date.isoformat(),
                          "returned": False, "return_date": None, "fine_paid": 0.0})
            self.store.write("loans", loans); messagebox.showinfo("Success", "Book issued successfully.")
            self.page_loans()
        self.button(form, "Issue book", issue, self.GREEN).grid(row=2, column=3, padx=16, pady=(4, 14))
        tk.Label(body, text="Active loans", bg=self.BG, fg=self.NAV, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))
        table = self.make_table(body, ("loan_id", "book", "user", "issue_date", "due_date", "overdue_fine"), height=9)
        book_map = {b["id"]: b for b in self.store.read("books")}
        user_map = {u["id"]: u for u in self.store.read("users")}
        active = [l for l in self.store.read("loans") if not l.get("returned")]
        for l in active:
            table.insert("", "end", values=(l["id"], book_map.get(l["book_id"], {}).get("title", "Deleted"),
                user_map.get(l["user_id"], {}).get("username", "Deleted"), l["issue_date"], l["due_date"], f"₹{self.current_fine(l):.2f}"))
        actions = tk.Frame(body, bg=self.BG); actions.pack(fill="x", pady=10)
        def return_selected():
            row = self.selected_row(table)
            if not row: return
            loans = self.store.read("loans")
            loan = next((l for l in loans if l["id"] == row[0]), None)
            if not loan: return
            fine = self.current_fine(loan)
            if messagebox.askyesno("Confirm return", f"Record return?\nLate fine due: ₹{fine:.2f}"):
                loan["returned"] = True
                loan["return_date"] = date.today().isoformat()
                loan["fine_paid"] = fine
                self.store.write("loans", loans)
                messagebox.showinfo("Return recorded", f"Book returned. Fine recorded: ₹{fine:.2f}")
                self.page_loans()
        self.button(actions, "Record return", return_selected, self.PURPLE).pack(side="left")

    def current_fine(self, loan):
        try:
            due = date.fromisoformat(loan["due_date"])
            end = date.fromisoformat(loan["return_date"]) if loan.get("returned") and loan.get("return_date") else date.today()
            overdue = max(0, (end - due).days)
            return overdue * DAILY_FINE
        except (ValueError, KeyError, TypeError):
            return 0.0

    def page_backup(self):
        body = self.page_heading("Backup & restore", "Protect your records before major changes or when moving computers.")
        card = tk.Frame(body, bg=self.WHITE, highlightbackground="#E2E8F0", highlightthickness=1)
        card.pack(fill="x", pady=(0, 16))
        tk.Label(card, text="Create backup", bg=self.WHITE, fg=self.NAV, font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=(18, 6))
        tk.Label(card, text="Copies admins, users, books and loans JSON files into one backup folder.", bg=self.WHITE, fg=self.MUTED).pack(anchor="w", padx=20, pady=(0, 12))
        def make_backup():
            folder = filedialog.askdirectory(title="Choose backup destination", initialdir=str(BACKUP_DIR))
            if not folder: return
            try:
                path = self.store.backup(Path(folder) / f"library_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                messagebox.showinfo("Backup complete", f"Backup saved to:\n{path}")
                refresh_backups()
            except Exception as exc: messagebox.showerror("Backup failed", str(exc))
        self.button(card, "Create backup…", make_backup, self.GREEN).pack(anchor="w", padx=20, pady=(0, 18))
        restore_card = tk.Frame(body, bg=self.WHITE, highlightbackground="#E2E8F0", highlightthickness=1)
        restore_card.pack(fill="x")
        tk.Label(restore_card, text="Restore backup", bg=self.WHITE, fg=self.NAV, font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=20, pady=(18, 6))
        tk.Label(restore_card, text="Restoring replaces current records. A safety backup is created first.", bg=self.WHITE, fg=self.MUTED).pack(anchor="w", padx=20, pady=(0, 12))
        def restore():
            folder = filedialog.askdirectory(title="Select backup folder", initialdir=str(BACKUP_DIR))
            if not folder: return
            if not messagebox.askyesno("Replace current data?", "Current data will be replaced by this backup.\nA safety backup will be made first. Continue?"): return
            try:
                self.store.restore(folder)
                messagebox.showinfo("Restore complete", "Data restored successfully. The application will return to login.")
                self.logout()
            except Exception as exc: messagebox.showerror("Restore failed", str(exc))
        self.button(restore_card, "Choose backup to restore…", restore, self.ORANGE).pack(anchor="w", padx=20, pady=(0, 18))
        tk.Label(body, text=f"Automatic backup folder: {BACKUP_DIR}", bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(14, 0))
        tk.Label(body, text="Backups contain password hashes and personal data. Store them securely.", bg=self.BG,
                 fg=self.RED, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(5, 0))

    def page_user_home(self):
        body = self.page_heading("My library", f"Welcome, {self.current.get('full_name', self.current['username'])}. Here are your current loans.")
        loans = [l for l in self.store.read("loans") if l.get("user_id") == self.current["id"] and not l.get("returned")]
        books = {b["id"]: b for b in self.store.read("books")}
        total_fine = sum(self.current_fine(l) for l in loans)
        cards = tk.Frame(body, bg=self.BG); cards.pack(fill="x")
        for i, c in enumerate([
            self.card(cards, "Books currently issued", len(loans), self.BLUE),
            self.card(cards, "Current overdue fine", f"₹{total_fine:.2f}", self.ORANGE),
            self.card(cards, "Daily fine rate", f"₹{DAILY_FINE:.2f}", self.PURPLE)
        ]):
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0)); cards.columnconfigure(i, weight=1)
        tk.Label(body, text="Your issued books", bg=self.BG, fg=self.NAV, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(24, 10))
        table = self.make_table(body, ("book", "author", "issue_date", "due_date", "status", "fine"), height=12)
        for l in loans:
            b = books.get(l["book_id"], {})
            try: overdue = max(0, (date.today() - date.fromisoformat(l["due_date"])).days)
            except ValueError: overdue = 0
            status = f"Overdue {overdue} day(s)" if overdue else "On time"
            table.insert("", "end", values=(b.get("title", "Book unavailable"), b.get("author", ""), l["issue_date"], l["due_date"], status, f"₹{self.current_fine(l):.2f}"))
        if not loans:
            tk.Label(body, text="You have no books currently issued.", bg=self.BG, fg=self.MUTED).pack(anchor="w", pady=10)
        tk.Label(body, text=f"Fine policy: ₹{DAILY_FINE:.2f} per day after the due date. Please contact an admin to return a book.",
                 bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 0))

    def page_catalog(self):
        body = self.page_heading("Book catalogue", "Search titles and authors. This view is read-only.")
        top = tk.Frame(body, bg=self.BG); top.pack(fill="x", pady=(0, 12))
        search = self.entry(top, width=38); search.pack(side="left", ipady=5)
        search.insert(0, "Search title or author...")
        table = self.make_table(body, ("id", "title", "author", "category", "availability"), height=14)
        def refresh():
            q = search.get().strip().casefold()
            for i in table.get_children(): table.delete(i)
            books, loans = self.store.read("books"), self.store.read("loans")
            for b in books:
                if q and q != "search title or author..." and q not in (b.get("title","")+" "+b.get("author","")).casefold(): continue
                issued = sum(1 for l in loans if l.get("book_id") == b["id"] and not l.get("returned"))
                available = max(0, int(b.get("copies", 0)) - issued)
                table.insert("", "end", values=(b["id"], b["title"], b["author"], b.get("category",""), f"{available} available"))
        self.button(top, "Search", refresh).pack(side="left", padx=8)
        self.button(top, "Show all", lambda: (search.delete(0, "end"), refresh()), "#64748B").pack(side="left")
        refresh()


if __name__ == "__main__":
    app = LibraryApp()
    app.mainloop()
