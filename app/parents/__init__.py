from flask import Blueprint

parents_bp = Blueprint("parents", __name__, template_folder="../templates/parents")

from app.parents import routes
