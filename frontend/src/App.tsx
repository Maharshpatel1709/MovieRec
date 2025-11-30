import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { SearchPage } from './pages/SearchPage'
import { ChatPage } from './pages/ChatPage'
import { MovieDetailPage } from './pages/MovieDetailPage'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/movie/:id" element={<MovieDetailPage />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App

