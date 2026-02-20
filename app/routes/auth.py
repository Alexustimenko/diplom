# app/routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, send_file
from app.db import get_conn
import bcrypt
import io
from docx import Document
from openpyxl import Workbook

auth_bp = Blueprint("auth", __name__)

def _require_admin():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("is_admin") != 1:
        return "Forbidden", 403
    return None
def _require_login():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return None



@auth_bp.route("/")
def index():
    q = request.args.get("q", "").strip()

    conn = get_conn()
    cur = conn.cursor()

    if q:
        like = f"%{q}%"
        # строго через VIEW
        cur.execute(
            """
            SELECT * FROM dbo.vw_products
            WHERE
                (name LIKE ?)
                OR (description LIKE ?)
                OR (brand_name LIKE ?)
                OR (category_name LIKE ?)
            ORDER BY product_id DESC
            """,
            like, like, like, like
        )
    else:
        cur.execute("SELECT * FROM dbo.vw_products ORDER BY product_id DESC")

    products = cur.fetchall()
    conn.close()

    return render_template("index.html", products=products, q=q)


# ✅ Страница товара (галерея по всем image_id)
@auth_bp.route("/product/<int:pid>")
def product(pid):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM dbo.vw_products WHERE product_id = ?", pid)
    p = cur.fetchone()
    if not p:
        conn.close()
        return "Not Found", 404

    cur.execute("SELECT image_id FROM dbo.images WHERE product_id = ? ORDER BY image_id DESC", pid)
    images = cur.fetchall()  # [(image_id,), ...]

    conn.close()
    return render_template("product.html", p=p, images=images)


