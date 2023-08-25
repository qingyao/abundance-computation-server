from aiohttp import web
import asyncio, os
import aiohttp_cors
from dotenv import load_dotenv

app_dir = 'computeAbundanceApp'

load_dotenv()

async def index(request):
    # Simple HTML page with JavaScript to open SSE connection
    return web.Response(text="""
        <html>
            <body>
                <script>
                    var eventSource = new EventSource("/stream");
                    eventSource.onmessage = function (event) {
                        console.log(event.data);
                    };
                </script>
            </body>
        </html>
    """, content_type='text/html')

async def stream(request):
    # Async generator to send server-side events
    # session_id = request.headers.get('X-Session-ID')
    session_id = request.rel_url.query.get('session_id')
    # print(session_id, 'here')
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/event-stream'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    
    print(request.headers['X-Forwarded-For'])
    # Start the response stream
    await response.prepare(request)
    try:
        while True:
            status = False
            await asyncio.sleep(1)
            # print("Alive..")
            message, status = check_session_progress(session_id)
            if status:
                break
            data = "data: "+message+"\n\n"
            # data = "data: 90\n\n"
            # Send data
            # data = "data: Hello, world!\n\n"
            await response.write(data.encode('utf-8'))
    except ConnectionResetError:
        # Handle client disconnection
        print("Client disconnected")
    except Exception as e:
        # Handle any other exceptions
        print(f"Encountered error: {e}")
    finally:
        response.headers['Connection'] = 'close'
        await response.write_eof()

    return response

    # async def event_stream():
    #     while True:
    #         await asyncio.sleep(1)
    #         check_session_progress(session_id)
    #         # yield b'data: Hello, world!\n\n'
    # return web.Response(body=event_stream(), content_type='text/event-stream')

def check_session_progress(session_id):
    in_dir = os.path.join(app_dir, 'user_upload', session_id, 'in')
    status_dir = os.path.join(app_dir, 'user_upload', session_id, 'status')

    submit_type_fpath = os.path.join(status_dir,'submit_type.txt')
    
    if os.path.isfile(submit_type_fpath):
        with open(submit_type_fpath) as f:
            submit_type = f.readline().strip()

        if submit_type == 'single':
            for i in os.listdir(status_dir):
                if os.path.splitext(i)[1]=='.status':
                    with open(os.path.join(status_dir,i)) as f:
                        message = f.readline().strip()
                        if message == '100%':
                            finished = True
                        else:
                            finished = False
                        return message, finished
            return "0%", False
                
        else:
            finished = set()
            if os.path.isfile(os.path.join(status_dir, 'status.all')):
                with open(os.path.join(status_dir, 'status.all')) as f:
                    for l in f:
                        finished.add(l.strip())
            total = len(os.listdir(in_dir))
            processed = len(finished)
            if processed < total:
                for i in os.listdir(status_dir):
                    if i.endswith('status') and not i in finished:
                        with open(os.path.join(status_dir,i)) as f:
                            percent = f.readline().strip()
                        
                        break
                else:
                    percent = '0%'
                total_fraction = (int(percent[:-1]) / 100 + processed) / total    
            else:
                total_fraction = 1
            
            message = str(round(total_fraction*100)) + '%,' +str(processed)+'/'+str(total)
            if total_fraction == 1:
                finished = True
            else:
                finished = False
            return message, finished
    else:
        return "0%", False
app = web.Application()
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
    )
})

cors.add(app.router.add_get('/sse/', index))
cors.add(app.router.add_get('/sse/stream/', stream))

web.run_app(app, port=os.getenv('SSE_PORT'))
