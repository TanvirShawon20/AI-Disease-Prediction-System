
from urllib.parse import urljoin, urlsplit

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.auth import auth_bp
from app.extensions import db
from app.models import User
from app.auth.forms import RegistrationForm, LoginForm


def is_safe_redirect(target):
    if not target:
        return False

    host_url = urlsplit(request.host_url)
    redirect_url = urlsplit(urljoin(request.host_url, target))

    return (
        redirect_url.scheme in {"http", "https"}
        and redirect_url.netloc == host_url.netloc
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        existing_user = db.session.scalar(
            db.select(User).where(
                or_(
                    db.func.lower(User.username) == username.lower(),
                    db.func.lower(User.email) == email,
                )
            )
        )

        if existing_user:
            flash(
                "That username or email is already registered.",
                "danger",
            )
            return render_template(
                "auth/register.html",
                form=form,
            )

        user = User(username=username, email=email)
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                "That username or email is already registered.",
                "danger",
            )
            return render_template(
                "auth/register.html",
                form=form,
            )

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        user = db.session.scalar(
            db.select(User).where(
                db.func.lower(User.email) == email
            )
        )

        if user and user.is_active and user.check_password(
            form.password.data
        ):
            login_user(user)

            next_url = request.args.get("next")
            if is_safe_redirect(next_url):
                return redirect(next_url)

            return redirect(url_for("auth.dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "auth/dashboard.html",
        username=current_user.username,
    )