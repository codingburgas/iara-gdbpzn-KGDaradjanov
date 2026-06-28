from app import app, db, User

with app.app_context():
    user = User.query.first()

    if user:
        user.role = 'Admin'
        db.session.commit()
        print(f"Успех! Потребителят '{user.username}' вече е Главен Администратор (Admin)!")
    else:
        print("Грешка: Няма намерени потребители.")