from app.security.audit import log_action
from app.models.audit_log import AuditLog
from sqlalchemy import or_
from datetime import (
    date,
    datetime
)
from app.security.rbac import role_required
import csv

from io import TextIOWrapper

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required
)

from app.extensions import db

from app.models.agent import Agent


bp = Blueprint(
    "agents",
    __name__,
    url_prefix="/agents"
)


# =========================
# AGE
# =========================
def compute_age(agent):

    if not agent.date_naissance:
        return 0

    today = date.today()

    return (
        today.year
        - agent.date_naissance.year
        - (
            (
                today.month,
                today.day
            )
            <
            (
                agent.date_naissance.month,
                agent.date_naissance.day
            )
        )
    )


# =========================
# ANCIENNETE
# =========================
def compute_anciennete(agent):

    if not agent.date_entree:
        return 0

    today = date.today()

    return (
        today.year
        - agent.date_entree.year
        - (
            (
                today.month,
                today.day
            )
            <
            (
                agent.date_entree.month,
                agent.date_entree.day
            )
        )
    )


# =========================
# IA SCORE
# =========================
def compute_score(agent):

    score = 0

    age = compute_age(agent)

    anc = compute_anciennete(agent)

    score += min(age * 0.5, 20)

    score += min(anc * 2, 30)

    if anc > 5:
        score += 15

    if not agent.email:
        score -= 10

    if not agent.telephone:
        score -= 10

    return max(
        0,
        min(100, round(score))
    )


# =========================
# SEGMENTATION
# =========================
def segment(score):

    if score < 40:
        return "Risque"

    elif score < 70:
        return "Surveiller"

    return "Stable"

# =========================
# LISTE AGENTS
# =========================
@bp.route("/")
@login_required
def list_agents():

    # =========================
    # PARAMETRES
    # =========================
    search = request.args.get(
        "search",
        ""
    )

    service_filter = request.args.get(
        "service",
        ""
    )

    direction_filter = request.args.get(
        "direction",
        ""
    )

    sexe_filter = request.args.get(
        "sexe",
        ""
    )

    segment_filter = request.args.get(
        "segment",
        ""
    )

    age_range = request.args.get(
        "age_range",
        ""
    )

    anciennete_range = request.args.get(
        "anciennete_range",
        ""
    )

    sort = request.args.get(
        "sort",
        "nom"
    )

    page = request.args.get(
        "page",
        1,
        type=int
    )

    # =========================
    # QUERY
    # =========================
    query = Agent.query

    # =========================
    # RECHERCHE
    # =========================
    if search:

        query = query.filter(

            or_(

                Agent.nom.ilike(
                    f"%{search}%"
                ),

                Agent.prenom.ilike(
                    f"%{search}%"
                ),

                Agent.email.ilike(
                    f"%{search}%"
                ),

                Agent.service.ilike(
                    f"%{search}%"
                )
            )
        )

    # =========================
    # FILTRES SQL
    # =========================
    if service_filter:

        query = query.filter_by(
            service=service_filter
        )

    if direction_filter:

        query = query.filter_by(
            direction=direction_filter
        )

    if sexe_filter:

        query = query.filter_by(
            sexe=sexe_filter
        )

    # =========================
    # TRI
    # =========================
    if sort == "nom":

        query = query.order_by(
            Agent.nom.asc()
        )

    elif sort == "service":

        query = query.order_by(
            Agent.service.asc()
        )

    elif sort == "direction":

        query = query.order_by(
            Agent.direction.asc()
        )

    # =========================
    # PAGINATION
    # =========================
    pagination = query.paginate(

        page=page,

        per_page=15
    )

    agents = pagination.items

    data = []

    # =========================
    # FILTRES METIERS
    # =========================
    for agent in agents:

        score = compute_score(agent)

        seg = segment(score)

        age = compute_age(agent)

        anciennete = compute_anciennete(agent)

        # =========================
        # FILTRE SEGMENT
        # =========================
        if (
            segment_filter
            and seg != segment_filter
        ):
            continue

        # =========================
        # FILTRE AGE
        # =========================
        if age_range == "20-29":

            if not (20 <= age <= 29):
                continue

        elif age_range == "30-39":

            if not (30 <= age <= 39):
                continue

        elif age_range == "40-49":

            if not (40 <= age <= 49):
                continue

        elif age_range == "50+":

            if age < 50:
                continue

        # =========================
        # FILTRE ANCIENNETE
        # =========================
        if anciennete_range == "0-5":

            if not (
                0 <= anciennete <= 5
            ):
                continue

        elif anciennete_range == "6-10":

            if not (
                6 <= anciennete <= 10
            ):
                continue

        elif anciennete_range == "10+":

            if anciennete < 10:
                continue

        data.append({

            "agent": agent,

            "age": age,

            "anciennete": anciennete,

            "score": score,

            "segment": seg
        })

    # =========================
    # LISTES FILTRES
    # =========================
    services = sorted({

        a.service
        for a in Agent.query.all()

        if a.service
    })

    directions = sorted({

        a.direction
        for a in Agent.query.all()

        if a.direction
    })

    return render_template(

        "agents/list.html",

        data=data,

        pagination=pagination,

        services=services,

        directions=directions
    )


