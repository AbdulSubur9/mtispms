from flask import Blueprint

parent_management_bp = Blueprint(
    "parent_management", __name__, template_folder="../templates/parent_management"
)

from app.parent_management import routes
