from flask import Blueprint

academics_bp = Blueprint("academics", __name__, template_folder="../templates/academics")

from app.academics import routes
