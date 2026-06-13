# AprendeYEmprende

## Estructura del proyecto

```
aprendeyemprende/
│
├── frontend/               ← Abrir en el navegador
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
└── backend/                ← Servidor Python + FastAPI
    ├── .env                ← Tus credenciales (no subir a Git)
    ├── requirements.txt
    └── app/
        ├── main.py         ← Punto de entrada del servidor
        ├── database.py     ← Conexión a MongoDB
        ├── core/
        │   ├── config.py   ← Variables de entorno
        │   └── security.py ← JWT y contraseñas
        ├── models/
        │   ├── user.py
        │   ├── course.py
        │   ├── task.py
        │   └── payment.py
        └── routes/
            ├── auth.py     ← /v1/auth/register, /v1/auth/login
            ├── courses.py  ← /v1/courses/
            ├── tasks.py    ← /v1/tasks/
            └── payments.py ← /v1/payments/
```

---

## Cómo correr el proyecto

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

El servidor queda en: http://localhost:8000
Documentación automática: http://localhost:8000/docs

### 2. Frontend

Abre `frontend/index.html` directamente en el navegador.
O usa Live Server en VS Code.

---

## Variables de entorno (.env)

Edita `backend/.env` con tus datos de MongoDB Atlas:

```
MONGODB_URL=mongodb+srv://usuario:password@cluster.mongodb.net/
DB_NAME=aprendeyemprende
SECRET_KEY=una_clave_larga_y_segura
```
