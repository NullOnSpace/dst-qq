import os
import sys
import logging
import collections
import functools
import zipfile
import io
import json

import redis

CWD = os.path.dirname(__file__)
sys.path.append(CWD)
from get_config import SCRIPT_FILE

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
logger.addHandler(logging.FileHandler("debug.log", mode="w"))

REDIS_TRANSLATIONS_PREPEND = "dst:translation:"


class LazyText(dict):
    ROOTS = {}

    def __new__(cls, msgctxt, *args, **kwargs):
        if "." not in msgctxt:
            if msgctxt in cls.ROOTS:
                logger.debug(f"existed root: {msgctxt}")
                return cls.ROOTS[msgctxt]
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, msgctxt, msgid=None, msgstr=None):
        if "." not in msgctxt:
            # root node
            self.ROOTS[msgctxt] = self
        self.msgctxt = msgctxt
        self.msgid = msgid
        self.msgstr = msgstr
        self.translated = False

    def __getattr__(self, name):
        logger.debug(f"enter getattr: {name}")
        if name in self:
            logger.debug(f"get {name} in {self} from attr")
            return self[name]
        else:
            logger.debug(f"create new key {name} for {self}")
            self[name] = LazyText(f"{self.msgctxt}.{name}")
            return self[name]
    
    def __str__(self):
        if not self.translated:
            self.translation()
        return self.msgid or self.msgctxt
    
    def __repr__(self):
        return f"_('{self.__str__()}')"
    
    def __add__(self, other):
        return str(self) + str(other)
    
    def __radd__(self, other):
        return str(self) + str(other)
    
    def translation(self):
        if "." not in self.msgctxt:
            self.translated = True
            return self.msgctxt
        R = redis.Redis()
        name, key = self.msgctxt.rsplit(".", maxsplit=1)
        value = R.hget(REDIS_TRANSLATIONS_PREPEND+name, key)
        if value:
            value_ = json.loads(value)
            msgid = value_["msgid"]
            msgstr = value_["msgstr"]
        else:
            with zipfile.ZipFile(SCRIPT_FILE) as zip:
                content = zip.read("scripts/languages/chinese_s.po")
            fp = io.StringIO(content.decode("utf8"))
            found = False
            msgid = ""
            msgstr = ""
            for idx, line in enumerate(fp, 1):
                if not line.strip():
                    continue
                if not (found or line.startswith("#.")):
                    continue
                if line.startswith("#."):
                    if line[3:].strip() == self.msgctxt:
                        found = True
                        continue
                if found:
                    if line.startswith("msgid"):
                        msgid = line[6:].strip()[1:-1]
                    if line.startswith("msgstr"):
                        msgstr = line[7:].strip()[1:-1]
                if msgid and msgstr:
                    break
        self.msgid = msgid
        self.msgstr = msgstr
        self.translated = True
    
    @classmethod
    def load_strings(cls):
        R = redis.Redis()
        with zipfile.ZipFile(SCRIPT_FILE) as zip:
            content = zip.read("scripts/languages/chinese_s.po")
        fp = io.StringIO(content.decode("utf8"))
        for idx, line in enumerate(fp, start=1):
            line = line.strip()
            if idx < 7:
                continue
            elif line == "":
                continue
            elif line.startswith("#"):
                continue
            else:
                if line.startswith("msgctxt"):
                    msgctxt = line.split(" ")[-1][1:-1]
                elif line.startswith("msgid"):
                    msgid = line.split(" ", maxsplit=1)[-1][1:-1]
                elif line.startswith("msgstr"):
                    msgstr = line.split(" ", maxsplit=1)[-1][1:-1]
                    name, key = msgctxt.rsplit(".", maxsplit=1)
                    value = json.dumps(dict(msgid=msgid, msgstr=msgstr))
                    R.hset(REDIS_TRANSLATIONS_PREPEND+name, key, value)
                    # parent = None
                    # for part in parts:
                    #     if parent is None:
                    #         parent = LazyText(part)
                    #     else:
                    #         parent = getattr(parent, part)
                    # parent.msgid = msgid
                    # parent.msgstr = msgstr
        R.close()


class LuaDict(collections.OrderedDict):
    def __getattr__(self, name):
        return self[name]
    
    def __repr__(self):
        return dict.__repr__(self)


class LuaList(list):
    def __setitem__(self, key, value):
        if key >= len(self):
            l = len(self)
            for i in range(l, key):
                self.append(None)
            self.append(value)
        else:
            super().__setitem__(key, value)


