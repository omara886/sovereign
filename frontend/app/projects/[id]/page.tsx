'use client'
import { useState, useRef, useCallback, useEffect } from 'react'
import { useParams } from 'next/navigation'
import AnimatedContent from '@/components/react-bits/AnimatedContent'
import { Card } from '@/components/ui/Card'
import { Upload, Image, Type, Palette, FileText, Check, Loader2 } from 'lucide-react'

const API = '/api/proxy'

const FILE_TYPES = [
  { key: 'logo', label: 'Logo', icon: Image, accept: 'image/*', hint: 'PNG, SVG, WebP' },
  { key: 'screenshot', label: 'Screenshots', icon: FileText, accept: 'image/*', hint: 'PNG, JPG' },
  { key: 'font', label: 'Arabic Font', icon: Type, accept: '.ttf,.otf,.woff,.woff2', hint: 'TTF, OTF, WOFF' },
  { key: 'color_palette', label: 'Brand Colors', icon: Palette, accept: 'image/*,.pdf', hint: 'Image or PDF' },
  { key: 'other', label: 'Other', icon: FileText, accept: '*', hint: 'Any file up to 10MB' },
]

interface UploadedFile { type: string; url: string; name: string }

export default function ProjectPage() {
  const params = useParams()
  const slug = params.id as string
  const projectName = slug.charAt(0).toUpperCase() + slug.slice(1)
  const [uploads, setUploads] = useState<UploadedFile[]>([])
  const [uploading, setUploading] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [activeType, setActiveType] = useState('logo')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchUploads = useCallback(async () => {
    try {
      const res = await fetch(`${API}/uploads/${slug}`)
      if (res.ok) { const d = await res.json(); setUploads(d.files || []) }
    } catch { /* silent */ }
  }, [slug])

  useEffect(() => { fetchUploads() }, [fetchUploads])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(activeType); setError(''); setDone(null)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('file_type', activeType)
      const res = await fetch(`${API}/uploads/${slug}`, { method: 'POST', body: form })
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Upload failed') }
      setDone(activeType)
      await fetchUploads()
      setTimeout(() => setDone(null), 3000)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const active = FILE_TYPES.find(f => f.key === activeType)!

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <div className="pt-12 pb-6 px-4 md:px-8 border-b border-[rgba(201,168,76,0.1)]">
        <div className="max-w-3xl mx-auto">
          <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.3)] mb-1">Project</p>
          <h1 className="font-['Cormorant_Garamond'] text-3xl text-[#F8F6F1]">{projectName}</h1>
          <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.4)] mt-1">
            Upload brand assets — the AI uses these in every generated design.
          </p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 md:px-8 pt-6 pb-8">
        <AnimatedContent delay={100}>
          <h2 className="font-['IBM_Plex_Sans'] text-xs font-semibold text-[rgba(248,246,241,0.4)] uppercase tracking-wider mb-3">
            Asset Type
          </h2>

          {/* Type tabs — horizontal scroll on mobile */}
          <div className="flex gap-2 overflow-x-auto pb-3 mb-5 -mx-4 px-4">
            {FILE_TYPES.map(({ key, label, icon: Icon }) => (
              <button key={key} onClick={() => setActiveType(key)}
                className={`shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs font-['IBM_Plex_Sans'] transition-all duration-200 min-h-[40px] ${
                  activeType === key
                    ? 'bg-[rgba(201,168,76,0.15)] border-[rgba(201,168,76,0.4)] text-[#C9A84C]'
                    : 'border-[rgba(255,255,255,0.08)] text-[rgba(248,246,241,0.5)]'
                }`}
              >
                <Icon size={13} />{label}
              </button>
            ))}
          </div>

          {/* Upload zone */}
          <Card>
            <input ref={fileInputRef} type="file" accept={active.accept}
              onChange={handleUpload} className="hidden" id="file-upload" />
            <label htmlFor="file-upload" className="flex flex-col items-center gap-4 py-10 cursor-pointer group">
              <div className={`w-16 h-16 rounded-2xl border-2 border-dashed flex items-center justify-center transition-all duration-200 ${
                uploading ? 'border-[#C9A84C] bg-[rgba(201,168,76,0.08)]' :
                done ? 'border-[#10B981] bg-[rgba(16,185,129,0.08)]' :
                'border-[rgba(201,168,76,0.3)] group-hover:border-[#C9A84C]'
              }`}>
                {uploading ? <Loader2 size={24} className="text-[#C9A84C] animate-spin" /> :
                 done ? <Check size={24} className="text-[#10B981]" /> :
                 <Upload size={24} className="text-[rgba(201,168,76,0.5)] group-hover:text-[#C9A84C]" />}
              </div>
              <div className="text-center">
                <p className="font-['IBM_Plex_Sans'] text-sm text-[#F8F6F1] font-medium">
                  {uploading ? `Uploading ${active.label}...` :
                   done ? 'Uploaded!' : `Tap to upload ${active.label}`}
                </p>
                <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.4)] mt-1">
                  {active.hint} · Max 10MB
                </p>
              </div>
            </label>
            {error && <p className="font-['IBM_Plex_Sans'] text-sm text-[#EF4444] text-center pb-4">{error}</p>}
          </Card>
        </AnimatedContent>

        {/* Uploaded files grid */}
        {uploads.length > 0 && (
          <AnimatedContent delay={200}>
            <h2 className="font-['IBM_Plex_Sans'] text-xs font-semibold text-[rgba(248,246,241,0.4)] uppercase tracking-wider mt-8 mb-4">
              Uploaded ({uploads.length})
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {uploads.map((file, i) => (
                <Card key={i}>
                  <div className="aspect-square rounded-xl bg-[#0A0A0A] overflow-hidden flex items-center justify-center mb-2">
                    {file.type !== 'font' ? (
                      <img src={file.url} alt={file.name}
                        className="w-full h-full object-contain"
                        onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                      />
                    ) : <Type size={28} className="text-[#C9A84C]" />}
                  </div>
                  <p className="font-['IBM_Plex_Sans'] text-xs text-[rgba(248,246,241,0.6)] truncate">{file.name}</p>
                  <span className="font-['IBM_Plex_Sans'] text-[10px] text-[#C9A84C] uppercase tracking-wider">{file.type}</span>
                </Card>
              ))}
            </div>
          </AnimatedContent>
        )}

        {uploads.length === 0 && !uploading && (
          <p className="font-['IBM_Plex_Sans'] text-sm text-[rgba(248,246,241,0.25)] text-center mt-8">
            No assets yet. Start with your logo — the AI uses it in every design.
          </p>
        )}
      </div>
    </div>
  )
}