@auth_bp.route("/product_image/<int:pid>")
def product_image(pid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT TOP 1 image_data FROM dbo.images WHERE product_id=? ORDER BY image_id DESC", pid)
    row = cur.fetchone()
    conn.close()

    if not row or row[0] is None:
        return "", 404

    data = row[0]
    if isinstance(data, memoryview):
        data = data.tobytes()
    else:
        data = bytes(data)

    return send_file(io.BytesIO(data), mimetype="image/jpeg")


@auth_bp.route("/image/<int:image_id>")
def image_by_id(image_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT image_data FROM dbo.images WHERE image_id = ?", image_id)
    row = cur.fetchone()
    conn.close()

    if not row or row[0] is None:
        return "", 404

    data = row[0]
    if isinstance(data, memoryview):
        data = data.tobytes()
    else:
        data = bytes(data)

    return send_file(io.BytesIO(data), mimetype="image/jpeg")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        customer_type = request.form.get("customer_type", "fiz").strip()

        if not email or not password:
            return render_template("register.html", error="Заполни email и пароль")

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("EXEC dbo.sp_register_user ?, ?, ?", email, hashed, customer_type)
        result = cur.fetchone()[0]
        conn.commit()
        conn.close()

        if result == -1:
            return render_template("register.html", error="Пользователь уже существует")
        if result == -2:
            return render_template("register.html", error="Неверный тип клиента")

        return render_template("register.html", success="Аккаунт создан! Теперь можно входить.")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Заполни email и пароль")

        if email == "admin" and password == "admin":
            session["user_id"] = 0
            session["email"] = "admin"
            session["is_admin"] = 1
            return redirect("/admin")

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("EXEC dbo.sp_login_user ?", email)
        row = cur.fetchone()
        conn.close()

        if not row:
            return render_template("login.html", error="Ошибка входа")

        if not bcrypt.checkpw(password.encode(), row.password_hash.encode()):
            return render_template("login.html", error="Ошибка входа")

        session["user_id"] = row.user_id
        session["email"] = email
        session["is_admin"] = 1 if row.is_admin else 0

        return redirect("/admin" if row.is_admin else "/")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@auth_bp.route("/cabinet")
def cabinet():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template(
        "cabinet.html",
        email=session.get("email"),
        customer_type=session.get("customer_type"),
    )


@auth_bp.route("/admin", methods=["GET", "POST"])
def admin():
    gate = _require_admin()
    if gate:
        return gate

    error = None
    success = None

    # ================= POST (CRUD) =================
    if request.method == "POST":
        action = request.form.get("action", "").strip()

        try:
            conn = get_conn()
            cur = conn.cursor()

            # ---------- BRANDS ----------
            if action == "add_brand":
                name = request.form.get("brand_name", "").strip()
                cur.execute("EXEC dbo.sp_add_brand ?", name)
                conn.commit()
                success = "Бренд добавлен"

            elif action == "edit_brand":
                cur.execute(
                    "EXEC dbo.sp_edit_brand ?, ?",
                    int(request.form["brand_id"]),
                    request.form["brand_name"]
                )
                conn.commit()
                success = "Бренд обновлён"

            elif action == "delete_brand":
                cur.execute("EXEC dbo.sp_delete_brand ?", int(request.form["brand_id"]))
                conn.commit()
                success = "Бренд удалён"

            # ---------- CATEGORIES ----------
            elif action == "add_category":
                name = request.form["category_name"]
                parent = request.form.get("parent_id") or None
                cur.execute("EXEC dbo.sp_add_category ?, ?", name, parent)
                conn.commit()
                success = "Категория добавлена"

            elif action == "edit_category":
                cid = int(request.form["category_id"])
                name = request.form["category_name"]
                parent = request.form.get("parent_id") or None
                cur.execute("EXEC dbo.sp_edit_category ?, ?, ?", cid, name, parent)
                conn.commit()
                success = "Категория обновлена"

            elif action == "delete_category":
                cur.execute("EXEC dbo.sp_delete_category ?", int(request.form["category_id"]))
                conn.commit()
                success = "Категория удалена"

            # ---------- PRODUCTS ----------
            elif action == "add_product":
                name = request.form.get("name", "").strip()
                description = request.form.get("description") or None

                price = float(request.form["price"])
                old_price = request.form.get("old_price") or None
                stock = int(request.form["stock"])

                category_id = request.form.get("category_id") or None
                brand_id = request.form.get("brand_id") or None

                old_price = float(old_price) if old_price else None
                category_id = int(category_id) if category_id else None
                brand_id = int(brand_id) if brand_id else None

                cur.execute("""
                    EXEC dbo.sp_add_product
                        @name = ?,
                        @description = ?,
                        @price = ?,
                        @old_price = ?,
                        @stock = ?,
                        @category_id = ?,
                        @brand_id = ?
                """, name, description, price, old_price, stock, category_id, brand_id)

                product_id = cur.fetchone()[0]

                for f in request.files.getlist("images"):
                    if f.filename:
                        cur.execute(
                            "INSERT INTO dbo.images(product_id, image_data) VALUES (?, ?)",
                            product_id, f.read()
                        )

                conn.commit()
                success = "Товар добавлен"

            elif action == "edit_product":
                pid = int(request.form["product_id"])

                cur.execute("""
                    EXEC dbo.sp_update_product ?, ?, ?, ?, ?, ?, ?, ?
                """,
                            pid,  # @product_id
                            request.form["name"],  # @name
                            request.form.get("description") or None,  # @description
                            float(request.form["price"]),  # @price
                            float(request.form["old_price"]) if request.form.get("old_price") else None,  # @old_price
                            int(request.form["stock"]),  # @stock
                            int(request.form["category_id"]) if request.form.get("category_id") else None,
                            # @category_id
                            int(request.form["brand_id"]) if request.form.get("brand_id") else None  # @brand_id
                            )

                if request.form.get("replace_images"):
                    cur.execute("DELETE FROM dbo.images WHERE product_id=?", pid)

                for f in request.files.getlist("images"):
                    if f.filename:
                        cur.execute(
                            "INSERT INTO dbo.images(product_id,image_data) VALUES (?,?)",
                            pid, f.read()
                        )

                conn.commit()
                success = "Товар обновлён"
            elif action == "delete_product":
                pid = int(request.form["product_id"])
                cur.execute("DELETE FROM dbo.images WHERE product_id=?", pid)
                cur.execute("DELETE FROM dbo.products WHERE product_id=?", pid)
                conn.commit()
                success = "Товар удалён"

            conn.close()

            return redirect("/admin")

        except Exception as e:
            try:
                conn.close()
            except:
                pass
            error = str(e)

    # ================= GET =================
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id_brand,name FROM dbo.vw_brands")
    brands = cur.fetchall()

    cur.execute("SELECT category_id,name,parent_id,parent_name FROM dbo.vw_categories")
    categories = cur.fetchall()

    cur.execute("SELECT * FROM dbo.vw_products ORDER BY product_id DESC")
    products = cur.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        brands=brands,
        categories=categories,
        products=products,
        tab="products",
        error=error,
        success=success
    )


@auth_bp.route("/admin/reports")
def admin_reports():
    gate = _require_admin()
    if gate:
        return gate

    date_from = request.args.get("from", "").strip()
    date_to   = request.args.get("to", "").strip()

    # если даты не задали — подставим сегодня
    if not date_from or not date_to:
        from datetime import date
        today = date.today().isoformat()
        date_from = today
        date_to = today

    # если пользователь перепутал местами даты — поменяем
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    conn = get_conn()
    cur = conn.cursor()

    # 0) товары по категориям (старый VIEW)
    cur.execute("SELECT * FROM dbo.vw_report_products_per_category ORDER BY category_name")
    report_rows = cur.fetchall()

    # 1) заказы за период
    cur.execute("EXEC dbo.sp_report_orders_period_grouped ?, ?", date_from, date_to)
    orders_rows = cur.fetchall()

    # 2) клиенты (история заказов за период)
    cur.execute("EXEC sp_report_clients_orders")
    customers_rows = cur.fetchall()

    # 3) проданные товары за период
    cur.execute("EXEC dbo.sp_report_sold_products_period ?, ?", date_from, date_to)
    sold_rows = cur.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        tab="reports",
        report_rows=report_rows,
        orders_rows=orders_rows,
        customers_rows=customers_rows,
        sold_rows=sold_rows,
        date_from=date_from,
        date_to=date_to
    )



