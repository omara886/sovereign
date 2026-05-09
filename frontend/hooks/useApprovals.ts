import useSWR from 'swr'
import { api } from '@/lib/api'
export function useApprovals(){return useSWR('/api/approvals', (p)=>api(p))}
