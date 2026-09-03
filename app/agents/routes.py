import os
import uuid

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.agents import agents
from app.agents.models import Agent
from app.extensions import db

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


def _upload_folder():
    folder = os.path.join(current_app.root_path, "static", "uploads", "agents")
    os.makedirs(folder, exist_ok=True)
    return folder


def _valid_image(uploaded_file):
    filename = secure_filename(uploaded_file.filename or "")
    return (
        filename
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def _within_size(uploaded_file):
    uploaded_file.stream.seek(0, os.SEEK_END)
    size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    return size <= MAX_IMAGE_SIZE


def _save_photo(uploaded_file):
    extension = secure_filename(uploaded_file.filename).rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"
    uploaded_file.save(os.path.join(_upload_folder(), filename))
    return filename


def _remove_photo(filename):
    if filename:
        path = os.path.join(_upload_folder(), filename)
        if os.path.isfile(path):
            os.remove(path)


def _agent_values(form):
    values = {
        field: form.get(field, "").strip() or None
        for field in (
            "first_name",
            "last_name",
            "gender",
            "phone",
            "email",
            "national_id",
            "license_number",
            "kra_pin",
            "county",
            "town",
            "address",
            "bio",
        )
    }
    try:
        values["years_experience"] = (
            int(form.get("years_experience", ""))
            if form.get("years_experience", "").strip()
            else None
        )
        values["commission_rate"] = (
            float(form.get("commission_rate", ""))
            if form.get("commission_rate", "").strip()
            else None
        )
    except ValueError:
        raise ValueError(
            "Years of experience must be a whole number and commission rate must be numeric."
        )
    values["is_active"] = form.get("is_active") == "on"
    return values


@agents.route("/")
@login_required
def index():
    agent_list = Agent.query.order_by(Agent.created_at.desc()).all()
    return render_template("agents/index.html", agents=agent_list)


@agents.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        phone = request.form.get("phone", "").strip()
        if not first_name or not last_name or not phone:
            flash("First name, last name, and phone are required.", "danger")
            return render_template("agents/create.html")
        try:
            values = _agent_values(request.form)
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("agents/create.html")
        uploaded_file = request.files.get("profile_photo")
        if uploaded_file and uploaded_file.filename:
            if not _valid_image(uploaded_file):
                flash("Only JPG, JPEG, PNG, and WEBP images are allowed.", "danger")
                return render_template("agents/create.html")
            if not _within_size(uploaded_file):
                flash("The profile photo must be 10 MB or smaller.", "danger")
                return render_template("agents/create.html")
            values["profile_photo"] = _save_photo(uploaded_file)
        agent = Agent(agent_number="TEMP", **values)
        db.session.add(agent)
        db.session.flush()
        agent.agent_number = f"AGT-2026-{agent.id:06d}"
        db.session.commit()
        flash("Agent added successfully.", "success")
        return redirect(url_for("agents.index"))
    return render_template("agents/create.html")


@agents.route("/<int:id>")
@login_required
def details(id):
    return render_template("agents/details.html", agent=Agent.query.get_or_404(id))


@agents.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    agent = Agent.query.get_or_404(id)
    if request.method == "POST":
        if (
            not request.form.get("first_name", "").strip()
            or not request.form.get("last_name", "").strip()
            or not request.form.get("phone", "").strip()
        ):
            flash("First name, last name, and phone are required.", "danger")
            return render_template("agents/edit.html", agent=agent)
        try:
            values = _agent_values(request.form)
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("agents/edit.html", agent=agent)
        uploaded_file = request.files.get("profile_photo")
        old_photo = agent.profile_photo
        if uploaded_file and uploaded_file.filename:
            if not _valid_image(uploaded_file):
                flash("Only JPG, JPEG, PNG, and WEBP images are allowed.", "danger")
                return render_template("agents/edit.html", agent=agent)
            if not _within_size(uploaded_file):
                flash("The profile photo must be 10 MB or smaller.", "danger")
                return render_template("agents/edit.html", agent=agent)
            values["profile_photo"] = _save_photo(uploaded_file)
        for field, value in values.items():
            setattr(agent, field, value)
        db.session.commit()
        if uploaded_file and uploaded_file.filename:
            _remove_photo(old_photo)
        flash("Agent updated successfully.", "success")
        return redirect(url_for("agents.details", id=agent.id))
    return render_template("agents/edit.html", agent=agent)


@agents.route("/<int:id>/delete", methods=["GET", "POST"])
@login_required
def delete(id):
    agent = Agent.query.get_or_404(id)
    if request.method == "POST":
        photo = agent.profile_photo
        db.session.delete(agent)
        db.session.commit()
        _remove_photo(photo)
        flash("Agent deleted successfully.", "success")
        return redirect(url_for("agents.index"))
    return render_template("agents/delete.html", agent=agent)
