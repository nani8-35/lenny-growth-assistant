export type Source={id:string;title:string;guest:string;source_url:string;timestamp_ref:string|null;content:string;score:number};
export type Message={id:string;role:'user'|'assistant';content:string;sources:Source[];status?:string;provider?:string;mode?:string};
export type Artifact={id:string;message_id:string;artifact_type:'markdown'|'html';title:string;content:string};
export type Session={id:string;title:string;updated_at:string};
export type User={id:string;name:string;email:string;is_admin:boolean};
export type AdminUser=User & {created_at:string;conversation_count:number};
export type Health={ready:boolean;database:boolean;ollama:boolean;agent:boolean;chunks:number;episodes:number;cloud_configured:boolean;gemini_configured?:boolean;embedding_model_ready?:boolean;default_provider?:string;ollama_model?:string;models?:string[]};
const key='lenny-access-token';
export const accessToken=()=>localStorage.getItem(key)||'';
export const setAccessToken=(token:string)=>localStorage.setItem(key,token);
export const clearAccessToken=()=>localStorage.removeItem(key);
export async function api<T>(path:string,init?:RequestInit):Promise<T>{
 const headers={...init?.headers,'Content-Type':'application/json',...(accessToken()?{Authorization:`Bearer ${accessToken()}`}:{})};
 const res=await fetch('/api'+path,{...init,headers});
 const text=await res.text();const body=text?JSON.parse(text):null;if(!res.ok)throw new Error(body?.error?.message||body?.detail||'Request failed');return body as T;
}
export async function consumeSSE(body:ReadableStream<Uint8Array>,onEvent:(value:any)=>void){
 const reader=body.getReader();const decoder=new TextDecoder();let pending='';
 try{while(true){const {done,value}=await reader.read();if(done)break;pending+=decoder.decode(value,{stream:true});let boundary;while((boundary=pending.indexOf('\n\n'))!==-1){const frame=pending.slice(0,boundary);pending=pending.slice(boundary+2);for(const line of frame.split('\n'))if(line.startsWith('data: '))onEvent(JSON.parse(line.slice(6)));}}}finally{reader.releaseLock();}
}