@auth_bp.route("/admin/reports/excel")
def export_excel():
    gate = _require_admin()
    if gate:
        return gate

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM dbo.vw_report_products_per_category ORDER BY category_name")
    rows = cur.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Категория", "Количество"])

    for r in rows:
        ws.append([r.category_id, r.category_name, r.products_count])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return send_file(buf, as_attachment=True, download_name="report.xlsx")


@auth_bp.route("/admin/reports/word")
def export_word():
    gate = _require_admin()
    if gate:
        return gate

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM dbo.vw_report_products_per_category ORDER BY category_name")
    rows = cur.fetchall()
    conn.close()

    doc = Document()
    doc.add_heading("Отчет по количеству товаров в категориях", level=1)

    t = doc.add_table(rows=1, cols=3)
    t.rows[0].cells[0].text = "ID"
    t.rows[0].cells[1].text = "Категория"
    t.rows[0].cells[2].text = "Количество"

    for r in rows:
        c = t.add_row().cells
        c[0].text = str(r.category_id)
        c[1].text = r.category_name
        c[2].text = str(r.products_count)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    return send_file(buf, as_attachment=True, download_name="report.docx")
@auth_bp.route("/admin/reports/orders")
def report_orders_period():
    gate = _require_admin()
    if gate:
        return gate

    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()

    rows = []
    if date_from and date_to:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("EXEC dbo.sp_report_orders_period_grouped ?, ?", date_from, date_to)
        rows = cur.fetchall()
        conn.close()

    return render_template(
        "admin.html",
        tab="reports",
        report_tab="orders",
        rows=rows,
        date_from=date_from,
        date_to=date_to
    )
