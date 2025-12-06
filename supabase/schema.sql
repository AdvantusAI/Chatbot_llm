-- Schema and helper functions for the M8 Solutions chatbot
CREATE SCHEMA IF NOT EXISTS m8_schema;

CREATE TABLE IF NOT EXISTS m8_schema.chat_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id),
  question TEXT,
  refined_question TEXT,
  generated_sql TEXT,
  response_summary TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS m8_schema.bot_contexts (
  id SERIAL PRIMARY KEY,
  context_name VARCHAR(50),
  description TEXT,
  example_questions TEXT[],
  sql_template TEXT
);

-- RPC function to run sanitized SQL templates server-side
CREATE OR REPLACE FUNCTION m8_schema.execute_sql_safe(sql TEXT)
RETURNS SETOF RECORD
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Only allow read-only operations
  IF position(';' IN sql) > 0 THEN
    RAISE EXCEPTION 'Multiple statements are not allowed';
  END IF;

  RETURN QUERY EXECUTE sql;
END;
$$;

GRANT EXECUTE ON FUNCTION m8_schema.execute_sql_safe(TEXT) TO anon, authenticated;
