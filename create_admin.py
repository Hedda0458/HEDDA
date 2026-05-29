from app import create_app

from app.extensions import db

from app.models.user import User


app = create_app()


with app.app_context():

    users = [

        {
            "username": "admin",
            "password": "admin123",
            "role": "admin"
        },

        {
            "username": "manager",
            "password": "manager123",
            "role": "manager"
        },

        {
            "username": "user",
            "password": "user123",
            "role": "user"
        }
    ]

    for u in users:

        existing = User.query.filter_by(
            username=u["username"]
        ).first()

        if existing:
            continue

        user = User(

            username=u["username"],

            role=u["role"]
        )

        user.set_password(
            u["password"]
        )

        db.session.add(user)

    db.session.commit()

    print("✅ UTILISATEURS CRÉÉS")