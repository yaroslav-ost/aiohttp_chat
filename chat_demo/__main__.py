import asyncio
import logging
import utils
from aiohttp import web

from chat_demo import views


async def init_app():
    app = web.Application()
    app.on_startup.append(start_clean_chat_task)
    app.on_cleanup.append(stop_clean_chat_task)
    app['chat'] = {}
    app.router.add_get('/chat', views.chat)
    return app


async def start_clean_chat_task(app):
    app['chat_cleaner'] = asyncio.create_task(utils.clean_chat(app))


async def stop_clean_chat_task(app):
    app['chat_cleaner'].cancel()
    await app['chat_cleaner']


def main():
    logging.basicConfig(level=logging.DEBUG)
    app = init_app()
    web.run_app(app)


if __name__ == '__main__':
    main()
