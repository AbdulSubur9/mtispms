from flask import Blueprint

fee_structures_bp = Blueprint("fee_structures", __name__, template_folder="../templates/fee_structures")

from app.fee_structures import routes
