import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { api } from '../api'

export default function RulesPage() {
  const rules = useQuery({ queryKey: ['rules'], queryFn: api.rules, staleTime: Infinity })
  const { hash } = useLocation()
  useEffect(() => {
    if (hash && rules.data) document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [hash, rules.data])
  if (!rules.data) return <div className="text-ink-500">Загрузка…</div>
  const active = hash.replace('#', '')
  return (
    <div className="card p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">{rules.data.title}</h1>
      <p className="text-sm text-ink-500 mb-6">Единственная база правил сервиса. Ответы ссылаются на пункты этого Положения.</p>
      {rules.data.sections.map((s) => (
        <section key={s.id} className="mb-6">
          <h2 className="font-semibold text-lg mb-2">{s.id}. {s.title}</h2>
          <ol className="space-y-2">
            {s.rules.map((r) => {
              const id = `rule-${r.id.replace('.', '-')}`
              return (
                <li key={r.id} id={id} className={`rounded-lg p-2 text-sm leading-6 ${active === id ? 'bg-brand-50 ring-1 ring-brand-300' : ''}`}>
                  <b className="mr-1">{r.id}.</b>{r.text}
                </li>
              )
            })}
          </ol>
        </section>
      ))}
    </div>
  )
}
