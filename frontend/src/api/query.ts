import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({defaultOptions:{queries:{retry:false,staleTime:0,gcTime:60_000,refetchOnWindowFocus:false,refetchOnReconnect:false},mutations:{retry:false}}});
const partitions = new Map<string,string>();
const generations = new Map<string,number>();
let serial = 0;
export function sessionPartition(token?: string) {
  if (!token) return "public";
  let value = partitions.get(token);
  if (!value) {value="session-"+(++serial);partitions.set(token,value);}
  return value;
}
export function sessionGeneration(scope:string) {return generations.get(scope) || 0;}
export function advanceSessionGeneration(scope:string) {generations.set(scope,sessionGeneration(scope)+1);}
export function clearSessionQueries() {queryClient.clear();partitions.clear();generations.clear();}
