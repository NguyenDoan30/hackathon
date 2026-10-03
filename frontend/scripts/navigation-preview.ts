import {useSyncExternalStore} from 'react';
const eventName='luma-preview-navigation';
function subscribe(listener:()=>void) {
  window.addEventListener('popstate',listener);window.addEventListener(eventName,listener);
  return ()=>{window.removeEventListener('popstate',listener);window.removeEventListener(eventName,listener);};
}
const router={push(to:string){navigate(to,false);},replace(to:string){navigate(to,true);},back(){window.history.back();}};
function navigate(to:string,replace:boolean) {
  const url=new URL(to,window.location.href);
  if(url.origin!==window.location.origin)throw new Error('Preview chỉ điều hướng trong ứng dụng.');
  window.history[replace?'replaceState':'pushState']({},'',url.pathname+url.search+url.hash);
  window.dispatchEvent(new Event(eventName));window.scrollTo(0,0);
}
export function useRouter(){return router;}
export function usePathname(){return useSyncExternalStore(subscribe,()=>window.location.pathname,()=>'/');}
export function useSearchParams(){const query=useSyncExternalStore(subscribe,()=>window.location.search,()=>'');return new URLSearchParams(query);}
