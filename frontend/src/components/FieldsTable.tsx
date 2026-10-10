import { Check, X } from 'lucide-react'
import type { FieldValue } from '../api'

interface Props {
  fields: Record<string, FieldValue>
  highlight: string | null
  onSelect: (key: string | null) => void
  docId: string
}

export default function FieldsTable({ fields, highlight, onSelect }: Props) {
  return (
    <table className="w-full text-sm">
      <thead className="text-xs text-slate-500">
        <tr><th className="text-left font-medium pb-2">Поле</th><th className="text-left font-medium pb-2">Значение</th><th className="text-right font-medium pb-2">OCR</th></tr>
      </thead>
      <tbody>
        {Object.values(fields).map((f) => {
          const active = highlight === f.key
          return (
            <tr key={f.key} onClick={() => onSelect(active ? null : f.key)} className={`cursor-pointer border-t border-slate-100 ${active ? 'bg-orange-50' : 'hover:bg-slate-50'}`}>
              <td className="py-2 pr-2 align-top">
                <div className="font-medium">{f.label}</div>
                <div className="text-[11px] text-slate-400">{f.key}</div>
              </td>
              <td className="py-2 pr-2 align-top">
                {f.kind === 'mark' ? (
                  f.found ? <span className="chip border-blue-300 bg-blue-50 text-blue-800"><Check size={12} /> есть</span>
                    : <span className="chip border-red-300 bg-red-50 text-red-800"><X size={12} /> отсутствует</span>
                ) : f.found ? (
                  <span>{String(f.value)}</span>
                ) : (
                  <span className="chip border-slate-300 bg-slate-100 text-slate-600">не найдено</span>
                )}
                {f.kind === 'text' && f.raw && f.raw !== f.value && f.found && (
                  <div className="text-[11px] text-slate-400">OCR: {f.raw}</div>
                )}
              </td>
              <td className="py-2 text-right align-top text-xs text-slate-500">{f.confidence ? `${(f.confidence * 100).toFixed(0)}%` : '—'}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
