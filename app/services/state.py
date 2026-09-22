import ast
import copy
import json
import os
import threading
from abc import ABC, abstractmethod

from loguru import logger

from app.config import config
from app.models import const
from app.utils import utils


_PATCH_EXISTING_TASK_SCRIPT = """
if redis.call("EXISTS", KEYS[1]) == 0 then
    return 0
end

for index = 1, #ARGV, 2 do
    redis.call("HSET", KEYS[1], ARGV[index], ARGV[index + 1])
end

return 1
"""


# Base class for state management
class BaseState(ABC):
    @abstractmethod
    def update_task(self, task_id: str, state: int, progress: int = 0, **kwargs):
        pass

    @abstractmethod
    def get_task(self, task_id: str):
        pass

    @abstractmethod
    def get_all_tasks(self, page: int, page_size: int):
        pass

    @abstractmethod
    def patch_task(self, task_id: str, **kwargs) -> bool:
        """只更新已有任务的指定字段；任务不存在时返回 False。"""
        pass


# Memory state management with Disk Persistence
class MemoryState(BaseState):
    def __init__(self):
        self._tasks = {}
        self._lock = threading.RLock()
        self._load_from_disk()

    def _state_file(self) -> str:
        s_dir = utils.storage_dir(create=True)
        return os.path.join(s_dir, "tasks_state.json")

    def _persist_to_disk(self):
        try:
            s_file = self._state_file()
            temp_path = s_file + ".tmp"
            os.makedirs(os.path.dirname(s_file), exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._tasks, f, ensure_ascii=False, indent=2, default=str)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, s_file)
        except Exception as exc:
            logger.warning(f"failed to persist tasks_state.json: {exc}")

    def _load_from_disk(self):
        with self._lock:
            # 1. Load from tasks_state.json if available
            try:
                s_file = self._state_file()
                if os.path.isfile(s_file):
                    with open(s_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            self._tasks.update(data)
            except Exception as exc:
                logger.warning(f"failed to load tasks_state.json: {exc}")

            # 2. Reconstruct from task directories in storage/tasks
            try:
                tasks_root = utils.task_dir()
                if os.path.isdir(tasks_root):
                    for entry in os.scandir(tasks_root):
                        if entry.is_dir() and not entry.name.startswith("."):
                            tid = entry.name
                            if tid not in self._tasks:
                                t_state_file = os.path.join(entry.path, "task_state.json")
                                if os.path.isfile(t_state_file):
                                    try:
                                        with open(t_state_file, "r", encoding="utf-8") as tf:
                                            self._tasks[tid] = json.load(tf)
                                            continue
                                    except Exception:
                                        pass

                                script_file = os.path.join(entry.path, "script.json")
                                script_data = {}
                                if os.path.isfile(script_file):
                                    try:
                                        with open(script_file, "r", encoding="utf-8") as sf:
                                            script_data = json.load(sf)
                                    except Exception:
                                        pass

                                videos = []
                                for fn in os.listdir(entry.path):
                                    if fn.startswith("final-") and fn.endswith((".mp4", ".mov", ".mkv")):
                                        videos.append(os.path.join(entry.path, fn))

                                if videos:
                                    videos.sort()
                                    params_dict = script_data.get("params", {})
                                    subject = (
                                        params_dict.get("video_subject")
                                        or script_data.get("script", "")[:40]
                                        or tid
                                    )
                                    self._tasks[tid] = {
                                        "task_id": tid,
                                        "state": const.TASK_STATE_COMPLETE,
                                        "progress": 100,
                                        "videos": videos,
                                        "video_subject": subject,
                                        "script": script_data.get("script", ""),
                                        "mtime": entry.stat().st_mtime,
                                    }
            except Exception as exc:
                logger.warning(f"failed to scan task storage for recovery: {exc}")

    def get_all_tasks(self, page: int, page_size: int):
        start = (page - 1) * page_size
        end = start + page_size
        with self._lock:
            # Sort by mtime descending (newest first)
            tasks = [copy.deepcopy(task) for task in self._tasks.values()]
            tasks.sort(
                key=lambda t: float(t.get("mtime", 0) or t.get("updated_at", 0) or 0),
                reverse=True,
            )
            total = len(tasks)
        return tasks[start:end], total

    def update_task(
        self,
        task_id: str,
        state: int = const.TASK_STATE_PROCESSING,
        progress: int = 0,
        **kwargs,
    ):
        progress = int(progress)
        if progress > 100:
            progress = 100

        with self._lock:
            existing = self._tasks.get(task_id, {})
            task_dict = {
                **existing,
                "task_id": task_id,
                "state": state,
                "progress": progress,
                **copy.deepcopy(kwargs),
            }
            import time
            if "mtime" not in task_dict:
                task_dict["mtime"] = time.time()
            self._tasks[task_id] = task_dict

            try:
                tdir = utils.task_dir(task_id)
                t_state_file = os.path.join(tdir, "task_state.json")
                temp_tf = t_state_file + ".tmp"
                with open(temp_tf, "w", encoding="utf-8") as tf:
                    json.dump(task_dict, tf, ensure_ascii=False, indent=2, default=str)
                    tf.flush()
                    os.fsync(tf.fileno())
                os.replace(temp_tf, t_state_file)
            except Exception:
                pass

            self._persist_to_disk()

    def get_task(self, task_id: str):
        with self._lock:
            task = self._tasks.get(task_id, None)
            return copy.deepcopy(task) if task is not None else None

    def patch_task(self, task_id: str, **kwargs) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.update(copy.deepcopy(kwargs))

            try:
                tdir = utils.task_dir(task_id)
                t_state_file = os.path.join(tdir, "task_state.json")
                temp_tf = t_state_file + ".tmp"
                with open(temp_tf, "w", encoding="utf-8") as tf:
                    json.dump(task, tf, ensure_ascii=False, indent=2, default=str)
                    tf.flush()
                    os.fsync(tf.fileno())
                os.replace(temp_tf, t_state_file)
            except Exception:
                pass

            self._persist_to_disk()
            return True

    def delete_task(self, task_id: str):
        with self._lock:
            self._tasks.pop(task_id, None)
            self._persist_to_disk()


# Redis state management
class RedisState(BaseState):
    """
    Redis-backed task state.

    Trust boundary: Redis is expected to be private to this application. Task
    values are written by MoneyPrinterTurbo and converted back from strings for
    compatibility with existing state records. Do not expose this Redis database
    to untrusted writers without replacing deserialization with a stricter
    schema-based format.
    """

    def __init__(self, host="localhost", port=6379, db=0, password=None):
        import redis

        self._redis = redis.StrictRedis(host=host, port=port, db=db, password=password)

    def get_all_tasks(self, page: int, page_size: int):
        start = (page - 1) * page_size
        end = start + page_size
        tasks = []
        cursor = 0
        total = 0
        while True:
            # Redis 数据库中除了任务 Hash，还可能存在 RedisTaskManager 使用的
            # List 队列。只扫描 Hash 可以避免对队列执行 HGETALL 时触发
            # WRONGTYPE，同时保证 total 只统计真正的任务记录。
            cursor, keys = self._redis.scan(
                cursor,
                count=page_size,
                _type="HASH",
            )
            batch_start = total
            batch_size = len(keys)
            total += batch_size

            # Redis SCAN 是分批返回 key。分页切片必须基于“当前批次起始索引”
            # 计算，而不能用累积后的 total 反推，否则第一页会切到空数组，
            # 第二页也可能只返回部分数据。
            if batch_start < end and total > start:
                slice_start = max(0, start - batch_start)
                slice_end = min(batch_size, end - batch_start)
                for key in keys[slice_start:slice_end]:
                    task_data = self._redis.hgetall(key)
                    task = {
                        k.decode("utf-8"): self._convert_to_original_type(v)
                        for k, v in task_data.items()
                    }
                    tasks.append(task)

            # 即使当前页已经取满，也要继续 SCAN 到 cursor=0，
            # 因为调用方需要准确 total 来渲染分页信息。
            if cursor == 0:
                break
        return tasks, total

    def update_task(
        self,
        task_id: str,
        state: int = const.TASK_STATE_PROCESSING,
        progress: int = 0,
        **kwargs,
    ):
        progress = int(progress)
        if progress > 100:
            progress = 100

        fields = {
            "task_id": task_id,
            "state": state,
            "progress": progress,
            **kwargs,
        }

        for field, value in fields.items():
            self._redis.hset(task_id, field, str(value))

    def get_task(self, task_id: str):
        task_data = self._redis.hgetall(task_id)
        if not task_data:
            return None

        task = {
            key.decode("utf-8"): self._convert_to_original_type(value)
            for key, value in task_data.items()
        }
        return task

    def patch_task(self, task_id: str, **kwargs) -> bool:
        if not kwargs:
            return False

        arguments = []
        for field, value in kwargs.items():
            arguments.extend((field, str(value)))

        # EXISTS 和 HSET 如果分成两条命令，后台发布线程与删除请求并发时，
        # HSET 可能在删除后重新创建一条残缺任务。Lua 脚本由 Redis 原子执行，
        # 可以保证任务不存在时不写入，且不会改变现有字段之外的数据。
        updated = self._redis.eval(
            _PATCH_EXISTING_TASK_SCRIPT,
            1,
            task_id,
            *arguments,
        )
        return bool(updated)

    def delete_task(self, task_id: str):
        self._redis.delete(task_id)

    @staticmethod
    def _convert_to_original_type(value):
        """
        Convert values written by this application back to common Python types.

        This compatibility parser assumes Redis is inside the application's
        trust boundary. If Redis can be written by untrusted clients, task state
        should move to a strict JSON/schema parser instead of open-ended literal
        conversion.
        """
        value_str = value.decode("utf-8")

        try:
            # try to convert byte string array to list
            return ast.literal_eval(value_str)
        except (ValueError, SyntaxError):
            pass

        if value_str.isdigit():
            return int(value_str)
        # Add more conversions here if needed
        return value_str


# Global state
_enable_redis = config.app.get("enable_redis", False)
_redis_host = config.app.get("redis_host", "localhost")
_redis_port = config.app.get("redis_port", 6379)
_redis_db = config.app.get("redis_db", 0)
_redis_password = config.app.get("redis_password", None)

state = (
    RedisState(
        host=_redis_host, port=_redis_port, db=_redis_db, password=_redis_password
    )
    if _enable_redis
    else MemoryState()
)