# =========================
# DASHBOARD
# =========================
@bp.route("/dashboard")
@login_required
def dashboard():

    agents = Agent.query.all()

    total = len(agents)

    services = sorted({

        a.service
        for a in agents

        if a.service
    })

    directions = sorted({

        a.direction
        for a in agents

        if a.direction
    })

    segments = {

        "Risque": 0,
        "Surveiller": 0,
        "Stable": 0
    }

    scores = []

    hommes = 0
    femmes = 0

    tranches = {

        "20-29": 0,

        "30-39": 0,

        "40-49": 0,

        "50-59": 0,

        "60+": 0
    }

    services_count = {}

    directions_count = {}

    for agent in agents:

        score = compute_score(agent)

        scores.append(score)

        seg = segment(score)

        segments[seg] += 1

        if agent.sexe == "Homme":
            hommes += 1

        elif agent.sexe == "Femme":
            femmes += 1

        age = compute_age(agent)

        if 20 <= age <= 29:

            tranches["20-29"] += 1

        elif 30 <= age <= 39:

            tranches["30-39"] += 1

        elif 40 <= age <= 49:

            tranches["40-49"] += 1

        elif 50 <= age <= 59:

            tranches["50-59"] += 1

        elif age >= 60:

            tranches["60+"] += 1

        if agent.service:

            services_count[
                agent.service
            ] = (

                services_count.get(
                    agent.service,
                    0
                ) + 1
            )

        if agent.direction:

            directions_count[
                agent.direction
            ] = (

                directions_count.get(
                    agent.direction,
                    0
                ) + 1
            )

    avg_score = (

        round(
            sum(scores) / len(scores),
            1
        )

        if scores else 0
    )

    return render_template(

        "agents/dashboard.html",

        total=total,

        avg_score=avg_score,

        nb_services=len(services),

        nb_directions=len(directions),

        segments=segments,

        hommes=hommes,

        femmes=femmes,

        tranches=tranches,

        services_count=services_count,

        directions_count=directions_count
    )


