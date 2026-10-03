import { useEffect, useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { getSystemStatus } from './api/model'
import { Compress } from './pages/Compress'
import { Decode } from './pages/Decode'
import { Experiments } from './pages/Experiments'
import { Model } from './pages/Model'
import { About } from './pages/About'
import './styles.css'

export default function App() { const [online, setOnline] = useState(false); useEffect(() => { const check = () => getSystemStatus().then(() => setOnline(true)).catch(() => setOnline(false)); check(); const id = window.setInterval(check, 15000); return () => clearInterval(id) }, []); return <BrowserRouter><Routes><Route path="/" element={<Compress online={online} />} /><Route path="/decode" element={<Decode online={online} />} /><Route path="/experiments" element={<Experiments online={online} />} /><Route path="/model" element={<Model online={online} />} /><Route path="/about" element={<About online={online} />} /></Routes></BrowserRouter> }
