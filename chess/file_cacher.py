import os,json
from typing import *

class Cache:
    def __init__(self, path: str, default_content: dict = {}, indent: int = 2, remake: bool = False):
        self.path = path
        self.default_content = default_content
        self.indent = indent

        if remake:
            open(self.path, 'w').write(json.dumps(self.default_content, indent=self.indent))


    def get_cache(self) -> dict:
        if not self.file_exists:
            open(self.path, 'w').write(json.dumps(self.default_content, indent=self.indent))
            return WatchableDict(self.default_content, indent=self.indent)

        return WatchableDict(json.loads(self.file_content), indent=self.indent)

    def get_file_content(self) -> str:
        if not self.file_exists:
            open(self.path, 'w').write(json.dumps(self.default_content, indent=self.indent))
            return json.dumps(self.default_content, indent=self.indent)

        return open(self.path, 'r').read()

    @property
    def cache(self) -> dict:
        return self.get_cache()

    @property
    def file_content(self) -> str:
        return self.get_file_content()

    def get(self, key, default_value=None):
        res = self.cache.get(key, default_value)
        if isinstance(res, dict):
            return WatchableDict(res, indent=self.indent)
        elif isinstance(res, dict):
            return WatchableDict(res, indent=self.indent)
        return res

    def set(self, content: Union[dict, str], as_json: bool = True):
        open(self.path, 'w').write(json.dumps(content, indent=self.indent) if as_json else content)

    def make_indent(self, value: Union[str, list, dict]) -> str:
        if isinstance(value, str):
            return json.dumps(json.loads(value), indent=self.indent)
        elif isinstance(value, (dict, list)):
            return json.dumps(value, indent=self.indent)
        return value

    @property
    def file_exists(self) -> bool:
        return os.path.isfile(self.path)

    def __call__(self) -> dict:
        return self.cache

    def __getitem__(self, key):
        if isinstance(key, tuple):
            last_key = None
            try:
                last_result = self.cache
                for k in key:
                    last_key = k
                    last_result = last_result[k]
                if isinstance(last_result, dict):
                    return WatchableDict(last_result, indent=self.indent)
                elif isinstance(last_result, list):
                    return WatchableList(last_result, indent=self.indent)
                else:
                    return last_result
            except IndexError:
                raise IndexError(last_key)
            except KeyError:
                raise KeyError(last_key)
        else:
            return WatchableDict(self.cache[key], indent=self.indent)
    def __setitem__(self, key, value):
        cache = self.cache
        if isinstance(key, tuple):
            str_key = [ (f'"{k}"' if isinstance(k, str) else str(k)) for k in key ]
            exec(f'cache[{ "][".join(str_key) }] = value')
        else:
            cache[key] = value
        self.set(cache)
    def __delitem__(self, key):
        cache = self.cache
        del cache[key]
        self.set(cache)

    def __str__(self):
        return self.file_content
    def __repr__(self):
        return f'{self.__class__.__name__}({self.path}, default_content={self.default_content})'

class WatchableDict(dict):
    def __init__(self, *args, indent: int = 2, **kwargs):
        super().__init__(*args, **kwargs)
        self.indent = indent
    def __str__(self):
        return json.dumps(self, indent=self.indent)

class WatchableList(list):
    def __init__(self, *args, indent: int = 2, **kwargs):
        super().__init__(*args, **kwargs)
        self.indent = indent
    def __str__(self):
        return json.dumps(self, indent=self.indent)