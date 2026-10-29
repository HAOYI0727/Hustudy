// Browser persistence is optional; a failed cache must not turn a server success into failure.
export const bankStorage={
 getItem(key:string){try{return localStorage.getItem(key);}catch{return null;}},
 setItem(key:string,value:string){try{localStorage.setItem(key,value);}catch{/* Server state remains authoritative. */}},
 removeItem(key:string){try{localStorage.removeItem(key);}catch{/* Optional cache. */}},
};