@auth_bp.route("/admin/reports/clients")
def report_clients():
    gate = _require_admin()
    if gate:
        return gate

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("EXEC dbo.sp_report_clients_orders")
    rows = cur.fetchall()
    conn.close()

    return render_template(
        "admin.html",
        tab="reports",
        report_tab="clients",
        rows=rows
    )
@auth_bp.route("/admin/reports/products")
def report_products_period():
    gate = _require_admin()
    if gate:
        return gate

    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()

    rows = []
    if date_from and date_to:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("EXEC dbo.sp_report_sold_products_period ?, ?", date_from, date_to)
        rows = cur.fetchall()
        conn.close()

    return render_template(
        "admin.html",
        tab="reports",
        report_tab="products",
        rows=rows,
        date_from=date_from,
        date_to=date_to
    )
@auth_bp.route("/admin/reports/orders/excel")
def export_orders_excel():
    gate = _require_admin()
    if gate:
        return gate

    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    if not date_from or not date_to:
        return redirect("/admin/reports?rtab=orders")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("EXEC dbo.sp_report_orders_period_grouped ?, ?", date_from, date_to)
    rows = cur.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.append(["Статус", "Клиент", "Категория", "Заказов", "Позиций", "Сумма"])

    for r in rows:
        ws.append([r.status, r.client_email, r.category_name, r.orders_count, r.items_count, r.total_sum])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="orders_report.xlsx")
@auth_bp.route("/admin/reports/orders/word")
def export_orders_word():
    gate = _require_admin()
    if gate:
        return gate

    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    if not date_from or not date_to:
        return redirect("/admin/reports?rtab=orders")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("EXEC dbo.sp_report_orders_period_grouped ?, ?", date_from, date_to)
    rows = cur.fetchall()
    conn.close()

    doc = Document()
    doc.add_heading(f"Отчет по заказам за период {date_from} — {date_to}", level=1)

    t = doc.add_table(rows=1, cols=6)
    t.rows[0].cells[0].text = "Статус"
    t.rows[0].cells[1].text = "Клиент"
    t.rows[0].cells[2].text = "Категория"
    t.rows[0].cells[3].text = "Заказов"
    t.rows[0].cells[4].text = "Позиций"
    t.rows[0].cells[5].text = "Сумма"

    for r in rows:
        c = t.add_row().cells
        c[0].text = str(r.status)
        c[1].text = str(r.client_email)
        c[2].text = str(r.category_name)
        c[3].text = str(r.orders_count)
        c[4].text = str(r.items_count)
        c[5].text = str(r.total_sum)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="orders_report.docx")
@auth_bp.route("/admin/reports/clients/excel")
def export_clients_excel():
    gate = _require_admin()
    if gate:
        return gate

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("EXEC dbo.sp_report_clients_orders")
    rows = cur.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.append(["User ID", "Email", "Заказов", "Потрачено", "Первый заказ", "Последний заказ"])

    for r in rows:
        ws.append([r.user_id, r.email, r.orders_count, r.total_spent, r.first_order, r.last_order])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="clients_report.xlsx")
@auth_bp.route("/admin/reports/clients/word")
def export_clients_word():
    gate = _require_admin()
    if gate:
        return gate

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("EXEC dbo.sp_report_clients_orders")
    rows = cur.fetchall()
    conn.close()

    doc = Document()
    doc.add_heading("Отчет по клиентам (история заказов)", level=1)

    t = doc.add_table(rows=1, cols=6)
    t.rows[0].cells[0].text = "User ID"
    t.rows[0].cells[1].text = "Email"
    t.rows[0].cells[2].text = "Заказов"
    t.rows[0].cells[3].text = "Потрачено"
    t.rows[0].cells[4].text = "Первый заказ"
    t.rows[0].cells[5].text = "Последний заказ"

    for r in rows:
        c = t.add_row().cells
        c[0].text = str(r.user_id)
        c[1].text = str(r.email)
        c[2].text = str(r.orders_count)
        c[3].text = str(r.total_spent)
        c[4].text = str(r.first_order) if r.first_order else "-"
        c[5].text = str(r.last_order) if r.last_order else "-"

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="clients_report.docx")
@auth_bp.route("/admin/reports/products/excel")
def export_products_excel():
    gate = _require_admin()
    if gate:
        return gate

    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    if not date_from or not date_to:
        return redirect("/admin/reports?rtab=products")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("EXEC dbo.sp_report_sold_products_period ?, ?", date_from, date_to)
    rows = cur.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Товар", "Продано (шт)", "Выручка"])

    for r in rows:
        ws.append([r.product_id, r.name, r.sold_qty, r.revenue])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="sold_products_report.xlsx")
