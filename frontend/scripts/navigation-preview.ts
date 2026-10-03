import {useSyncExternalStore} from 'react';

const eventName='luma-preview-navigation';

function currentRoute() {
  const hash=window.location.hash.startsWith('#')?window.location.hash.slice(1):'';
  const route=hash || '/';
  const [path,query='']=route.split('?');
  return {
    pathname:path.startsWith('/')?path:'/'+path,
    search:query?('?'+query):''
  };
}

function subscribe(listener:()=>void) {
  window.addEventListener('hashchange',listener);
  window.addEventListener(eventName,listener);
  return ()=>{
    window.removeEventListener('hashchange',listener);
    window.removeEventListener(eventName,listener);
  };
}

const router={
  push(to:string){navigate(to,false);},
  replace(to:string){navigate(to,true);},
  back(){window.history.back();}
};

function navigate(to:string,replace:boolean) {
  if(!to.startsWith('/')) throw new Error('Preview chỉ điều hướng trong ứng dụng.');
  const target='#'+to;
  if(replace) window.history.replaceState({},'',target);
  else window.history.pushState({},'',target);
  window.dispatchEvent(new Event(eventName));
  window.scrollTo(0,0);
}

export function useRouter(){return router;}

export function usePathname(){
  return useSyncExternalStore(
    subscribe,
    ()=>currentRoute().pathname,
    ()=>'/'
  );
}

export function useSearchParams(){
  const query=useSyncExternalStore(
    subscribe,
    ()=>currentRoute().search,
    ()=>''
  );
  return new URLSearchParams(query);
}
