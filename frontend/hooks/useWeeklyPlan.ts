import useSWR from 'swr'
import { api } from '@/lib/api'
export function useWeeklyPlan(id:string){return useSWR(id?`/api/plans/${id}`:null, (p)=>api(p))}
