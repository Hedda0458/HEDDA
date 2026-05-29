from app.security.audit import log_action
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_user,
    logout_user,
    login_required
)

from app.models.user import User


bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


# =========================
# LOGIN
# =========================
@bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username"
        )

        password = request.form.get(
            "password"
        )

        user = User.query.filter_by(
            username=username
        ).first()

        if user and user.check_password(
            password
        ):

            login_user(user)
            log_action(
            "Connexion"
            )
            return redirect(
                url_for(
                    "agents.list_agents"
                )
            )

        flash(
            "Identifiants invalides",
            "danger"
        )

    return render_template(
        "auth/login.html"
    )


# =========================
# LOGOUT
# =========================
@bp.route("/logout")
@login_required
def logout():

    log_action(
    "Déconnexion"
    )
    logout_user()

logout_user()
    return redirect(
        url_for("auth.login")
    )