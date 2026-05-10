export function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-[20px] p-[2px] bg-gradient-to-br from-[rgba(201,168,76,0.1)] to-transparent border border-[rgba(201,168,76,0.15)] ${className}`}><div className="rounded-[18px] bg-[#1E293B] p-4 md:p-6 h-full">{children}</div></div>
}
