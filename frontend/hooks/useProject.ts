import useSWR from 'swr'
import { api } from '@/lib/api'
export function useProject(id:string){return useSWR(id?`/api/projects/${id}`:null, (p)=>api(p))}
