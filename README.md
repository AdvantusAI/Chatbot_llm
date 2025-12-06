# M8 Solutions – Chatbot contextual de Inteligencia de Negocio

Implementación inicial de un chatbot que interpreta preguntas en lenguaje natural
sobre datos empresariales, genera SQL seguro contra Supabase y responde con texto
o gráficos.

## Carpetas
- `/backend`: API FastAPI con endpoints `/chatbot/query`, `/chatbot/history` y `/health`.
- `/frontend`: UI React + Vite con chat básico y componente de barras.
- `/supabase`: Scripts SQL para tablas y RPC de ejecución segura.
- `/docs`: Notas de arquitectura.

## Ejecutar backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=...
export SUPABASE_URL=...
export SUPABASE_SERVICE_KEY=...
uvicorn backend.main:app --reload
```

## Ejecutar frontend
```bash
cd frontend
npm install
npm run dev -- --host
```

Configura la variable `VITE_API_URL` apuntando al backend (por defecto usa
`http://localhost:8000`).