class Dummy:
    def __init__(self, *args, **kwargs) -> None:
        a = ",".join(map(lambda x: str(x), args))
        k = ",".join(map(lambda x, y: f"{x}={y}", kwargs.items()))
        self.name = f"({a},{k})"

    def __getattr__(self, name):
        return Dummy(self.name, name)
    
    def __call__(self, *args, **kwargs):
        return Dummy(self.name, *args, **kwargs)


class LUAParser:
    
    def __init__(self, global_={}):
        self.global_ = global_  # put variables in this
        self.if_stack = []  # record the if condition meets true or false
        self.for_stack = []  # every record is a list of statements of a for loop
        self.useless_end_counter = 0  # end is useless when context in if condition that dont meet True
        self.last_end_stack = []  # record the next end should be end of "if" or "for" 

    def parse_lua(self, lua_file, start_line=0, end_line=None, end_cond=lambda x: False):
        """:end_cond: a function takes line as arg and return T if needs end else False
        """
        not_complete = False  # True when need a } or ) in following lines to end
        block_comment = False
        partial = ""
        prepartial = ""
        for i, line in enumerate(lua_file):
            if block_comment:
                if line.strip().endswith("]]"):
                    block_comment = False
                continue
            if line.strip().startswith("--"):
                pass # comment but later take quoted "--" into account
                if line.strip().startswith("--[["):
                    block_comment = True
                continue
            if i < start_line:
                continue
            if (end_line and i > end_line) or end_cond(line):
                break
            line_comment_idx = line.find("--")
            if line_comment_idx != -1:
                # inline line comment
                line = line[:line_comment_idx]
            if line.strip().endswith(";"):
                line = line.strip()[:-1]+","
            if not_complete:
                partial = partial + line.strip()
                if "}" not in line and ")" not in line:
                    continue
                try:
                    fetch_end(partial)
                except LookupError:
                    continue
                else:
                    not_complete = False
                    line = prepartial + partial
            else:
                line = line.rstrip()
                if not line:
                    continue
                quoted = False
                not_complete = 0
                if line.endswith("="):
                    not_complete = True
                    prepartial = line
                    partial = ""
                    continue
                for idx, ch in enumerate(line):
                    if ch in ("'", '"') and not quoted:
                        q = ch
                        quoted = True
                    elif quoted and ch == q:
                        if not _is_backslashed(line[:idx]):
                            quoted = False
                    elif not quoted and ch in ("{", "("):
                        prepartial = line[:idx]
                        partial = line[idx:]
                        not_complete += 1
                    elif not quoted and ch in ("}", ")"):
                        not_complete -= 1
                else:
                    if not_complete:
                        continue
            self.parse_lua_line(line)

    def parse_lua_line(self, line):
        # assign, function call, or reserved word handling
        line = line.strip()
        s = line
        id_waiting = False
        stash = []
        while s:
            if self.for_stack and s != "end":
                logger.debug(f"ignore stmt:---{s}--- due to for")
                self.for_stack[-1].append(s)
                break
            if self.if_stack and self.if_stack[-1] is False:
                if s.startswith("if ") or s.startswith("for "):
                    self.useless_end_counter += 1
                    break
                elif s == "end" and self.useless_end_counter > 1:
                    self.useless_end_counter -= 1
                    break
                elif s != "end" and s != "else":
                    break
            value, type_, s = self.read_one_part(s)
            if type_ != "res":
                if value == "=":
                    v = self.explain(s)
                    self.assign_value(stash, v)
                    break
                else:
                    stash.append((value, type_))
            
    def assign_value(self, id_stash, value):
        # assign value to id_stash
        # id_stash be like [("a", "i"), ("['b']", "["), ...] means a['b']...
        if len(id_stash) == 1:
            id_ = id_stash[0][0]
            self.global_[id_] = value
        else:
            # parse to last but one property
            last_value, last_type = id_stash[-1]
            if last_type == "i":  # a.property = value 
                lbo = self.parse_identifier(list(zip(*id_stash[:-2]))[0])
                assert id_stash[-2][0] == ".", \
                        f"assign value property pattern wrong in {id_stash}"
                setattr(lbo, last_value, value)
            elif last_type == "[":  # a["item"] = value
                lbo = self.parse_identifier(list(zip(*id_stash[:-1]))[0])
                lbo[self.explain(last_value[1:-1])] = value
            else:
                # logging unknown pattern
                logger.debug(f"ERROR cant assign id_stash:{id_stash}")

    def read_one_part(self, s):
        # read a part and return this part, what is it and the rest
        logger.debug(f"read one part from: ---{s}---")
        s = s.strip()
        if s[0] in ("'", '"', "{", "[", "("):
            type_ = s[0]
            try:
                value = fetch_end(s) 
            except LookupError:
                # --an open bracket
                pass
            else:
                rest = s[len(value):]
        elif s[0].isidentifier():
            word, rest = read_a_word(s)
            if word in _LUA_KEYWORDS:
                value, rest = _LUA_KEYWORDS[word](rest, self)
                type_ = "res"  # res for reserved words 
            else:
                type_ = "i"  # i for identifier
                value = word
        elif s[0] in ("0123456789"):
            type_ = "n"  # n for numeric
            num = ""
            for n in s:
                if n in ("0123456789."):
                    num += n
                elif n == 'e':
                    num += 'e'
                elif n == '-' and num[-1] == 'e':
                    num += '-'
                else:
                    break
            rest = s[len(num):]
            if "." in num or 'e' in num:
                value = float(num)
            else:
                value = int(num)
        elif s[0] in ("+-*/"):
            if s[1] in ("+-=*/"):
                value = s[:2]
                rest = s[2:]
            else:
                value = s[0]
                rest = s[1:]
            type_ = "o"  # o for operater
        elif s[0] == "=" and s[1] != "=":
            value = "="
            rest = s[1:]
            type_ = "a"  # a for assignment
        elif s[0] in "<>~" or s[:2] == "==":
            if s[1] == "=":
                value = s[:2]
                rest = s[2:]
            else:
                value = s[0]
                rest = s[1:]
            type_ = "c"  # c for comparing
        elif s[0] == ".":
            if s[1] == ".":  # str concate
                value = ".."
                type_ = "con"  # con for str concate
                rest = s[2:]
            elif s[1] not in "1234567890":
                value = "."
                type_ = "."  # ask for property
                rest = s[1:]
            else:
                # .12 number
                num = ""
                for n in s[1:]:
                    if n in "0123456789":
                        num += n
                    elif n == 'e':
                        num += 'e'
                    elif n == '-' and num[-1] == 'e':
                        num += '-'
                    else:
                        break
                value = float("."+num)
                type_ = "n"
                rest = s[len(num)+1:]
        elif s[0] == ":":
            value = ":"
            type_ = "call"  # call a member function
            rest = s[1:]
        elif s[0] == ",":
            type_ = value = ","
            rest = s[1:]
        else:
            print(f"unparsed: {s}")
        return value, type_, rest
    
    def explain(self, s_):
        # parse an expression to value
        logger.debug(f"explaining: {s_}")
        s = s_.strip()
        parsed = []
        id_waiting = False
        while s:
            value, type_, s = self.read_one_part(s)
            logger.debug(f"explain parsing1: value:{value}, type:{type_}, s:{s}, id_waiting:{id_waiting}")
            # merge identifier and its call or prop or function or dict or list
            if id_waiting:
                if type_ in ".:[(i":
                    id_waiting.append(value)
                else:  # id_waiting ends, sth new comes
                    logger.debug(f"parsing id_waiting: {id_waiting}")
                    result = self.parse_identifier(id_waiting)
                    t = type(result)
                    if t is int or t is float:
                        parsed.append((result, "n"))
                    elif t is str:
                        parsed.append((result, "'"))
                    elif t is bool:
                        parsed.append((result, "TF"))  # TF for True or False
                    elif t is list:
                        parsed.append((result, "l"))  # l for list
                    else:
                        parsed.append((result, "v"))  # v for any value
                    id_waiting = False
                    parsed.append((value, type_))
            else:
                if type_ == "i":
                    id_waiting = [value,]
                else:
                    if type_ == "{":
                        value = self.parse_a_table(value)
                    elif type_ == "(":
                        value = self.explain(value[1:-1])
                    elif type_ in ("'", '"'):
                        value = value[1:-1]
                    parsed.append((value, type_))
            s = s.strip()
            logger.debug(f"explain parsing2: value:{value}, type:{type_}, s:{s}, id_waiting:{id_waiting}")
        else:
            if id_waiting:
                logger.debug(f"parsing id_waiting: {id_waiting}")
                result = self.parse_identifier(id_waiting)
                t = type(result)
                if t is int or t is float:
                    parsed.append((result, "n"))
                elif t is str:
                    parsed.append((result, "'"))
                elif t is bool:
                    parsed.append((result, "TF"))  # TF for True or False
                elif t is list:
                    parsed.append((result, "l"))  # l for list
                else:
                    parsed.append((result, "v"))  # v for any value
        logger.debug(f"explain parsed:---{parsed}---")
        op = None
        last_type = None
        last_obj = None
        current_value = None
        for part in parsed:
            v, t = part
            # handle
            if t in ("o", "con", "c"):
                op = v
            else:
                if current_value is None and op is None:
                    current_value = v
                else:
                    current_value = handle_op(op, current_value, v)
        return current_value

    def parse_a_table(self, table_str):
        # parse a table str into a dict or a list
        logger.debug(f"parsing table str: {table_str}")
        table_str = table_str.strip()[1:-1].strip()
        parts = []
        s = table_str
        if s:
            while s:
                value, type_, s = self.read_one_part(s)
                parts.append(value)
            logger.debug(f"parsing table str got parts:{parts}")
            if "=" in parts and \
                    not parts[parts.index("=")-1].strip("[] ").isdigit():
                # dict
                result = LuaDict()
                key = ""
                stash = []
                for part in parts:
                    if part == "=":
                        if len(part) > 1:
                            logger.debug(f"ERROR: unexpected len of table key: {stash}")
                            sys.exit(1)
                        else:
                            key = stash[0]
                            if key[0] == "[":
                                key = key[1:-1].strip()  # strip space after [ or before ]            
                                key = key[1:-1]  # strip " " or ' '
                            # if not key is an identifier which should be str in python
                            # in that case nothing need to be done
                        stash.clear()
                    elif part == ",":
                        value = self.explain("".join(map(lambda x: str(x), stash)))
                        result[key] = value
                        stash.clear()
                        key = ""
                    else:
                        stash.append(part)
                else:
                    if key:
                        value = self.explain("".join(map(lambda x: str(x), stash)))
                        result[key] = value
            else:  # array
                result = LuaList()
                stash = []
                idx = None
                for part in parts:
                    if type(part) is not str or part not in  ",=":
                        stash.append(part)
                    elif part == "=":
                        assert len(stash) == 1, f"{stash} not in [d] mode"
                        idx = int(stash[0].strip("[]"))
                        stash.clear()
                    else: # , condition
                        v = self.explain("".join(map(lambda x: str(x), stash)))
                        if idx:
                            result[idx-1] = v
                            idx = None
                        else:
                            result.append(v)
                        stash.clear()
                else:
                    if stash:
                        v = self.explain("".join(map(lambda x: str(x), stash)))
                        if idx:
                            result[idx-1] = v
                            idx = None
                        else:
                            result.append(v)
            return result
        else:  # empty list
            return LuaList()

    def parse_identifier(self, id_list):
        # parse an identifier and the following into value
        # be like ["a", "['b']", ".", "c", ":", "d", "()"] "a[b].c:d()"
        logger.debug(f"parse identifiers {id_list}")
        value = None
        op = None
        for id_ in id_list:
            if id_[0] in ".:":
                op = id_
            elif id_[0] == "[":  # table or array
                value = value[self.explain(id_[1:-1])]
            elif id_[0] == "(":
                args, kwds = self.parse_arguements(id_[1:-1])
                value = value(*args, **kwds)
            else:  # identifier
                if op is None:  # the first identifier
                    value = self.get_value(id_)
                else:  # op will be either "." or ":"
                    value = getattr(value, id_)
        logger.debug(f"parse --{id_list}-- into: --{value}--")
        return value
    

    def get_value(self, s):
        # return s identifier's value follow LEGB rules
        return self.global_[s]
                        
    def parse_arguements(self, s):
        # parse s into args and kwargs
        if s.strip().startswith("{"):
            value = self.explain(s)
            args = [value,]
            kwargs = {}
            return args, kwargs
        unparsed_args = s.split(",")
        args = []
        kwargs = {}
        for arg in unparsed_args:
            if "=" in arg:
                k, v = arg.split("=")
                value = self.explain(v)
                kwargs[k] = v
            else:
                value = self.explain(arg)
                args.append(value)
        return args, kwargs


