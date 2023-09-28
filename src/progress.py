import asyncio
import tqdm.asyncio as tqdm_async
import logging

from typing import Iterable, List

logger = logging.getLogger(__name__)

async def async_execute_tasks_with_progressbar(tasks: Iterable[asyncio.Task], skip_errors: bool = False, **kwargs) -> List[any]:
    results = []
    for task in tqdm_async.tqdm.as_completed(tasks, bar_format='{l_bar}{bar:10}{r_bar}{bar:-10b}', **kwargs):
        try:
            task_result = await task
        except:
            logger.warning(f'Got error during executing tasks. {f"This error was skipped" if skip_errors else ""}')
            logging.exception('Error during executing tasks')
            if not skip_errors:
                raise
            continue
        if task_result:
            results.append(task_result)
    return results
