import useSWR from 'swr'
import { api } from '@/lib/api'
export function useProjects(){return useSWR('/api/projects', (p)=>api(p))}