class PseudoFunctions:
    fns = []

    def __init__(self, fn_name):
        self.fn_name = fn_name
        self.records = []
        self.fns.append(self)

    def __call__(self, *args, **kwds):
        result = self.run(*args, **kwds)
        record = (args, kwds, result)
        self.records.append(record)
        return result
    
    def run(self, *args, **kwds):
        return f"run fn {self.fn_name} with args:{args}, kwargs:{kwds}"
    

# keyword handlers
def _if_handler(s, lp: LUAParser):
    s.strip()
    T_or_F = bool(lp.explain(s[:-4]))
    lp.if_stack.append(T_or_F)
    lp.last_end_stack.append("if")
    return None, ""

def _then_handler(s, lp):
    return None, ""

def _else_handler(s, lp):
    lp.if_stack[-1] = not lp.if_stack[-1]
    return None, ""

def _end_handler(s, lp: LUAParser):
    # ignore for loop for now
    last_end = lp.last_end_stack.pop()
    if last_end == "if":
        lp.if_stack.pop()
    elif last_end == "for":
        statements = lp.for_stack.pop()
        _for_statements(statements, lp)
    return None, ""

def _for_statements(statements, lp: LUAParser):
    for_stmt = statements[0]
    stmt = for_stmt.strip()
    var_stash = []
    iter_stash = []
    current = "var"
    while stmt:
        v, t, stmt = lp.read_one_part(stmt)
        if current == "var" and t == "i":
            var_stash.append(v)
        elif current == "var" and t == "res":  # 'in' keyword
            current = "iter"
        elif current == "iter" and t != "res":  # iter part
            iter_stash.append(v)
        logger.debug(f"useless word in for stmt {v}")
        # rest are 'do' keyword and ',' between vars
    iter_ = lp.parse_identifier(iter_stash)
    # handle for loop
    for value in iter_:
        # param initialize
        logger.debug(f"assign {value} to {var_stash}")
        for i, v in enumerate(var_stash):
            lp.global_[v] = value[i]
            logger.debug(f"initialize param:{v} with value: {value[i]}")
        for stmt in statements[1:]:
            lp.parse_lua_line(stmt)


