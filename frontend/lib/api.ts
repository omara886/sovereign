export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
export async function api<T>(path:string, init?:RequestInit):Promise<T>{const r=await fetch(`${API_URL}${path}`,{...init,headers:{'Content-Type':'application/json',...(init?.headers||{})}});if(!r.ok) throw new Error('api'); return r.json()}
