import { useCallback, useMemo, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Camera, FileUp, Loader2, Search, Sparkles } from 'lucide-react'
import { api, SUGGESTED_QUESTIONS } from '../api'

const MAX_MB = 20
const STEPS = ['Загружаем файл…', 'Распознаём текст (OCR)…', 'Извлекаем поля…', 'Проверяем по Положению…']

export default function UploadPage() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [docType, setDocType] = useState('auto')
  const [question, setQuestion] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState(0)
  const types = useQuery({ queryKey: ['doc-types'], queryFn: api.docTypes })

  const preview = useMemo(() => (file && file.type.startsWith('image/') ? URL.createObjectURL(file) : null), [file])

  const onDrop = useCallback((accepted: File[], rejected: unknown[]) => {
    setError(null)
    if (rejected.length) setError('Поддерживаются JPG, PNG и одностраничный PDF до 20 МБ')
    if (accepted[0]) setFile(accepted[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    multiple: false,
    noClick: true,
    maxSize: MAX_MB * 1024 * 1024,
    accept: { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'], 'application/pdf': ['.pdf'] },
  })

  const mutation = useMutation({
    mutationFn: async ({ check }: { check: boolean }) => {
      if (!file) throw new Error('Выберите файл')
      setStep(0)
      const timer = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 1500)
      try {
        return await api.upload(file, docType, check ? '' : question.trim(), check)
      } finally {
        clearInterval(timer)
      }
    },
    onSuccess: (doc) => navigate(`/d/${doc.id}`, { state: { answer: doc.answer } }),
    onError: (e: Error) => setError(e.message),
  })

  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
      <section className="card p-5">
        <h1 className="text-2xl font-bold mb-1">Проверить студенческий документ</h1>
        <p className="text-sm text-ink-600 mb-4">
          Загрузите фото или скан справки/заявления (JPG, PNG, PDF) и задайте вопрос на русском. Сервис распознает текст,
          заполнит карточку полей и ответит со ссылками на поля документа и пункты Положения.
        </p>

        <div
          {...getRootProps()}
          className={`rounded-2xl border-2 border-dashed p-6 text-center transition ${
            isDragActive ? 'border-brand-400 bg-brand-50' : 'border-ink-300 bg-ink-50'
          }`}
        >
          <input {...getInputProps()} />
          {file ? (
            <div className="flex flex-col items-center gap-3">
              {preview ? (
                <img src={preview} alt="превью" className="max-h-64 rounded-lg shadow" />
              ) : (
                <div className="h-24 w-20 rounded-lg bg-surface border flex items-center justify-center text-xs text-ink-500">PDF</div>
              )}
              <div className="text-sm">
                <b>{file.name}</b> · {(file.size / 1024).toFixed(0)} КБ
              </div>
              <button type="button" className="btn-ghost" onClick={open}>
                Выбрать другой файл
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 py-4">
              <FileUp className="text-ink-400" size={40} />
              <div className="text-sm text-ink-600">Перетащите файл сюда или</div>
              <div className="flex flex-wrap gap-2 justify-center">
                <button type="button" className="btn-primary" onClick={open}>
                  <FileUp size={16} /> Выбрать файл
                </button>
                <label className="btn-ghost cursor-pointer">
                  <Camera size={16} /> Сфотографировать
                  <input
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
                  />
                </label>
              </div>
              <div className="text-xs text-ink-500">JPG, PNG или одностраничный PDF, до {MAX_MB} МБ</div>
            </div>
          )}
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            <span className="block mb-1 font-medium">Тип документа</span>
            <select className="input" value={docType} onChange={(e) => setDocType(e.target.value)}>
              <option value="auto">Определить автоматически</option>
              {types.data?.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.title}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="block mt-4 text-sm">
          <span className="block mb-1 font-medium">Вопрос (необязательно)</span>
          <textarea
            className="input min-h-[72px]"
            placeholder="Например: Хватит ли этой справки для перевода? Какова дата выдачи?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
        </label>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              className="chip border-ink-300 bg-surface hover:bg-ink-100"
              onClick={() => setQuestion(q)}
            >
              {q}
            </button>
          ))}
        </div>

        {error && <div className="mt-4 rounded-xl bg-red-50 text-red-700 text-sm p-3">{error}</div>}

        <div className="mt-5 flex flex-wrap gap-2">
          <button className="btn-accent" disabled={!file || mutation.isPending} onClick={() => mutation.mutate({ check: false })}>
            {mutation.isPending ? <Loader2 className="animate-spin" size={16} /> : <Sparkles size={16} />}
            {question.trim() ? 'Задать вопрос' : 'Распознать документ'}
          </button>
          <button className="btn-ghost" disabled={!file || mutation.isPending} onClick={() => mutation.mutate({ check: true })}>
            <Search size={16} /> Проверить без вопроса
          </button>
        </div>
        {mutation.isPending && (
          <div className="mt-3 text-sm text-ink-600 flex items-center gap-2">
            <Loader2 className="animate-spin" size={14} /> {STEPS[step]} (обычно 3–8 секунд)
          </div>
        )}
      </section>

      <aside className="space-y-4">
        <div className="card p-5">
          <h2 className="font-semibold mb-2">Как это работает</h2>
          <ol className="text-sm text-ink-700 space-y-2 list-decimal pl-5">
            <li>OCR читает текст на снимке (PaddleOCR / Tesseract, локально).</li>
            <li>Поля раскладываются по карточке выбранного типа; пустые — «не найдено».</li>
            <li>Проверяется наличие подписи и печати как графических отметок (п. 2.3).</li>
            <li>Ответ формируется только по документу и Положению со ссылками на источники (п. 2.1).</li>
            <li>Если сведений нет — сервис честно сообщает об этом (п. 2.4, 6.3).</li>
          </ol>
        </div>
        <div className="card p-5">
          <h2 className="font-semibold mb-2">Поддерживаемые типы</h2>
          <ul className="text-sm text-ink-700 space-y-1">
            {types.data?.map((t) => (
              <li key={t.key} className="flex justify-between gap-2">
                <span>{t.title}</span>
                <span className="text-ink-400">раздел {t.rules_section} · {t.fields.length} полей</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-ink-500 mt-3">
            Новый тип добавляется YAML-файлом в <code>config/doc_types/</code> без изменения кода.
          </p>
        </div>
      </aside>
    </div>
  )
}