def _local_handler(s, lp):
    _local = lp.global_
    try:
        var, expr_ = s.split("=", maxsplit=1)
    except ValueError:  # statement not assignment
        var = s
        value = None
    else:
        value = lp.explain(expr_)
    var = var.strip()
    _local[var] = value
    return None, ""

def _for_handler(s, lp: LUAParser):
    lp.last_end_stack.append("for")
    lp.for_stack.append([s])
    return None, ""

def _in_handler(s, lp: LUAParser):
    return None, s

def _assert_handler(s, lp):
    return None, ""

def _do_handler(s, lp):
    return None, ""

def _return_handler(s, lp):
    lp.global_['__rt'] = lp.explain(s)
    return None, ""

def _function_handler(s, lp):
    return None, ""


_LUA_KEYWORDS = {
    'if': _if_handler,
    'then': _then_handler,
    'else': _else_handler,
    'end': _end_handler,
    'local': _local_handler,
    'for': _for_handler,
    'in': _in_handler,
    'assert': _assert_handler,
    'do': _do_handler,
    'return': _return_handler,
    'function': _function_handler,
}


def fetch_end(s):
    """after meeting '{', '"', "'", "(", find the matching one 
    and return the content and its wrapping
    """
    logger.debug(f"fetch end for {s[:6]}...{s[-6:]}:{len(s)}chars {s.count(chr(10))}lines")
    bracket_dict = { "{": "}", "(": ")", "[": "]"}
    start = s[0]
    rest = s[1:]
    if start in bracket_dict.keys():
        end = bracket_dict[start]
        in_quote = False
        bracket_count = 0
        chs = start
        backslash = False
        for ch in rest:
            if ch == "\\" and backslash == False:
                backslash = True
                chs += ch
                continue
            if ch in ('"', "'") and backslash is False:
                if not in_quote:
                    in_quote = ch
                elif ch == in_quote:
                    in_quote = False
            elif ch == end and not in_quote:
                if bracket_count:
                    bracket_count -= 1
                else:
                    chs += ch
                    return chs
            elif ch == start and not in_quote:
                bracket_count += 1
            chs += ch
            backslash = False
        else:
            raise LookupError(f"No match sign in given str: {s}")
    elif start in ("'", '"'):
        pos = rest.find(start)
        while True:
            if pos == 0:
                return '""'
            elif rest[pos-1] != "\\":
                return start + rest[:pos+1]
            else:
                pos = rest[pos+1:].find(start)
                if pos == -1:
                    raise LookupError(f"No match sign in given str: {s}")
    else:
        raise ValueError(f"wrong start to find a match: {s[:5]}...")


