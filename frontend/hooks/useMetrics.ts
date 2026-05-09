import useSWR from 'swr'
export function useMetrics(){return useSWR('/api/metrics',()=>[])}
