from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

# Abre uma sessão direta no banco para executar o cadastro inicial manualmente.
db = SessionLocal()

# Credenciais padrão usadas para semear o primeiro usuário administrativo.
username = "admin"
password = "admin123"

# Verifica se o usuário já existe para evitar duplicidade ao rodar o script mais de uma vez.
existing_user = db.query(User).filter(User.username == username).first()

if existing_user:
    print("Usuário já existe.")
else:
    # Persiste o novo usuário já com a senha protegida por hash.
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

# Fecha a conexão aberta manualmente ao final do script.
db.close()
