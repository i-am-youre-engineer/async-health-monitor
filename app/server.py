import asyncio
import utils
import multiprocessing
from logger import default_logger
from scheduler import Scheduler

async def handle_client(reader, writer):
    request_data = await reader.read(1024)
    request = utils.Request(request_data)
    response = utils.Response(request)
    writer.write(response.data)
    await writer.drain()
    writer.close()
    await writer.wait_closed()

    level = "INFO" if 200 <= response.status_code < 400 else "WARNING" if response.status_code < 500 else "ERROR"
    msg = f"{request.method} {request.path} -> {response.status_code}"
    getattr(default_logger, level.lower())(msg)

async def main(host:str='0.0.0.0', port:int=8080):
    scheduler_proc = multiprocessing.Process(
        target=start_scheduler_process,
        daemon=True
    )
    scheduler_proc.start()

    server = await asyncio.start_server(handle_client, host, port)
    addr = server.sockets[0].getsockname()
    default_logger.info(f"START SERVER {addr} -> OK")

    async with server:
        await server.serve_forever()

def start_scheduler_process():
    """Entry point for the scheduler daemon process."""
    s = Scheduler()
    s.run_forever()

if __name__ == '__main__':
    import logger
    config = utils.Config()

    logger.default_logger.log_file = config.server['server_log']
    utils.test_load_processor(config.processors, config.server['run_with_error'])

    asyncio.run(
        main(
            host=config.server.get('host'),
            port=config.server.get('port'),
        )
    )