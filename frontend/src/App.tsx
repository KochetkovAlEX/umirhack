import { NavLink, Route, Routes } from 'react-router-dom'
import { FileText, BookOpen, Info } from 'lucide-react'
import UploadPage from './pages/UploadPage'
import DocumentPage from './pages/DocumentPage'
import RulesPage from './pages/RulesPage'
import AboutPage from './pages/AboutPage'

const navCls = ({ isActive }: { isActive: boolean }) =>
  `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition ${
    isActive ? 'bg-brand-500 text-white' : 'text-ink-700 hover:bg-brand-50 hover:text-brand-700'
  }`

function Logo() {
  return (
    <NavLink to="/" className="flex items-center gap-2.5">
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-brand-500 text-white font-black text-sm tracking-tight shadow-[0_4px_12px_rgba(80,184,72,0.35)]">
        ОД
      </span>
      <span className="leading-tight">
        <span className="block font-bold text-[17px] text-ink-900 tracking-tight">Онлайн-деканат</span>
        <span className="block text-[11px] text-ink-500">Цифровой секретарь студента · хакатон Банка «Центр-инвест»</span>
      </span>
    </NavLink>
  )
}

export default function App() {
  return (
    <div className="min-h-full flex flex-col">
      <div className="h-1 bg-gradient-to-r from-brand-500 via-brand-400 to-sun-400" />
      <header className="sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-ink-200">
        <div className="mx-auto max-w-7xl px-4 h-16 flex items-center justify-between gap-3">
          <Logo />
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
      <footer className="border-t border-ink-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-5 grid gap-2 sm:grid-cols-[1fr_auto] text-xs text-ink-500">
          <div>
            <div className="text-ink-700 font-medium">Предварительная проверка по учебному Положению.</div>
            Окончательное решение принимает сотрудник деканата (п. 1.3). Обработка выполняется локально, без внешних API.
          </div>
          <div className="sm:text-right">
            © 2026 Онлайн-деканат · учебный проект для кейса хакатона Банка «Центр-инвест».
            <br />Не является сервисом банка.
          </div>
        </div>
      </footer>
    </div>
  )
}