@auth_bp.route("/admin/reports/products/word")
def export_products_word():
    gate = _require_admin()
    if gate:
        return gate

    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    if not date_from or not date_to:
        return redirect("/admin/reports?rtab=products")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("EXEC dbo.sp_report_sold_products_period ?, ?", date_from, date_to)
    rows = cur.fetchall()
    conn.close()

    doc = Document()
    doc.add_heading(f"Отчет по проданным товарам за период {date_from} — {date_to}", level=1)

    t = doc.add_table(rows=1, cols=4)
    t.rows[0].cells[0].text = "ID"
    t.rows[0].cells[1].text = "Товар"
    t.rows[0].cells[2].text = "Продано (шт)"
    t.rows[0].cells[3].text = "Выручка"

    for r in rows:
        c = t.add_row().cells
        c[0].text = str(r.product_id)
        c[1].text = str(r.name)
        c[2].text = str(r.sold_qty)
        c[3].text = str(r.revenue)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="sold_products_report.docx")

# ---------------- CART (only for logged-in) ----------------

def _cart():
    if "cart" not in session or not isinstance(session.get("cart"), dict):
        session["cart"] = {}
    return session["cart"]

@auth_bp.route("/cart")
def cart():
    gate = _require_login()
    if gate:
        return gate

    cart_map = _cart()  # { "product_id": qty }
    ids = [int(k) for k in cart_map.keys()] if cart_map else []

    items = []
    total = 0

    if ids:
        conn = get_conn()
        cur = conn.cursor()

        placeholders = ",".join(["?"] * len(ids))
        cur.execute(f"SELECT * FROM dbo.vw_products WHERE product_id IN ({placeholders})", *ids)
        rows = cur.fetchall()
        conn.close()

        by_id = {int(r.product_id): r for r in rows}

        for pid_str, qty in cart_map.items():
            pid = int(pid_str)
            p = by_id.get(pid)
            if not p:
                continue

            q = int(qty)
            price = float(p.price) if p.price is not None else 0
            line = price * q
            total += line

            items.append({
                "product_id": pid,
                "name": p.name,
                "price": price,
                "qty": q,
                "line_total": line
            })

    return render_template("cart.html", items=items, total=total)

@auth_bp.route("/cart/add/<int:pid>", methods=["POST"])
def cart_add(pid):
    gate = _require_login()
    if gate:
        return gate

    cart_map = _cart()
    qty = request.form.get("qty", "1").strip()
    try:
        qty_int = max(1, int(qty))
    except:
        qty_int = 1

    cart_map[str(pid)] = int(cart_map.get(str(pid), 0)) + qty_int
    session.modified = True
    return redirect(request.referrer or "/")

@auth_bp.route("/cart/update", methods=["POST"])
def cart_update():
    gate = _require_login()
    if gate:
        return gate

    cart_map = _cart()
    for k, v in request.form.items():
        if not k.startswith("qty_"):
            continue
        pid = k.replace("qty_", "").strip()
        try:
            q = int(v)
        except:
            q = 1

        if q <= 0:
            cart_map.pop(pid, None)
        else:
            cart_map[pid] = q

    session.modified = True
    return redirect("/cart")

