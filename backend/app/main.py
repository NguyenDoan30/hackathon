from contextlib import asynccontextmanager
from pathlib import Path
import logging
import time
from uuid import uuid4
from fastapi import FastAPI,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,FileResponse,RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from .config import Settings
from .database import Database
from .integrations.providers import Providers
from .errors import ApiError
from .api import auth,lessons,documents,learning
from .models import HealthPublic,ErrorEnvelope

log=logging.getLogger('study.backend')

def create_app(settings=None,providers=None):
    settings=settings or Settings.from_env()
    db=Database(settings.data_dir)
    providers=providers or Providers.from_settings(settings)

    @asynccontextmanager
    async def lifespan(app):
        db.initialize()
        if settings.mode=='demo':
            from .services.seed import seed_demo
            seed_demo(db,providers)
        yield

    app=FastAPI(title='AI Study Assistant · Backend',version='1.0.0',
                description='API của Người 2: dữ liệu, quyền truy cập, upload và kết nối module. Chế độ demo dùng fixture, không phải AI thật.',lifespan=lifespan,
                responses={code:{'model':ErrorEnvelope,'description':label} for code,label in [(401,'Cần đăng nhập'),(404,'Không tìm thấy dữ liệu của tài khoản'),(409,'Xung đột trạng thái'),(422,'Dữ liệu không hợp lệ'),(502,'Module lỗi hoặc trả sai đặc tả'),(503,'Module chưa kết nối')]})
    app.state.settings=settings
    app.state.db=db
    app.state.providers=providers
    app.add_middleware(CORSMiddleware,allow_origins=list(settings.cors_origins),allow_credentials=False,allow_methods=['GET','POST','PATCH','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type'],expose_headers=['X-Request-ID','X-Process-Time'])

    def error_response(request,status,code,message,details=None):
        payload={'error':{'code':code,'message':message},'request_id':getattr(request.state,'request_id',None)}
        if details is not None:
            payload['error']['details']=details
        return JSONResponse(payload,status_code=status,headers={'WWW-Authenticate':'Bearer'} if status==401 else None)

    @app.middleware('http')
    async def trace(request,call_next):
        request.state.request_id=str(uuid4())
        start=time.perf_counter()
        response=await call_next(request)
        elapsed=(time.perf_counter()-start)*1000
        response.headers['X-Request-ID']=request.state.request_id
        response.headers['X-Process-Time']=f'{elapsed:.2f}ms'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        # Avoid logs containing body, password, token or uploaded content.
        log.info('%s %s %s %.2fms request=%s',request.method,request.url.path,response.status_code,elapsed,request.state.request_id)
        return response

    @app.exception_handler(ApiError)
    async def api_error(request,exc):
        return error_response(request,exc.status,exc.code,exc.message,exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        details=[{'field':'.'.join(str(x) for x in e['loc']),'message':e['msg'],'type':e['type']} for e in exc.errors()]
        return error_response(request,422,'VALIDATION_ERROR','Dữ liệu gửi lên chưa hợp lệ.',details)

    @app.exception_handler(HTTPException)
    async def http_error(request,exc):
        return error_response(request,exc.status_code,'HTTP_ERROR',str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected(request,exc):
        log.exception('Unexpected request failure request=%s',getattr(request.state,'request_id',None),exc_info=exc)
        return error_response(request,500,'INTERNAL_ERROR','Có lỗi hệ thống. Dùng request_id để kiểm tra log.')

    @app.get('/health',tags=['00 · Hệ thống'],response_model=HealthPublic,summary='Trạng thái API, database và module')
    def health():
        with db.session() as conn:
            conn.execute('SELECT 1').fetchone()
        return {'status':'ok','database':'connected','mode':settings.mode,'integrations':providers.status(),'version':'1.0.0'}

    for router in (auth.router,lessons.router,documents.router,learning.router):
        app.include_router(router)

    if settings.mode=='demo':
        demo_dir=Path(__file__).parent/'demo'
        app.mount('/demo/assets',StaticFiles(directory=demo_dir),name='demo-assets')
        @app.get('/demo',include_in_schema=False)
        def demo():
            return FileResponse(demo_dir/'index.html')
        @app.get('/',include_in_schema=False)
        def root():
            return RedirectResponse('/demo')
    return app

app=create_app()
