import { useRef, useState } from 'react'
import { CloudUpload, FileImage, X } from 'lucide-react'

interface Props { file: File | null; onChange: (file: File | null) => void; accept?: string; label?: string }
export function UploadZone({ file, onChange, accept = 'image/png,image/jpeg,image/webp', label = 'Drop an image here' }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const choose = (candidate?: File) => {
    if (!candidate) return
    if (accept.includes('image') && !candidate.type.startsWith('image/')) return
    onChange(candidate)
  }
  return <div className={`upload-zone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`} onDragOver={(e) => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(e) => { e.preventDefault(); setDragging(false); choose(e.dataTransfer.files[0]) }} onClick={() => input.current?.click()}>
    <input ref={input} type="file" accept={accept} hidden onChange={(e) => choose(e.target.files?.[0])} />
    {file ? <div className="file-preview"><FileImage size={28} /><div><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(1)} KB · {file.type.split('/')[1]?.toUpperCase()}</span></div><button className="icon-button" onClick={(e) => { e.stopPropagation(); onChange(null) }}><X size={17} /></button></div> : <><div className="upload-icon"><CloudUpload size={23} /></div><strong>{label}</strong><span>PNG, JPG, JPEG, or WEBP · up to 20 MB</span><button className="text-button" type="button">Browse files</button></>}
  </div>
}