@auth_bp.route("/cart/remove/<int:pid>", methods=["POST"])
def cart_remove(pid):
    gate = _require_login()
    if gate:
        return gate

    cart_map = _cart()
    cart_map.pop(str(pid), None)
    session.modified = True
    return redirect("/cart")

@auth_bp.route("/cart/clear", methods=["POST"])
def cart_clear():
    gate = _require_login()
    if gate:
        return gate

    session["cart"] = {}
    session.modified = True
    return redirect("/cart")
@auth_bp.route("/cart/checkout", methods=["POST"])
def cart_checkout():
    gate = _require_login()
    if gate:
        return gate

    cart = session.get("cart", {})
    if not cart:
        return redirect("/cart")

    user_id = session["user_id"]

    conn = get_conn()
    cur = conn.cursor()

    # товары из корзины
    ids = [int(k) for k in cart.keys()]
    placeholders = ",".join(["?"] * len(ids))

    cur.execute(f"""
        SELECT product_id, price
        FROM dbo.vw_products
        WHERE product_id IN ({placeholders})
    """, *ids)

    rows = cur.fetchall()

    price_map = {int(r.product_id): float(r.price) for r in rows}

    total = 0.0
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        q = int(qty)
        total += price_map.get(pid, 0.0) * q

    # 1) создаём заказ в orders
    cur.execute("EXEC dbo.sp_place_order ?, ?", user_id, total)
    order_id = cur.fetchone()[0]

    # 2) добавляем позиции в order_items
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        q = int(qty)
        price = price_map.get(pid, 0.0)

        cur.execute("EXEC dbo.sp_add_order_item ?, ?, ?, ?", order_id, pid, q, price)

    conn.commit()
    conn.close()

    session["cart"] = {}
    session.modified = True

    return redirect("/cabinet")
from flask import jsonify

@auth_bp.route("/compat")
def compat_page():
    gate = _require_login()
    if gate:
        return gate
    return render_template("compat.html")

@auth_bp.route("/api/search/products")
def api_search_products():
    gate = _require_login()
    if gate:
        return gate

    q = request.args.get("q", "").strip()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("EXEC dbo.sp_search_products ?, ?", q, "product")
    rows = cur.fetchall()
    conn.close()

    return jsonify([{"id": int(r.product_id), "name": r.name} for r in rows])

@auth_bp.route("/api/search/parts")
def api_search_parts():
    gate = _require_login()
    if gate:
        return gate

    q = request.args.get("q", "").strip()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("EXEC dbo.sp_search_products ?, ?", q, "part")
    rows = cur.fetchall()
    conn.close()

    return jsonify([{"id": int(r.product_id), "name": r.name} for r in rows])

@auth_bp.route("/api/compat/matrix", methods=["POST"])
def api_compat_matrix():
    gate = _require_login()
    if gate:
        return gate

    product_id = request.json.get("product_id")
    part_id = request.json.get("part_id")
    if not product_id or not part_id:
        return jsonify({"ok": False, "error": "product_id and part_id required"}), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("EXEC dbo.sp_part_compat_matrix ?", int(part_id))
    rows = cur.fetchall()
    conn.close()

    # разделяем на compatible / incompatible
    compatible = []
    incompatible = []
    part_name = None

    for r in rows:
        part_name = r.part_name
        item = {
            "id": int(r.product_id),
            "name": r.product_name,
            "brand": r.brand_name,
            "img": f"/product_image/{int(r.product_id)}",
        }
        if int(r.is_compatible) == 1:
            compatible.append(item)
        else:
            incompatible.append(item)

    # отдельно: подходит ли выбранная запчасть к выбранному товару
    selected_ok = any(x["id"] == int(product_id) for x in compatible)

    return jsonify({
        "ok": True,
        "selected_ok": selected_ok,
        "part_name": part_name,
        "compatible": compatible,
        "incompatible": incompatible
    })
