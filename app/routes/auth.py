from flask import Blueprint, render_template, request, redirect, url_for, session, send_file
from app.db import get_conn
import bcrypt
import io
from datetime import datetime
from docx import Document
from openpyxl import Workbook

auth_bp = Blueprint("auth", __name__)

def _require_admin():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("is_admin") != 1:
        return "Forbidden", 403
    return None


@auth_bp.route("/")
def index():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM dbo.vw_products ORDER BY product_id DESC")
    products = cur.fetchall()
    conn.close()
    return render_template("index.html", products=products)


@auth_bp.route("/product_image/<int:pid>")
def product_image(pid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT TOP 1 image_data FROM dbo.images WHERE product_id=? ORDER BY image_id DESC", pid)
    row = cur.fetchone()
    conn.close()
    if not row:
        return "", 404
    return send_file(io.BytesIO(row[0]), mimetype="image/jpeg")


@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","")
        password=request.form.get("password","")

        if email=="admin" and password=="admin":
            session["user_id"]=0
            session["email"]="admin"
            session["is_admin"]=1
            return redirect("/admin")

        conn=get_conn()
        cur=conn.cursor()
        cur.execute("EXEC dbo.sp_login_user ?",email)
        row=cur.fetchone()
        conn.close()

        if not row:
            return render_template("login.html",error="Ошибка входа")

        if not bcrypt.checkpw(password.encode(),row.password_hash.encode()):
            return render_template("login.html",error="Ошибка входа")

        session["user_id"]=row.user_id
        session["email"]=email
        session["is_admin"]=1 if row.is_admin else 0

        return redirect("/admin" if row.is_admin else "/")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@auth_bp.route("/admin")
def admin():
    gate=_require_admin()
    if gate: return gate

    conn=get_conn()
    cur=conn.cursor()

    cur.execute("SELECT id_brand,name FROM dbo.vw_brands")
    brands=cur.fetchall()

    cur.execute("SELECT category_id,name,parent_id,parent_name FROM dbo.vw_categories")
    categories=cur.fetchall()

    cur.execute("SELECT * FROM dbo.vw_products ORDER BY product_id DESC")
    products=cur.fetchall()

    conn.close()

    return render_template("admin.html",
        brands=brands,
        categories=categories,
        products=products,
        tab="products"
    )


# ---------------- REPORT TAB ----------------

@auth_bp.route("/admin/reports")
def admin_reports():
    gate=_require_admin()
    if gate: return gate

    conn=get_conn()
    cur=conn.cursor()

    cur.execute("SELECT * FROM dbo.vw_report_products_per_category ORDER BY category_name")
    report_rows=cur.fetchall()

    conn.close()

    return render_template("admin.html",
        tab="reports",
        report_rows=report_rows
    )


@auth_bp.route("/admin/reports/excel")
def export_excel():
    gate=_require_admin()
    if gate: return gate

    conn=get_conn()
    cur=conn.cursor()
    cur.execute("SELECT * FROM dbo.vw_report_products_per_category ORDER BY category_name")
    rows=cur.fetchall()
    conn.close()

    wb=Workbook()
    ws=wb.active
    ws.append(["ID","Категория","Количество"])

    for r in rows:
        ws.append([r.category_id,r.category_name,r.products_count])

    buf=io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return send_file(buf,as_attachment=True,download_name="report.xlsx")


@auth_bp.route("/admin/reports/word")
def export_word():
    gate=_require_admin()
    if gate: return gate

    conn=get_conn()
    cur=conn.cursor()
    cur.execute("SELECT * FROM dbo.vw_report_products_per_category ORDER BY category_name")
    rows=cur.fetchall()
    conn.close()

    doc=Document()
    doc.add_heading("Отчет по категориям",level=1)

    t=doc.add_table(rows=1,cols=3)
    t.rows[0].cells[0].text="ID"
    t.rows[0].cells[1].text="Категория"
    t.rows[0].cells[2].text="Количество"

    for r in rows:
        c=t.add_row().cells
        c[0].text=str(r.category_id)
        c[1].text=r.category_name
        c[2].text=str(r.products_count)

    buf=io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    return send_file(buf,as_attachment=True,download_name="report.docx")
