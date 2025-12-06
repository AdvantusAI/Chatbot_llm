# M8 Solutions – Chatbot Contextual de Inteligencia de Negocio

Este documento resume la arquitectura propuesta para el chatbot que consulta datos
empresariales en Supabase y responde con texto o gráficas.

## Componentes
- **Frontend (React + Vite + Tailwind + ShadCN + Recharts)**: interfaz de chat y gráficos.
- **Backend (FastAPI)**: recibe preguntas, coordina el LLM, ejecuta SQL seguro y retorna
  respuestas y datos para visualización.
- **Base de datos (Supabase Postgres)**: almacena métricas de negocio y logs de interacción.
- **Capa de IA (OpenAI GPT-4/5)**: analiza intención, completa datos faltantes y genera SQL.

## Flujo
1. El usuario ingresa una pregunta libre.
2. FastAPI envía la pregunta al LLM para detectar intención y entidades.
3. Con un prompt dedicado se genera SQL seguro usando tablas permitidas.
4. La consulta se ejecuta vía RPC `execute_sql_safe` en Supabase.
5. Se construye la respuesta textual y, si es pertinente, se arma un payload para gráficos
   (líneas, barras o pastel).
6. Cada interacción se guarda en `m8_schema.chat_logs` para trazabilidad.

## Seguridad
- El backend no ejecuta SQL libre; se apoya en plantillas y en la función RPC con
  `SECURITY DEFINER` para limitar a una sola sentencia `SELECT`.
- Se usan claves de servicio en variables de entorno (`SUPABASE_SERVICE_KEY`, `OPENAI_API_KEY`).

## Despliegue
- Contenedor Docker basado en `python:3.11-slim`.
- Sugerido usar `uvicorn` detrás de un proxy y Supabase Auth/JWT para identificar al usuario.