def is_end(line):
    opened = False
    # first strip all quoted str
    while True:
        for ch in line:
            if ch in ('"', "'"):
                idx1 = line.find(ch)
                rest = line[idx1+1:]
                idx2 = rest.find(ch)
                while True:
                    if _is_backslashed(rest[:idx2]):
                        rest_ = rest[idx2+1:]
                        idx2 = rest_.find(ch) + idx2 + 1
                    else:
                        break
                line = line[:idx1] + line[idx1+idx2+2:]
                break
        else:
            break
    closed = 0
    for ch in line:
        if ch in ("{", "("):
            closed += 1
        elif ch in ("}", ")"):
            closed -= 1
    return not closed


def _is_backslashed(line):
    if (len(line) - len(line.rstrip("\\")))%2 == 0:
        return False
    else:
        return True
    

def read_a_word(s):
    """fetch a word from given s and return the word and rest part
    it has been confirmed it start with a letter or underscore
    """
    if s and not s[0].isidentifier():
        raise TypeError(f"given str: {s} not start with proper char: {s[0]}")
    chs = ""
    for i, ch in enumerate(s):
        chs += ch
        if not chs.isidentifier():
            break
    else:
        # all string scanned so whole as identifier and the rest is empty
        i = i + 1
    return s[:i], s[i:]


