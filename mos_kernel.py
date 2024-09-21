#!/usr/bin/env python3

"""
KERNEL FOR MOS (My OS)
This is ofc a mock operating system!

p - planned
c - completed
i - in progress
o - getting optimized
P - postponed
x - canceled

Features:
c : Event handler
i : File system
p : Network
p : Multiple users
p : Window system using ncurses (graphics mode)

Naming convention for events:
  process = p_[name]
    Runs on threads.
  Event   = e_[name]
    Runs on the main thread.
    Useful when writing to files.
  cleaner = c_[process name]
    Useful when finalizing changes to files or
    for cleaning up hence the name.

  Example:
    def p_auto_save(handler):
        def c_auto_save(handler):
            ...
        handler.add_cleaner(c_auto_save)
        while handler.safe():
            ...
"""

# Imports (USE SEPARATE LINES)

import threading
import traceback
import datetime
import random
import atexit
import inspect

# Unrooted settings

SafeDict = {}

# Setup for the module

__all__ = []

def export(obj):
    if not hasattr(obj, "__name__"):
        print("   [INFO]: Export failed!")
        return
    __all__.append(obj.__name__)
    SafeDict[obj.__name__] = obj
    return obj

def exportAs(name):
    def f(obj):
        if name in globals():
            print(f"[WARNING]: While exporting object id({hex(id(obj))}) as {name!r}, the name was already used and thus this operation is aborted.")
        else:
            globals()[name] = obj
        __all__.append(name)
        SafeDict[name] = obj
        return obj
    return f

# Metaclasses

@export # for user convinience
class ReadOnly(type):
    def __setattr__(self, name, value):
        raise AttributeError(f"{self.__name__} is read only!")

# Events

GLOBAL_STOP = threading.Event()

def mk_event(self=type("object", (object,), {"verbose":True, "safe":lambda self: (not GLOBAL_STOP.is_set()), "g_safe":lambda self: (not GLOBAL_STOP.is_set())})(), args=tuple()):
    def f(event):
        def new_event():
            current_id = eventHandler.th_id
            if self.verbose:
                print(f"   [INFO]: Started event ({getattr(event, '__name__', repr(event))} [{current_id}])")
            try:
                event(self, *args)
            except:
                print(traceback.format_exc()+f"\n  [ERROR]: Error in event ({getattr(event, '__name__', repr(event))} [{current_id}])")
            if self.verbose:
                print(f"   [INFO]: Event ({getattr(event, '__name__', repr(event))} [{current_id}]) has finished.")
        new_event
        return new_event
    return f

def mk_event_cleaner(self=type("object", (object,), {"verbose":True, "safe":lambda self: (not GLOBAL_STOP.is_set()), "g_safe":lambda self: (not GLOBAL_STOP.is_set())})(), args=tuple()):
    def f(event):
        def new_event():
            if self.verbose:
                print(f"   [INFO]: Started event ({getattr(event, '__name__', repr(event))})")
            try:
                event(self, *args)
            except:
                print(traceback.format_exc()+f"\n  [ERROR]: Error in event ({getattr(event, '__name__', repr(event))})")
            if self.verbose:
                print(f"   [INFO]: Event ({getattr(event, '__name__', repr(event))}) has finished.")
        new_event
        return new_event
    return f

@export
class eventHandler:
    th_id = 0
    def __init__(self, lock=None, verbose=False):
        self.events = []
        self.verbose = verbose
        self.threads = []
        self.cleaners = []
        self._add_lock = threading.Lock()
        self._lock = lock if lock is not None else threading.Event()
        self.safe = lambda: not (self._lock.is_set() or GLOBAL_STOP.is_set())
        self.g_safe = lambda: not GLOBAL_STOP.is_set()
        if verbose:
            print(f"   [INFO]: Made new handler: id {hex(id(self))}")
    def add_event(self, event, thread=False, args=tuple()):
        with self._add_lock:
            self.events.append((thread, event, args))
    def run_events(self):
        while self.events:
            is_th, event, args = self.events.pop(0)
            new_event = mk_event(self, (eventHandler.th_id, *args))(event)
            if is_th:
                th = threading.Thread(target=new_event)
                th.daemon = True
                self.threads.append(th)
                th.start()
                with self._add_lock:
                    eventHandler.th_id += 1
            else:
                new_event()
    def add_cleaner(self, function):
        new_fn = mk_event_cleaner(self, ("cleanup",))(function)
        with self._add_lock:
            self.cleaners.append(new_fn)
    def stop(self):
        self._lock.set()
        for i in self.threads:
            i.join()
        for i in self.cleaners:
            i()
    def clear(self): # Reset the handler EXCEPT THE THREAD IDS
        with self._add_lock:
            self.threads.clear()
            self.cleaners.clear()
            self._lock.clear()

## Setup

KERNEL_HANDLER = eventHandler(verbose=True)

# Deinit!

## Needs root to be accessed by other programs
def FULL_STOP():
    "Boot off"
    GLOBAL_STOP.set()
    KERNEL_HANDLER.stop()
    print("   [INFO]: Kernel has finnished killing processes.")

def BOOT_OFF():
    FULL_STOP()
    atexit.unregister(FULL_STOP)
    raise SystemExit("Boot off.")

## Setup for the kernel

atexit.register(FULL_STOP)

# Date shenanigins

@export
def getDate():
    return datetime.datetime.now()

@export
def getDateString():
    return str(getDate())

# File system shenanigins

@export
class block:
    def __init__(self, data):
        self.data = data
    def read(self):
        return self.data
    def write(self, data):
        self.data = data
    def __repr__(self):
        return repr(self.data)

