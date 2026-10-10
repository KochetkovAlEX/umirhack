import { NavLink, Route, Routes } from 'react-router-dom'
import { FileText, BookOpen, Info, ScanLine } from 'lucide-react'
import UploadPage from './pages/UploadPage'
import DocumentPage from './pages/DocumentPage'
import RulesPage from './pages/RulesPage'
import AboutPage from './pages/AboutPage'

const navCls = ({ isActive }: { isActive: boolean }) =>
  `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-200'
  }`

export default function App() {
  return (
    <div className="min-h-full flex flex-col">
      <header className="sticky top-0 z-20 bg-[var(--paper)]/90 backdrop-blur border-b border-slate-200">
        <div className="mx-auto max-w-7xl px-4 h-14 flex items-center justify-between gap-3">
          <NavLink to="/" className="flex items-center gap-2 font-bold text-lg tracking-tight">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-orange-400">
              <ScanLine size={18} />
            </span>
            Онлайн-деканат
          </NavLink>
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={navCls}>
              <FileText size={16} /> <span className="hidden sm:inline">Документ</span>
            </NavLink>
            <NavLink to="/rules" className={navCls}>
              <BookOpen size={16} /> <span className="hidden sm:inline">Положение</span>
            </NavLink>
            <NavLink to="/about" className={navCls}>
              <Info size={16} /> <span className="hidden sm:inline">О сервисе</span>
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/d/:id" element={<DocumentPage />} />
          <Route path="/rules" element={<RulesPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </main>
      <footer className="border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        Предварительная проверка по учебному Положению. Окончательное решение принимает сотрудник деканата (п. 1.3).
        Все обработки выполняются локально, без внешних API.
      </footer>
    </div>
  )
}