# =========================
# ADD AGENT
# =========================
@bp.route("/add", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def add_agent():

    if request.method == "POST":

        agent = Agent(

            nom=request.form.get("nom"),

            prenom=request.form.get("prenom"),

            email=request.form.get("email"),

            telephone=request.form.get(
                "telephone"
            ),

            sexe=request.form.get("sexe"),

            service=request.form.get(
                "service"
            ),

            unite_service=request.form.get(
                "unite_service"
            ),

            direction=request.form.get(
                "direction"
            ),

            date_naissance=datetime.strptime(
                request.form.get(
                    "date_naissance"
                ),
                "%Y-%m-%d"
            ).date()

            if request.form.get(
                "date_naissance"
            )
            else None,

            date_entree=datetime.strptime(
                request.form.get(
                    "date_entree"
                ),
                "%Y-%m-%d"
            ).date()

            if request.form.get(
                "date_entree"
            )
            else None
        )

        db.session.add(agent)

        db.session.commit()
        log_action(
        f"Ajout agent {agent.nom}"
)

        flash(
            "Agent ajouté",
            "success"
        )

        return redirect(
            url_for("agents.list_agents")
        )

    return render_template(
        "agents/add.html"
    )
# =========================
# EDIT AGENT
# =========================
@bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def edit_agent(id):

    agent = Agent.query.get_or_404(id)

    if request.method == "POST":

        agent.nom = request.form.get("nom")

        agent.prenom = request.form.get("prenom")

        agent.email = request.form.get("email")

        agent.telephone = request.form.get(
            "telephone"
        )

        agent.sexe = request.form.get(
            "sexe"
        )

        agent.service = request.form.get(
            "service"
        )

        agent.unite_service = request.form.get(
            "unite_service"
        )

        agent.direction = request.form.get(
            "direction"
        )

        db.session.commit()
        log_action(
        f"Modification agent {agent.nom}"
        )

        flash(
            "Agent modifié",
            "success"
        )

        return redirect(
            url_for("agents.list_agents")
        )

    return render_template(
        "agents/add.html",
        agent=agent
    )
# =========================
# DELETE AGENT
# =========================
@bp.route("/delete/<int:id>")
@login_required
@role_required("admin")
def delete_agent(id):
    agent = Agent.query.get_or_404(id)

    nom = agent.nom

    db.session.delete(agent)

    db.session.commit()

    log_action(
        f"Suppression agent {nom}"
    )
    flash(
        "Agent supprimé",
        "success"
    )

    return redirect(
        url_for("agents.list_agents")
    )
# =========================
# IMPORT CSV
# =========================
@bp.route("/import", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def import_agents():

    if request.method == "POST":

        file = request.files.get("file")

        if not file:

            flash(
                "Aucun fichier",
                "danger"
            )

            return redirect(request.url)

        try:

            stream = TextIOWrapper(
                file,
                encoding="utf-8"
            )

            reader = csv.DictReader(stream)

            imported = 0
            skipped = 0

            for row in reader:

                email = row.get("email")

                existing = Agent.query.filter_by(
                    email=email
                ).first()

                if existing:

                    skipped += 1
                    continue

                agent = Agent(

                    nom=row.get("nom"),

                    prenom=row.get("prenom"),

                    email=email,

                    telephone=row.get(
                        "telephone"
                    ),

                    sexe=row.get("sexe"),

                    service=row.get("service"),

                    unite_service=row.get(
                        "unite_service"
                    ),

                    direction=row.get(
                        "direction"
                    ),

                    date_naissance=datetime.strptime(
                        row.get("date_naissance"),
                        "%Y-%m-%d"
                    ).date()

                    if row.get(
                        "date_naissance"
                    )
                    else None,

                    date_entree=datetime.strptime(
                        row.get("date_entree"),
                        "%Y-%m-%d"
                    ).date()

                    if row.get(
                        "date_entree"
                    )
                    else None
                )

                db.session.add(agent)

                imported += 1
    
            db.session.commit()
            log_action(
            f"Import CSV {imported} agents"
            )
            flash(
                f"{imported} agents importés / "
                f"{skipped} doublons ignorés",
                "success"
            )

            return redirect(
                url_for("agents.list_agents")
            )

        except Exception as e:

            flash(
                f"Erreur import : {e}",
                "danger"
            )

            return redirect(request.url)

    return render_template(
        "agents/import.html"
    )
# =========================
# AUDIT LOGS
# =========================
@bp.route("/audit")
@login_required
@role_required("admin")
def audit_logs():

    logs = AuditLog.query.order_by(
        AuditLog.created_at.desc()
    ).limit(200).all()

    return render_template(
        "agents/audit.html",
        logs=logs
    )