from app import app, db, User

with app.app_context():
    # Взимаме първия регистриран потребител (т.е. твоя акаунт)
    user = User.query.first()

    if user:
        user.role = 'Inspector'
        db.session.commit()
        print(f"Успех! Потребителят '{user.username}' вече е Инспектор!")
    else:
        print("Грешка: Няма намерени потребители в базата данни.")