def handle_op(op, v1, v2):
    if op == "+":
        return v1 + v2
    elif op == "-":
        if v1 is not None:
            return v1 - v2
        else:
            return -v2
    elif op == "*":
        return v1 * v2
    elif op == "/":
        return v1 / v2
    elif op == "..":
        return v1 + v2
    elif op == ">":
        return v1 > v2
    elif op == "<":
        return v1 < v2
    elif op == ">=":
        return v1 >= v2
    elif op == "<=":
        return v1 <= v2
    elif op == "==":
        return v1 == v2
    elif op == "~=":
        return v1 != v2


def LUA_dump(obj, ident=2, pre_ident=0):
    """dump py obj to lua string
    and transform into pprint format
    :ident: spaces that should be add when in sub level
    :pre_ident: ident level that subclass from pre class
    """
    cr_nl = "\n" + " "*(ident*(pre_ident+1))
    if issubclass(type(obj), dict):
        # dump a dict
        output = ["{",]
        nextline = False
        for k, v in obj.items():
            part1 = f"['{k}'] = "
            part2 = LUA_dump(v, pre_ident=pre_ident+1)
            part = part1 + part2 + ","
            output.append(part)
        output.append("}")
        no_nl_result = functools.reduce(str.__add__, output)
        if len(no_nl_result) > 48:
            result = cr_nl.join(output)
        else:
            result = no_nl_result
    elif issubclass(type(obj), list):
        # dump a list
        output = ["{",]
        for item in obj:
            part = LUA_dump(item, pre_ident=pre_ident+1) + ","
            output.append(part)
        output.append("}")
        no_nl_result = functools.reduce(str.__add__, output)
        if len(no_nl_result) > 48:
            result = cr_nl.join(output)
        else:
            result = no_nl_result
    elif obj is None:
        result = "nil"
    elif obj is True or obj is False:
        result = str(obj).lower()
    else:
        # dump str, num
        result = repr(obj)
    return result


_IsNotConsole = PseudoFunctions("IsConsole")
_IsNotConsole.run = lambda x: True
_IsPS4 = PseudoFunctions("IsPS4")
_IsPS4.run = lambda x: False

LUA_BUILTINS = {
    "require": Dummy("require"),
    "STRINGS": LazyText("STRINGS"),
    "IsNotConsole": _IsNotConsole,
    "IsPS4": _IsPS4,
    "ipairs": enumerate,
    'nil': None,
    'true': True,
    'false': False,
}

def main():
    line = "{{x=560,z=-40}}"
    lp = LUAParser(global_=LUA_BUILTINS)
    print(lp.explain(line))


if __name__ == "__main__":
    with open(os.path.join(CWD, "temp/0000000038")) as fp:
        lp = LUAParser(global_=LUA_BUILTINS)
        lp.parse_lua(fp)
        print(lp.global_['__rt'])