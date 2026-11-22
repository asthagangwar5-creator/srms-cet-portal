import csv
import io
import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from typing import Any
from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "srms-cet-inventory-secret-key")
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def log_activity(conn: sqlite3.Connection, actor: str, action: str, details: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    conn.execute(
        "INSERT INTO activity_logs (timestamp, actor, action, details) VALUES (?, ?, ?, ?)",
        (timestamp, actor, action, details),
    )


def login_required_page(view_func):
    @wraps(view_func)
    def wrapped_view(*args: Any, **kwargs: Any):
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        return view_func(*args, **kwargs)
    return wrapped_view


def login_required_api(view_func):
    @wraps(view_func)
    def wrapped_view(*args: Any, **kwargs: Any):
        if not session.get("user_id"):
            return jsonify({"error": "Authentication required. Please log in first."}), 401
        return view_func(*args, **kwargs)
    return wrapped_view


def init_db() -> None:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT 'General'
            )
            """
        )

        cursor.execute("PRAGMA table_info(inventory)")
        columns = {str(col["name"]) for col in cursor.fetchall()}
        if "department" not in columns:
            cursor.execute(
                "ALTER TABLE inventory ADD COLUMN department TEXT NOT NULL DEFAULT 'General'"
            )

        cursor.execute("SELECT COUNT(*) FROM inventory")
        row = cursor.fetchone()
        count = int(row[0]) if row is not None else 0

        if count == 0:
            sample_items = [
                ("Paracetamol 500mg", "Medicines", 1200, "Tablets", "Hospital / Medical"),
                ("Surgical Gloves (M)", "PPE", 30, "Pairs", "Hospital / Medical"),
                ("Digital Oscilloscope", "Equipment", 35, "Units", "ECE / CSE Lab"),
                ("Saline IV Drip (0.9%)", "Fluids", 210, "Bottles", "Hospital / Medical"),
            ]
            cursor.executemany(
                "INSERT INTO inventory (name, category, quantity, unit, department) VALUES (?, ?, ?, ?, ?)",
                sample_items,
            )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Admin'
            )
            """
        )

        cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", generate_password_hash("admin123"), "Admin"),
            )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS borrow_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                borrower_name TEXT NOT NULL,
                department TEXT NOT NULL,
                borrowed_qty INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Issued',
                issued_at TEXT NOT NULL,
                returned_at TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS srms_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department_or_lab TEXT NOT NULL,
                resource_name TEXT NOT NULL,
                allocated_qty INTEGER NOT NULL,
                status TEXT NOT NULL
            )
            """
        )

        conn.commit()
    finally:
        conn.close()


init_db()


def ask_ai_assistant(prompt: str, threshold: int = 50) -> str:
    q = prompt.lower().strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, quantity, unit, department FROM inventory")
        items = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT item_name, borrower_name, department, borrowed_qty, status FROM borrow_records WHERE status = 'Issued'"
        )
        issued = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT timestamp, actor, action, details FROM activity_logs ORDER BY id DESC LIMIT 5"
        )
        logs = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    low_stock = [i for i in items if int(i["quantity"]) < threshold]

    if "low" in q or "alert" in q or "restock" in q or "shortage" in q:
        if not low_stock:
            return f"All SRMS CET inventory items are at or above {threshold} units."
        lines = [
            f"- {i['name']} ({i['category']} | {i['department']}): {i['quantity']} {i['unit']}"
            for i in low_stock
        ]
        return f"Items below {threshold} units (restock priority):\n" + "\n".join(lines)

    if "borrow" in q or "issue" in q or "return" in q or "lent" in q:
        if not issued:
            return "No items are currently issued/borrowed."
        lines = [
            f"- {r['item_name']}: {r['borrowed_qty']} units to {r['borrower_name']} ({r['department']})"
            for r in issued
        ]
        return "Currently issued items:\n" + "\n".join(lines)

    if "log" in q or "activity" in q or "recent" in q or "history" in q:
        if not logs:
            return "No recent activity logs recorded yet."
        lines = [
            f"- [{l['timestamp']}] {l['actor']} — {l['action']}: {l['details']}"
            for l in logs
        ]
        return "Recent activity logs:\n" + "\n".join(lines)

    if "summary" in q or "total" in q or "count" in q or "overview" in q:
        total_units = sum(int(i["quantity"]) for i in items)
        by_cat: dict[str, int] = {}
        for i in items:
            cat = str(i["category"])
            by_cat[cat] = by_cat.get(cat, 0) + int(i["quantity"])
        cat_summary = ", ".join(f"{k}: {v}" for k, v in by_cat.items()) or "none"
        return (
            f"SRMS CET Overview: {len(items)} items, {total_units} total units, "
            f"{len(low_stock)} low-stock items (< {threshold}), {len(issued)} active borrows. "
            f"By category -> {cat_summary}."
        )

    words = [w for w in q.split() if len(w) > 2]
    matches = [
        i
        for i in items
        if any(
            w in str(i["name"]).lower()
            or w in str(i["category"]).lower()
            or w in str(i["department"]).lower()
            for w in words
        )
    ]
    if matches:
        lines = [
            f"- {i['name']} [{i['category']} | {i['department']}]: {i['quantity']} {i['unit']}"
            for i in matches[:8]
        ]
        return "Matching items:\n" + "\n".join(lines)

    return (
        f"SRMS CET Assistant ready ({len(items)} items tracked, {len(low_stock)} below {threshold} units). "
        "Try asking: 'summary', 'low stock alerts', 'issued items', 'recent activity', or search for an item."
    )


@app.route("/login", methods=["GET", "POST"])
def login_page():
    error: str | None = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = ?",
                (username,),
            )
            user = cursor.fetchone()

            if user is not None and check_password_hash(str(user["password_hash"]), password):
                session["user_id"] = int(user["id"])
                session["username"] = str(user["username"])
                session["role"] = str(user["role"])
                log_activity(conn, str(user["username"]), "LOGIN", "Signed in to SRMS CET portal")
                conn.commit()
                return redirect(url_for("dashboard"))
        finally:
            conn.close()

        error = "Invalid username or password."

    return render_template("login.html", active_page="login", error=error)


@app.route("/logout")
def logout_page():
    username = str(session.get("username") or "unknown")
    if session.get("user_id"):
        conn = get_db_connection()
        try:
            log_activity(conn, username, "LOGOUT", "Signed out of SRMS CET portal")
            conn.commit()
        finally:
            conn.close()
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/")
@login_required_page
def dashboard() -> str:
    return render_template("dashboard.html", active_page="dashboard")


@app.route("/add")
@login_required_page
def add_page() -> str:
    return render_template("add_item.html", active_page="add")


@app.route("/alerts")
@login_required_page
def alerts_page() -> str:
    return render_template("alerts.html", active_page="alerts")


@app.route("/borrow")
@login_required_page
def borrow_page() -> str:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, category, quantity, unit, department FROM inventory WHERE quantity > 0 ORDER BY name ASC"
        )
        items = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            """
            SELECT id, item_id, item_name, borrower_name, department, borrowed_qty, status, issued_at, returned_at
            FROM borrow_records
            ORDER BY id DESC
            """
        )
        records = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    return render_template("borrow.html", active_page="borrow", items=items, records=records)


@app.route("/srms", methods=["GET", "POST"])
@login_required_page
def handle_srms():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if request.method == "POST":
            dept = (request.form.get("department_or_lab") or "").strip()
            res_name = (request.form.get("resource_name") or "").strip()
            status = (request.form.get("status") or "Active").strip()
            try:
                qty = int(request.form.get("allocated_qty") or 1)
            except ValueError:
                qty = 1

            if dept and res_name:
                cursor.execute(
                    "INSERT INTO srms_records (department_or_lab, resource_name, allocated_qty, status) VALUES (?, ?, ?, ?)",
                    (dept, res_name, qty, status),
                )
                log_activity(conn, str(session.get("username") or "admin"), "SRMS_ALLOCATE", f"Allocated {qty} of '{res_name}' to {dept}")
                conn.commit()
            return redirect(url_for("handle_srms"))

        cursor.execute("SELECT id, department_or_lab, resource_name, allocated_qty, status FROM srms_records ORDER BY id DESC")
        records = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    return render_template("srms.html", active_page="srms", records=records)


@app.route("/activity")
@login_required_page
def activity_page() -> str:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, actor, action, details FROM activity_logs ORDER BY id DESC LIMIT 50"
        )
        logs = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

    return render_template("activity.html", active_page="activity", logs=logs)


@app.route("/ai")
@login_required_page
def ai_page() -> str:
    return render_template("ai_assistant.html", active_page="ai")


@app.route("/api/inventory", methods=["GET"])
@login_required_api
def get_inventory():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, quantity, unit, department FROM inventory")
        rows = cursor.fetchall()
    finally:
        conn.close()
    return jsonify([dict(row) for row in rows]), 200


@app.route("/api/inventory", methods=["POST"])
@login_required_api
def add_item():
    data: Any = request.get_json(silent=True) or request.form
    if not data or not data.get("name") or not data.get("category"):
        return jsonify({"error": "Item name and category are required."}), 400

    try:
        quantity = int(data.get("quantity", 0))
    except (ValueError, TypeError):
        quantity = 0

    name = str(data["name"]).strip()
    category = str(data["category"]).strip()
    unit = str(data.get("unit", "Units")).strip()
    department = str(data.get("department", "General")).strip() or "General"
    actor = str(session.get("username") or "api")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO inventory (name, category, quantity, unit, department) VALUES (?, ?, ?, ?, ?)",
            (name, category, quantity, unit, department),
        )
        new_id = cursor.lastrowid
        log_activity(conn, actor, "ADD_ITEM", f"Added '{name}' ({quantity} {unit}) in {category} [{department}]")
        conn.commit()
    finally:
        conn.close()

    return jsonify({"id": new_id, "name": name, "category": category, "quantity": quantity, "unit": unit, "department": department}), 201


@app.route("/api/inventory/<int:item_id>", methods=["PATCH"])
@login_required_api
def adjust_item_quantity(item_id: int):
    data: Any = request.get_json(silent=True) or {}
    actor = str(session.get("username") or "api")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, quantity, unit FROM inventory WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        if item is None:
            return jsonify({"error": "Item not found."}), 404

        current_qty = int(item["quantity"])
        if "delta" in data:
            new_qty = current_qty + int(data["delta"])
        elif "quantity" in data:
            new_qty = int(data["quantity"])
        else:
            return jsonify({"error": "Provide 'delta' or 'quantity'."}), 400

        if new_qty < 0:
            return jsonify({"error": "Quantity cannot be negative."}), 400

        cursor.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_qty, item_id))
        log_activity(conn, actor, "ADJUST_STOCK", f"'{item['name']}' changed from {current_qty} to {new_qty} {item['unit']}")
        conn.commit()
    finally:
        conn.close()

    return jsonify({"id": item_id, "name": str(item["name"]), "quantity": new_qty, "unit": str(item["unit"])}), 200


@app.route("/api/inventory/upload-csv", methods=["POST"])
@login_required_api
def upload_inventory_csv():
    if "file" not in request.files:
        return jsonify({"error": "No CSV file uploaded under field name 'file'."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename or not uploaded_file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a valid .csv file."}), 400

    text_stream = io.StringIO(uploaded_file.read().decode("utf-8-sig"))
    reader = csv.DictReader(text_stream)
    if not reader.fieldnames:
        return jsonify({"error": "CSV file is missing a header row."}), 400

    actor = str(session.get("username") or "api")
    conn = get_db_connection()
    inserted_count = updated_count = skipped_count = 0

    try:
        cursor = conn.cursor()
        for row in reader:
            norm_row = {str(k).strip().lower(): (str(v).strip() if v is not None else "") for k, v in row.items() if k is not None}
            name = norm_row.get("name", "")
            category = norm_row.get("category", "")
            if not name or not category:
                skipped_count += 1
                continue

            quantity = int(norm_row.get("quantity") or 0)
            unit = norm_row.get("unit") or "Units"
            department = norm_row.get("department") or "General"

            cursor.execute("SELECT id, quantity FROM inventory WHERE LOWER(name) = LOWER(?)", (name,))
            existing = cursor.fetchone()
            if existing is not None:
                updated_qty = int(existing["quantity"]) + quantity
                cursor.execute(
                    "UPDATE inventory SET category = ?, quantity = ?, unit = ?, department = ? WHERE id = ?",
                    (category, updated_qty, unit, department, int(existing["id"])),
                )
                updated_count += 1
            else:
                cursor.execute(
                    "INSERT INTO inventory (name, category, quantity, unit, department) VALUES (?, ?, ?, ?, ?)",
                    (name, category, quantity, unit, department),
                )
                inserted_count += 1

        log_activity(conn, actor, "CSV_UPLOAD", f"Uploaded '{uploaded_file.filename}': {inserted_count} inserted, {updated_count} updated, {skipped_count} skipped")
        conn.commit()
    finally:
        conn.close()

    return jsonify({"message": "CSV processed successfully.", "inserted": inserted_count, "updated": updated_count, "skipped": skipped_count}), 201


@app.route("/api/inventory/<int:item_id>", methods=["DELETE"])
@login_required_api
def delete_item(item_id: int):
    actor = str(session.get("username") or "api")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM inventory WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        if item is None:
            return jsonify({"error": "Item not found."}), 404

        cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        log_activity(conn, actor, "DELETE_ITEM", f"Deleted '{item['name']}' (ID {item_id})")
        conn.commit()
    finally:
        conn.close()

    return jsonify({"message": f"Item {item_id} deleted successfully."}), 200


@app.route("/api/borrow/issue", methods=["POST"])
@login_required_api
def issue_borrow_item():
    data: Any = request.get_json(silent=True) or request.form
    actor = str(session.get("username") or "api")
    item_id = int(data.get("item_id", 0))
    borrowed_qty = int(data.get("borrowed_qty", 1))
    borrower_name = str(data.get("borrower_name") or "").strip()
    department = str(data.get("department") or "General").strip() or "General"

    if item_id <= 0 or borrowed_qty <= 0 or not borrower_name:
        return jsonify({"error": "Item, borrower name, and positive quantity are required."}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, quantity, unit FROM inventory WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        if item is None:
            return jsonify({"error": "Selected item not found."}), 404

        available_qty = int(item["quantity"])
        if borrowed_qty > available_qty:
            return jsonify({"error": f"Insufficient stock. Available: {available_qty} {item['unit']}."}), 400

        new_qty = available_qty - borrowed_qty
        issued_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        cursor.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_qty, item_id))
        cursor.execute(
            "INSERT INTO borrow_records (item_id, item_name, borrower_name, department, borrowed_qty, status, issued_at) VALUES (?, ?, ?, ?, ?, 'Issued', ?)",
            (item_id, str(item["name"]), borrower_name, department, borrowed_qty, issued_at),
        )
        record_id = cursor.lastrowid
        log_activity(conn, actor, "ISSUE_ITEM", f"Issued {borrowed_qty} of '{item['name']}' to {borrower_name} ({department})")
        conn.commit()
    finally:
        conn.close()

    return jsonify({"id": record_id, "status": "Issued", "remaining_quantity": new_qty}), 201


@app.route("/api/borrow/<int:record_id>/return", methods=["POST"])
@login_required_api
def return_borrow_item(record_id: int):
    actor = str(session.get("username") or "api")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, item_id, item_name, borrower_name, borrowed_qty, status FROM borrow_records WHERE id = ?", (record_id,))
        rec = cursor.fetchone()
        if rec is None:
            return jsonify({"error": "Borrow record not found."}), 404
        if str(rec["status"]) == "Returned":
            return jsonify({"error": "Item is already marked as Returned."}), 400

        returned_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        cursor.execute("UPDATE borrow_records SET status = 'Returned', returned_at = ? WHERE id = ?", (returned_at, record_id))
        cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?", (int(rec["borrowed_qty"]), int(rec["item_id"])))
        log_activity(conn, actor, "RETURN_ITEM", f"Returned {rec['borrowed_qty']} of '{rec['item_name']}' from {rec['borrower_name']}")
        conn.commit()
    finally:
        conn.close()

    return jsonify({"id": record_id, "status": "Returned"}), 200


@app.route("/api/export/csv", methods=["GET"])
@login_required_api
def export_inventory_csv():
    actor = str(session.get("username") or "api")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, quantity, unit, department FROM inventory ORDER BY id ASC")
        rows = cursor.fetchall()
        log_activity(conn, actor, "EXPORT_CSV", f"Exported {len(rows)} inventory records to CSV")
        conn.commit()
    finally:
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Item Name", "Category", "Quantity", "Unit", "Department"])
    for row in rows:
        writer.writerow([row["id"], row["name"], row["category"], row["quantity"], row["unit"], row["department"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=srms_cet_inventory_report.csv"},
    )


@app.route("/api/ai", methods=["POST"])
@login_required_api
def ai_chat():
    data: Any = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400
    reply = ask_ai_assistant(prompt, threshold=int(data.get("threshold", 50)))
    return jsonify({"reply": reply}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)