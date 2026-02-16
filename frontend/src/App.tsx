import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Student from './pages/Student'
import Admin from './pages/Admin'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/session/:sessionId" element={<Student />} />
      <Route path="/session/:sessionId/admin" element={<Admin />} />
    </Routes>
  )
}

export default App
