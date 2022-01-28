import asyncio
import settings

async def clean_chat(app):
    while True:
        await asyncio.sleep(10)
        print('Chat janitor is working! ')
        for group_id,group_info in app['chat'].items():
            remove_items_count = len(group_info['events'])-settings.MAX_MESSAGE_TO_STORE
            for i in range(remove_items_count):
                item = app['chat'][group_id]['events'].pop(0)
                print(f'Event {item} was removed from the group {group_id}')