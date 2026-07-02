from app import app, db, User

with app.app_context():
    user = User.query.first()

    if user:
        user.role = 'Inspector'
        db.session.commit()
        print(f"Успех! Потребителят '{user.username}' вече е Инспектор!")
    else:
        print("Грешка: Няма намерени потребители в базата данни.")