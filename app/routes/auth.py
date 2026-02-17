# app/routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, send_file
from app.db import get_conn
import bcrypt
import io

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def index():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM dbo.vw_products ORDER BY product_id DESC")
    products = cur.fetchall()
    conn.close()
    return render_template("index.html", products=products)


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

        if email.lower() == "admin" and password == "admin":
            session["user_id"] = 0
            session["email"] = "admin"
            session["customer_type"] = "ur"
            session["is_admin"] = 1
            return redirect(url_for("auth.admin"))

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("EXEC dbo.sp_login_user ?", email)
        row = cur.fetchone()
        conn.close()

        if row is None:
            return render_template("login.html", error="Неверный email или пароль")

        user_id = int(row.user_id)
        password_hash = row.password_hash
        customer_type = row.customer_type
        is_admin = bool(row.is_admin)

        if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
            return render_template("login.html", error="Неверный email или пароль")

        session["user_id"] = user_id
        session["email"] = email
        session["customer_type"] = customer_type
        session["is_admin"] = 1 if is_admin else 0

        if is_admin:
            return redirect(url_for("auth.admin"))
        return redirect(url_for("auth.cabinet"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/cabinet")
def cabinet():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template(
        "cabinet.html",
        email=session.get("email"),
        customer_type=session.get("customer_type"),
    )


@auth_bp.route("/product_image/<int:pid>")
def product_image(pid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT TOP 1 image_data FROM dbo.images WHERE product_id = ? ORDER BY image_id DESC", pid)
    row = cur.fetchone()
    conn.close()

    if not row:
        return "", 404

    return send_file(io.BytesIO(row[0]), mimetype="image/jpeg")


@auth_bp.route("/admin", methods=["GET", "POST"])
def admin():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("is_admin") != 1:
        return "Forbidden", 403

    error = None
    success = None

    conn = get_conn()
    cur = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add_brand":
            brand_name = request.form.get("brand_name", "").strip()
            if not brand_name:
                error = "Название бренда не может быть пустым"
            else:
                cur.execute("EXEC dbo.sp_add_brand ?", brand_name)
                res = cur.fetchone()[0]
                conn.commit()
                if res == -1:
                    error = "Такой бренд уже существует"
                else:
                    success = "Бренд добавлен"

        elif action == "edit_brand":
            brand_id = request.form.get("brand_id", "").strip()
            brand_name = request.form.get("brand_name", "").strip()
            if not brand_id.isdigit() or not brand_name:
                error = "Некорректные данные для редактирования бренда"
            else:
                cur.execute("EXEC dbo.sp_update_brand ?, ?", int(brand_id), brand_name)
                res = cur.fetchone()[0]
                conn.commit()
                if res == -1:
                    error = "Такое название уже занято другим брендом"
                elif res == -2:
                    error = "Бренд не найден"
                else:
                    success = "Бренд обновлён"

        elif action == "delete_brand":
            brand_id = request.form.get("brand_id", "").strip()
            if not brand_id.isdigit():
                error = "Некорректный id бренда"
            else:
                cur.execute("EXEC dbo.sp_delete_brand ?", int(brand_id))
                res = cur.fetchone()[0]
                conn.commit()
                if res == -2:
                    error = "Бренд не найден"
                elif res == -3:
                    error = "Нельзя удалить: есть товары с этим брендом"
                else:
                    success = "Бренд удалён"

        elif action == "add_category":
            name = request.form.get("category_name", "").strip()
            parent_raw = request.form.get("parent_id", "").strip()
            parent_id = None if parent_raw in ("", "null", "None") else int(parent_raw)

            if not name:
                error = "Название категории не может быть пустым"
            else:
                cur.execute("EXEC dbo.sp_add_category ?, ?", name, parent_id)
                res = cur.fetchone()[0]
                conn.commit()
                if res == -1:
                    error = "Категория с таким названием уже существует"
                elif res == -2:
                    error = "Родительская категория не найдена"
                else:
                    success = "Категория добавлена"

        elif action == "edit_category":
            cat_id = request.form.get("category_id", "").strip()
            name = request.form.get("category_name", "").strip()
            parent_raw = request.form.get("parent_id", "").strip()
            parent_id = None if parent_raw in ("", "null", "None") else int(parent_raw)

            if (not cat_id.isdigit()) or (not name):
                error = "Некорректные данные для редактирования категории"
            else:
                cur.execute("EXEC dbo.sp_update_category ?, ?, ?", int(cat_id), name, parent_id)
                res = cur.fetchone()[0]
                conn.commit()
                if res == -1:
                    error = "Категория с таким названием уже существует"
                elif res == -2:
                    error = "Родительская категория не найдена"
                elif res == -3:
                    error = "Категория не найдена"
                elif res == -4:
                    error = "Категория не может быть родителем самой себя"
                else:
                    success = "Категория обновлена"

        elif action == "delete_category":
            cat_id = request.form.get("category_id", "").strip()
            if not cat_id.isdigit():
                error = "Некорректный id категории"
            else:
                cur.execute("EXEC dbo.sp_delete_category ?", int(cat_id))
                res = cur.fetchone()[0]
                conn.commit()
                if res == -2:
                    error = "Категория не найдена"
                elif res == -3:
                    error = "Нельзя удалить: есть подкатегории"
                elif res == -4:
                    error = "Нельзя удалить: есть товары в этой категории"
                else:
                    success = "Категория удалена"

        elif action == "add_product":
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            price = request.form.get("price", "").strip()
            old_price = request.form.get("old_price", "").strip()
            stock = request.form.get("stock", "").strip()
            category_id = request.form.get("category_id", "").strip()
            brand_id = request.form.get("brand_id", "").strip()

            if not name or not price or not stock:
                error = "Заполни название, цену и количество"
            else:
                cat_val = None if category_id in ("", "null", "None") else int(category_id)
                brand_val = None if brand_id in ("", "null", "None") else int(brand_id)
                desc_val = None if description == "" else description
                old_price_val = None if old_price == "" else old_price

                cur.execute(
                    "EXEC dbo.sp_add_product ?, ?, ?, ?, ?, ?, ?",
                    name, desc_val, price, old_price_val, int(stock), cat_val, brand_val
                )
                pid = cur.fetchone()[0]

                files = request.files.getlist("images")
                for f in files:
                    if f and f.filename:
                        cur.execute("EXEC dbo.sp_add_product_image ?, ?", int(pid), f.read())

                conn.commit()
                success = "Товар добавлен"

        elif action == "edit_product":
            product_id = request.form.get("product_id", "").strip()
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            price = request.form.get("price", "").strip()
            old_price = request.form.get("old_price", "").strip()
            stock = request.form.get("stock", "").strip()
            category_id = request.form.get("category_id", "").strip()
            brand_id = request.form.get("brand_id", "").strip()
            replace_images = (request.form.get("replace_images") == "1")

            if (not product_id.isdigit()) or (not name) or (not price) or (not stock):
                error = "Некорректные данные для редактирования товара"
            else:
                cat_val = None if category_id in ("", "null", "None") else int(category_id)
                brand_val = None if brand_id in ("", "null", "None") else int(brand_id)
                desc_val = None if description == "" else description
                old_price_val = None if old_price == "" else old_price

                cur.execute(
                    "EXEC dbo.sp_update_product ?, ?, ?, ?, ?, ?, ?, ?",
                    int(product_id), name, desc_val, price, old_price_val, int(stock), cat_val, brand_val
                )
                res = cur.fetchone()[0]

                if res == -2:
                    error = "Товар не найден"
                else:
                    files = request.files.getlist("images")
                    has_new = any(f and f.filename for f in files)

                    if has_new and replace_images:
                        cur.execute("EXEC dbo.sp_delete_product_images ?", int(product_id))
                        cur.fetchone()

                    if has_new:
                        for f in files:
                            if f and f.filename:
                                cur.execute("EXEC dbo.sp_add_product_image ?, ?", int(product_id), f.read())

                    conn.commit()
                    success = "Товар обновлён"

        elif action == "delete_product":
            product_id = request.form.get("product_id", "").strip()
            if not product_id.isdigit():
                error = "Некорректный id товара"
            else:
                cur.execute("EXEC dbo.sp_delete_product ?", int(product_id))
                res = cur.fetchone()[0]
                conn.commit()
                if res == -2:
                    error = "Товар не найден"
                else:
                    success = "Товар удалён"

    cur.execute("SELECT id_brand, name FROM dbo.vw_brands ORDER BY id_brand DESC")
    brands = cur.fetchall()

    cur.execute("SELECT category_id, name, parent_id, parent_name FROM dbo.vw_categories ORDER BY category_id DESC")
    categories = cur.fetchall()

    cur.execute("SELECT * FROM dbo.vw_products ORDER BY product_id DESC")
    products = cur.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        email=session.get("email"),
        brands=brands,
        categories=categories,
        products=products,
        error=error,
        success=success
    )