@export
class File(block):
    def __init__(self, name, content=""):
        super().__init__({
            "name":name,
            "content":content,
            "made-on":getDateString()
        })
        self.writeLock = threading.Lock() # prevent race conditions
    def read(self):
        return self.data["content"]
    def write(self, content):
        with self.writeLock:
            self.data["content"] = content
    def append(self, content):
        with self.writeLock:
            self.data["content"] += content
    def get_obj(self):
        return self.data
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return

@export
class Directory(block):
    def __init__(self, name):
        super().__init__({
            "name":name,
            "content":{},
            "made-on":getDateString()
        })
        self.writeLock = threading.Lock() # prevent race conditions
    def add_file(self, name, content):
        with self.writeLock:
            self.data["content"][name] = content
    def rem_file(self, name, content):
        with self.writeLock:
            if name in self.data["content"]:
                self.data["content"].pop(name)
            else:
                print(" [ERROR]: File does not exist!")
    def read(self, name):
        if name in self.data["content"]:
            print(" [ERROR]: File does not exist!")
            return
        return self.data["content"][name].read()
    def write(self, name, content):
        if name in self.data["content"]:
            print(" [ERROR]: File does not exist!")
            return
        with self.writeLock:
            self.data["content"][name].write(content)
    def append(self, name, content):
        if name in self.data["content"]:
            print(" [ERROR]: File does not exist!")
            return
        with self.writeLock:
            self.data["content"][name].append(content)
    def get_obj(self):
        return self.data
    def contents(self):
        return list(self.data["content"].keys())
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return

# Wrapper

@export
class askRoot:
    def __init__(self, name="[program]"):
        self.asdict = globals()
        self.kernel = type("KernelObject", (object,), self.asdict)
        op1 = random.randint(1, 10)
        op2 = random.randint(1, 10)
        math = random.choice("*+-")
        problem = f"{op1} {math} {op2}"
        key = eval(problem, {"__builtins__":{}}) # maybe switch to a more secure one
        if input(f"By entering the answer to '{problem}' you hereby grant {name!r} direct access to the kernel.\nEnter key to proceed: ") != str(key):
            raise KernelExceptions.PermissionError("Access was denied!")
        else:
            if KernelSettings.askSecondaryPrompt:
                key = random.randint(1000, 9999)
                if input(f"By entering the key '{key}' you hereby grant {name!r} direct access to the kernel.\nEnter key to proceed: ") != str(key):
                    raise Kernel.PermissionError("Access was denied!")
            print(f"Access granted to {name!r}")
    def getKernel(self): # looks cooler when you chain calls :)
        return self.kernel

# Constants and Exceptions

@export
class KernelSettings(metaclass=ReadOnly):
    askSecondaryPrompt = True

class KernelExceptions(metaclass=ReadOnly):
    class PermissionError(Exception): "Errors that occur when a process or an action was not permitted by the kernel to provide or to ensure secure access to importanr resources."
    class FatalError(Exception): "Errors that occur when the kernel it self has an error that it cannot resolve and cannot recover from such as data fragmentarion or a segmentarion fault of one of the core processes."
    class CascadeError(Exception): "Rare errors that happen when a process or program crashes and it causes other processes or programs to crash. Hence the name cascade."
    class ThreadError(Exception): "Errors that happen when a thread is misset to a non daemon thread and doesnt stop on boot off. (th.deamon = False)"
    class BootError(Exception): "Oh boy youre in for a ride."

@export
class KernelControlExceptions:
    class ExitSig(Exception): "When a process wants to kill it self."

# Running applications

@export
def unrootedExec(code, data=None, verbose=False):
    data = data if data is not None else {}
    data.update(SafeDict)
    try:
        exec(compile(code, "file", "exec"), data)
        return False
    except KernelControlExceptions.ExitSig:
        return False
    except SystemExit:
        raise
    except KeyboardError:
        print("[Job stopped]")
        return False
    except:
        print(traceback.format_exc()+f"\n  [ERROR]: Error while running application!")
        return True

def rootedExec(code, data=None, verbose=False):
    data = data if data is not None else {}
    data.update(askRoot("Application").asdict)
    try:
        exec(compile(code, "file", "exec"), data)
        return False
    except KernelControlExceptions.ExitSig:
        return False
    except SystemExit:
        raise
    except KeyboardError:
        print("[Job stopped]")
        return False
    except:
        print(traceback.format_exc()+f"\n  [ERROR]: Error while running application!")
        return True

# Get settings (default settings will be changed to the user specified settings)

...

# MAIN PROCESSES (main kernel processes such as network handles and resource management)

...

if __name__ == "__main__":
    import time
    
    # Covinience
    
    class KernelSettings(metaclass=ReadOnly):
        askSecondaryPrompt = False
    
    ############ HANDLER TESTING #############
    
    # Intialize the handler
    myhandler = eventHandler(verbose=True)
    
    # Define a test case
    def p_test(handler, th_id):
        def c_test(handler, th_id): print(f" [c_Test ({th_id})]: Done!")
        handler.add_cleaner(c_test)
        while handler.safe():
            ...
    
    # Add the event to the events list (queue)
    for _ in range(4):
        myhandler.add_event(p_test, thread=True)
    # Run all events (in this case only the test function)
    myhandler.run_events()
    # Do some stuff on the main thread
    time.sleep(1)
    # Signal the event handler to stop
    myhandler.stop()
    # Stop all threads of the kernel
    # FULL_STOP()
    
    ############# PERMISSION TESTING ##############
    
    # Initialize an askRoot instance
    myKernel = askRoot("Testing").getKernel()
    
    ############# Application Testing #############
    
    unrootedExec("print('unrooted', dir())")
    rootedExec("print('rooted', dir()); BOOT_OFF()")
