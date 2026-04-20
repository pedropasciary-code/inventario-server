from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

db = SessionLocal()

username = "admin"
password = "admin123"

existing_user = db.query(User).filter(User.username == username).first()

if existing_user:
    print("Usuário já existe.")
else:
    user = User(
        username=username,
        password_hash=hash_password(password),
        is_active=True
    )
    db.add(user)
    db.commit()
    print("Usuário criado com sucesso.")
    print(f"Usuário: {username}")
    print(f"Senha: {password}")

db.close()