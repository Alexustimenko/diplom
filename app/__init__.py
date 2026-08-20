import os

from dotenv import load_dotenv
from flask import Flask, render_template

from app.routes.auth import auth_bp
from app.routes.site import site_bp
from app.services.catalog import load_navigation, product_path, row_value
from app.site_data import STATIC_PAGES

def create_app():
    load_dotenv()
    app = Flask(__name__)
    # Preserve the previous fallback so existing signed sessions remain valid;
    # deployments can and should override it with SECRET_KEY.
    app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

    app.register_blueprint(site_bp)
    app.register_blueprint(auth_bp)

    @app.context_processor
    def public_navigation():
        categories, brands = load_navigation()
        return {"public_categories": categories, "public_brands": brands}

    app.jinja_env.globals.update(
        static_pages=STATIC_PAGES,
        product_path=product_path,
        row_value=row_value,
    )

    @app.errorhandler(404)
    def not_found(error):
        return render_template(
            "site/404.html",
            page_title="Страница не найдена",
            meta_description="Запрошенная страница не найдена.",
            canonical_url=None,
            breadcrumbs=[],
        ), 404

    return app
