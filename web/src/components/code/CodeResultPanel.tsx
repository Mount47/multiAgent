import { useEffect, useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { fetchWorkspaceFiles } from '../../api/client'
import { EmptyState } from '../common/EmptyState'
import { Spinner } from '../common/Spinner'
import type { WorkspaceFile } from '../../types/api'

const extLang: Record<string, string> = {
  py: 'python', js: 'javascript', ts: 'typescript', json: 'json',
  yaml: 'yaml', yml: 'yaml', md: 'markdown', txt: 'text',
  html: 'html', css: 'css', sh: 'bash',
}

function getLang(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  return extLang[ext] || 'text'
}

export function CodeResultPanel() {
  const [files, setFiles] = useState<WorkspaceFile[]>([])
  const [selected, setSelected] = useState(0)
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    fetchWorkspaceFiles()
      .then((f) => { setFiles(f); setSelected(0) })
      .catch(() => setFiles([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <div className="flex justify-center py-10"><Spinner /></div>
  if (files.length === 0) return <EmptyState message="No generated files yet. Run a task to see code output." />

  const file = files[selected]

  return (
    <div className="h-[74vh] flex flex-col">
      <div className="flex items-center gap-1 mb-2 overflow-x-auto">
        {files.map((f, i) => (
          <button
            key={f.name}
            onClick={() => setSelected(i)}
            className={`px-3 py-1 rounded-t-lg text-[12px] border border-b-0 cursor-pointer whitespace-nowrap transition-colors ${
              i === selected
                ? 'bg-deep-bg text-accent border-line'
                : 'bg-transparent text-muted border-transparent hover:text-text'
            }`}
          >
            {f.name}
          </button>
        ))}
        <button
          onClick={load}
          className="ml-auto text-[11px] text-accent bg-transparent border-none cursor-pointer hover:underline"
        >
          Refresh
        </button>
      </div>
      <div className="flex-1 overflow-auto rounded-[10px] border border-line">
        <SyntaxHighlighter
          language={getLang(file.name)}
          style={oneDark}
          customStyle={{ margin: 0, background: '#091121', fontSize: '13px', minHeight: '100%' }}
          showLineNumbers
        >
          {file.content}
        </SyntaxHighlighter>
      </div>
    </div>
  )
}
