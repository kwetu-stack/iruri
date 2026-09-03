from flask import Blueprint

agents = Blueprint("agents", __name__, url_prefix="/agents")

from app.agents.models import Agent
from app.agents import routes
