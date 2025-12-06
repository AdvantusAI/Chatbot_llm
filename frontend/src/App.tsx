import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export interface ChatMessage {
  id: string
  author: 'user' | 'bot'
  content: string
  chart?: ChartPayload
}

export interface ChartPayload {
  type: string
  x: (string | number | null)[]
  y: (string | number | null)[]
}

interface ApiResponse {
  answer: string
  chart?: ChartPayload
  raw_data?: Record<string, string | number | null>[]
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function ChartView({ chart }: { chart: ChartPayload }) {
  const data = useMemo(() => {
    if (!chart) return []
    return chart.x.map((xValue, index) => ({
      x: xValue,
      y: chart.y[index],
    }))
  }, [chart])

  if (!chart) return null

  return (
    <div className="chart-card">
      <h3>Visualización</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="x" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="y" fill="#22d3ee" name="Valor" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function App() {
  const [question, setQuestion] = useState('¿Cuál fue la precisión del forecast en octubre?')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setMessages([
      {
        id: 'intro',
        author: 'bot',
        content:
          'Soy tu asistente de analítica de negocio. Pregunta sobre ventas, forecast o inventario y devolveré texto y gráficos.',
      },
    ])
  }, [])

  const sendQuestion = async () => {
    if (!question.trim()) return
    const userMessage: ChatMessage = { id: crypto.randomUUID(), author: 'user', content: question }
    setMessages((prev) => [...prev, userMessage])
    setLoading(true)
    setError(null)

    try {
      const { data } = await axios.post<ApiResponse>(`${API_URL}/chatbot/query`, { question })
      const botMessage: ChatMessage = {
        id: crypto.randomUUID(),
        author: 'bot',
        content: data.answer,
        chart: data.chart,
      }
      setMessages((prev) => [...prev, botMessage])
    } catch (err) {
      console.error(err)
      setError('No pudimos obtener la respuesta. Revisa la consola o el backend.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">M8 Solutions · Chatbot BI</p>
          <h1>Consultas en lenguaje natural sobre tus datos</h1>
          <p className="subtitle">
            Analiza ventas, forecast, inventario o errores de pronóstico. El bot pedirá aclaraciones
            cuando falten filtros y devolverá respuestas con gráficos.
          </p>
        </div>
        <div className="status">{loading ? 'Generando respuesta…' : 'Listo'}</div>
      </header>

      <main className="layout">
        <section className="chat">
          <div className="chat-window">
            {messages.map((msg) => (
              <div key={msg.id} className={`bubble ${msg.author}`}>
                <div className="label">{msg.author === 'user' ? 'Tú' : 'Bot'}</div>
                <p>{msg.content}</p>
                {msg.chart && <ChartView chart={msg.chart} />}
              </div>
            ))}
            {error && <div className="bubble error">{error}</div>}
          </div>

          <div className="composer">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Pregunta: ventas, forecast, inventario…"
            />
            <button onClick={sendQuestion} disabled={loading}>
              {loading ? 'Enviando…' : 'Preguntar'}
            </button>
          </div>
        </section>

        <aside className="sidebar">
          <h3>Prompts base</h3>
          <ul>
            <li>Precisión del forecast por canal y mes</li>
            <li>Ventas totales por región y producto</li>
            <li>Nivel de inventario promedio por categoría</li>
          </ul>
          <h3>Recetas rápidas</h3>
          <p>Configura `VITE_API_URL` en `.env` para conectar con FastAPI.</p>
          <p>Ejecuta `npm install` y `npm run dev` dentro de `/frontend`.</p>
        </aside>
      </main>
    </div>
  )
}

export default App
