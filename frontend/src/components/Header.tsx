import { Link, NavLink } from 'react-router-dom'
import { FlaskConical } from 'lucide-react'
import { StatusBadge } from './StatusBadge'

export function Header({ online }: { online: boolean }) {
  return <header className="site-header">
    <Link to="/" className="brand"><span className="brand-mark"><FlaskConical size={19} /></span><span>Diffusion <em>Compression</em> Lab</span></Link>
    <nav>{[['/', 'Compress'], ['/decode', 'Decode'], ['/experiments', 'Experiments'], ['/model', 'Model'], ['/about', 'About']].map(([to, label]) => <NavLink key={to} to={to} end={to === '/'}>{label}</NavLink>)}</nav>
    <StatusBadge label={online ? 'SYSTEM READY' : 'BACKEND OFFLINE'} tone={online ? 'ready' : 'error'} />
  </header>
}
